# Аудит кодовой базы и предложения по доработке

**Дата:** 2026-06-10
**Ревизия:** `d8d4fed` (ветка идентична `main`, аудит покрывает всё текущее состояние проекта)

## Резюме

Проект в хорошем состоянии для демо/хакатона: CI зелёный (50/50 тестов, ruff/black/mypy
без замечаний), структура пакетов понятная, скрипты идемпотентны, секреты в скриптах
передаются через env (не argv). Основные риски сосредоточены в трёх местах:

1. **Две параллельные реализации продукта** — `src/roboqc_agent` и `src/neuron_vision`
   дублируют схемы, телеметрию и агентные концепции без общего ядра.
2. **Незавершённая интеграция `roboqc_agent`** — граф собран, но ключевые связки
   (state-передача, персистентность, policy engine) остались в TODO; пакет
   `neuron_vision` — единственный реально рабочий runtime-путь.
3. **Производственная небезопасность отдельных умолчаний** — in-memory БД, отсутствие
   таймаутов, контейнеры под root, мутация `os.environ` из UI.

Ниже — находки по приоритетам с конкретными предложениями.

---

## Критичные (исправить до продакшена)

### C1. Нет таймаута на параллельном выполнении инструментов
`src/roboqc_agent/orchestration/tool_runner.py` — `asyncio.gather()` без таймаута:
один зависший инструмент блокирует весь batch навсегда. То же в UI:
`app.py:334` — `asyncio.run(pipeline.run_async(...))` без таймаута, зависший вызов
Vertex AI замораживает сессию Streamlit.

**Предложение:** обернуть в `asyncio.wait_for(..., timeout=...)` (для batch — 30–60 с,
для пайплайна — 5 мин), таймаут вынести в конфиг, обрабатывать `TimeoutError` с
понятным сообщением пользователю.

### C2. SQLite-репозиторий: утечка соединения и хрупкая десериализация
`src/roboqc_agent/execution_store/sqlite_repo.py`:
- соединение открывается в `__init__` (стр. 21) и никогда не закрывается — нет
  `close()` / контекстного менеджера;
- `get_report()` (стр. 99) и `get_timeline()` (стр. 115) парсят JSON из БД без
  обработки `ValidationError` / `JSONDecodeError` — одна повреждённая запись роняет
  весь запрос;
- `metrics()` (стр. 122–130) сравнивает статусы строковыми литералами `'hold'`,
  `'rework'`, `'in_progress'` вместо `BoardStatus.*.value` — при изменении enum
  запросы молча вернут 0.

**Предложение:** добавить `close()` + `__enter__`/`__exit__`; обернуть
десериализацию в try/except с логированием и пропуском битых строк; перейти на
параметризованные запросы со значениями enum.

### C3. In-memory БД как умолчание
`sqlite_repo.py:17` — `db_path: str = ":memory:"`: при рестарте Cloud Run все
отчёты теряются. **Предложение:** `db_path = os.getenv("ROBOQC_DB_PATH")` с
обязательным явным значением для прод-режима (и валидацией, что путь лежит в
ожидаемой директории — сейчас `mkdir(parents=True)` создаст что угодно).

### C4. Мутация `os.environ` из Streamlit UI
`app.py:130` — введённый пользователем GCP Project ID пишется напрямую в
`os.environ["GOOGLE_CLOUD_PROJECT"]`. Для публично доступного инстанса это
позволяет перенаправить все вызовы Vertex AI в чужой проект; формат не валидируется.

**Предложение:** передавать `project_id` параметром в инициализацию пайплайна,
валидировать формат (6–30 символов, `[a-z][a-z0-9-]+`), логировать используемый
проект в каждом запросе.

### C5. Контейнеры работают под root
`Dockerfile` (корневой) и `infra/cloudrun/Dockerfile` не содержат `USER` —
процессы идут под root. `infra/fable5/Dockerfile` сделан правильно
(`USER appuser`, uid 1001). **Предложение:** привести все три Dockerfile к
единому шаблону с non-root пользователем.

### C6. Нереализованные связки в графе `roboqc_agent`
`src/roboqc_agent/graph.py:51-55` — три TODO блокируют реальное использование:
передача state между агентами, триггер evidence_report, персистентность через
execution_store. Кроме того:
- `agents/supervisor.py` и `agents/evidence_report.py` — пустые заглушки
  (docstring без кода);
- `FrictionPolicyEngine` (`policy/engine.py`) протестирован, но нигде не вызывается;
- `compute_defect_histogram()` экспортирован, но не используется как валидатор,
  хотя промпт evidence_report обещает: «система пересчитывает гистограмму и
  отклоняет расхождения».

**Предложение:** либо доделать интеграцию (state keys → персистентность →
policy engine в supervisor → валидация гистограммы), либо честно вынести
roboqc_agent в статус «reference architecture» в README и завести issues на
каждый TODO.

---

## Средний приоритет

### M1. Консолидация `roboqc_agent` и `neuron_vision`
Оба пакета определяют свои Severity/verdict-схемы, телеметрию и базовые агентные
абстракции. Поддержка дублируется, версии концепций расходятся.
**Предложение:** выделить общее ядро `src/qc_core/` (базовый агент, схемы
вердиктов, телеметрия, fallback-логика) и переиспользовать в обоих пакетах.
Это самая крупная, но и самая окупаемая доработка.

### M2. Потокобезопасность кэша и инициализации трейсинга
- `src/neuron_vision/fable5/cache.py:40-45` — `get()` делает
  check-then-delete без блокировки; при конкурентных запросах в Cloud Run
  возможна гонка. Минимум — `self._entries.pop(key, None)` вместо `del`,
  лучше — `threading.Lock` вокруг get/put.
- `src/neuron_vision/telemetry.py:28-46` — `init_tracer()` использует глобальные
  флаги без блокировки: двойная инициализация tracer provider при конкурентном
  старте. Решение — `threading.Lock` или `functools.lru_cache(maxsize=1)`.

### M3. Разделение retryable / non-retryable ошибок в Fable5-клиенте
`src/neuron_vision/fable5/client.py:264-276` — fallback-цепочка маскирует и
сетевые ошибки, и `ValidationError` (дрейф схемы). Ошибки валидации должны
падать громко с контекстом, а не ретраиться на fallback-модель.

### M4. Хрупкий парсинг JSON из ответов модели
`src/neuron_vision/agents/base.py:207-213` — снятие markdown-fence через
`split("```")` ломается, если fence встречается в середине текста.
**Предложение:** regex-извлечение JSON-блока + проверка, что распарсен весь ответ.

### M5. Гигиена зависимостей
- `pyproject.toml` (без версий) и `requirements.txt` (с версиями + лишние пакеты)
  расходятся — два источника правды. Перенести пины в `pyproject.toml`,
  `requirements.txt` генерировать или удалить.
- Нет верхних границ у `anthropic`, `google-cloud-secret-manager`, `hatchling` —
  мажорный релиз молча сломает сборку. Добавить `<N+1`.
- `infra/fable5/requirements.lock` не пересобирается автоматически — добавить
  CI-проверку соответствия.

### M6. Усиление CI
`.github/workflows/ci.yml`:
- нет pip-кэша (`cache: 'pip'` в `setup-python`) — ~30 с лишних на прогон;
- нет coverage-гейта — добавить `pytest --cov=src --cov-fail-under=70`;
- bench.yml гоняет только `--smoke` — нет защиты от регрессий латентности
  (сохранять baseline артефактом, падать при росте >10%).

### M7. Покрытие тестами
50 тестов проходят, но без покрытия остаются: `neuron_vision/pipeline.py`
(оркестрация), `neuron_vision/agents/*` (5 инспекторов), `demo_mode.py`,
`app.py`. Стабы в `test_fable5_api.py` не валидируют контракт SDK.
**Предложение:** интеграционный тест пайплайна на моках агентов; контрактный
тест Fable5-клиента за skip-декоратором.

### M8. Конфигурация вместо хардкода
`gemini-2.5-pro` захардкожен в 6 местах (`graph.py`, 4 фабрики агентов,
`vertex_gemini.py`), регион `us-central1` — в `vertex_gemini.py:42`.
**Предложение:** единый `config.py` с `ROBOQC_MODEL` / `GOOGLE_CLOUD_LOCATION`
из env. Заодно решает расхождение версий моделей между пакетами.

### M9. Ограничения схем
`src/roboqc_agent/schemas.py` — LLM-генерируемые поля (`justification`,
`reason`, `rationale`) без `max_length`; `image_uri` не валидируется как
`gs://`-URI; `defect_histogram` не сверяется со списком дефектов.
**Предложение:** Field-constraints + field_validator'ы.

### M10. Деprecation-предупреждения Google ADK
Тесты показывают: `SequentialAgent` и `BaseAgentConfig` объявлены deprecated
(`graph.py:45`). **Предложение:** мигрировать на `Workflow` до удаления API.

---

## Низкий приоритет

| # | Где | Что | Предложение |
|---|-----|-----|-------------|
| L1 | `app.py:105` | Логотип грузится с Wikimedia | положить в `assets/` |
| L2 | `app.py:49-98` | CSS-палитра не учитывает dark mode | media query `prefers-color-scheme` |
| L3 | `app.py:147-162` | Молчаливо пустой селектор примеров при отсутствии `examples/pcb_samples` | info-сообщение |
| L4 | `demo_mode.py:503` | `time.sleep()` блокирует event loop | async-версия с `asyncio.sleep()` |
| L5 | `neuron_vision/agents/base.py:216` | MIME только PNG/JPEG по magic bytes | расширить или валидировать вход |
| L6 | `tool_runner.py:58`, `llm_telemetry.py`, `request_log.py` | широкие `except Exception` без логирования | конкретные типы + `logger.debug/warning` |
| L7 | `.pre-commit-config.yaml:6` | `ruff --fix` авто-правит на коммите | оставить fix только локально |
| L8 | `.dockerignore` | не исключены `infra/`, `.github/`, `video/` | добавить |
| L9 | `.env.example` | не все используемые переменные задокументированы | синхронизировать с кодом |
| L10 | `schemas.py:8` | комментарий «Frozen 2026-05-16», но код меняется | обновить формулировку |
| L11 | `infra/monitoring` | нет бюджет-алерта и метрики fallback-rate Fable5 | `gcloud billing budgets` + log-based metric `fable5_fallback` |
| L12 | `README.md` | «два пути интеграции» Fable 5, описан один | дописать раздел про Agent Builder |

---

## Предлагаемый план работ

**Этап 1 — Quick wins (≈1 день):** ✅ выполнен в этой ветке
C5 (non-root в Dockerfile), M6 (pip-кэш + coverage-гейт), C2/C3 (sqlite: close,
try/except, env-путь), C1 (таймауты), M5 (пины версий), M2 (lock в cache/tracer).

**Этап 2 — Надёжность (≈3–5 дней):**
C4 (project_id через параметр), M3 (классификация ошибок Fable5), M4 (парсинг
JSON), M8 (config.py), M9 (валидаторы схем), M7 (интеграционные тесты пайплайна).

**Этап 3 — Архитектура (≈1–2 недели):**
C6 (доинтеграция или официальный reference-статус roboqc_agent),
M1 (общее ядро `qc_core`), M10 (миграция с deprecated ADK API),
L11 (метрики стоимости/fallback).

---

*Проверено локально на ревизии `d8d4fed`: `pytest` — 50 passed,
`ruff check .` / `black --check .` / `mypy src` — без замечаний.*
