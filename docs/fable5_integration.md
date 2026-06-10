# Интеграция Claude Fable 5 в Google Cloud — Neuron Vision Display

**Проект:** NeuroVision Display (RomeoFlexVision / RoboQC)
**Статус:** production-ready, оба варианта интеграции (Agent Builder + Cloud Run)

## Как это работает (summary)

Claude Fable 5 (`claude-fable-5`, Anthropic Messages API, контекст 1M токенов) подключён как
reasoning-движок двумя путями: (А) как Custom Tool в Vertex AI Agent Builder и (Б) как выделенный
FastAPI-сервис на Cloud Run (`src/neuron_vision/fable5/`), который вызывает API через официальный
`anthropic` SDK со structured output (JSON Schema), retry с экспоненциальным backoff и graceful
fallback на Claude Opus 4.8 при refusal/429/5xx/timeout. Ключ Anthropic живёт только в Google
Cloud Secret Manager и попадает в сервис через `--set-secrets` (или runtime-fetch через Workload
Identity); каждая модельная транзакция логируется в Cloud Logging метаданными (модель, токены,
латентность, оценка стоимости, fallback) — без промптов.

**Рекомендованная схема:** Agent Builder → Cloud Run (`/analyze-defect`) → Anthropic API.
Так ключ никогда не покидает Cloud Run, а fallback/кэш/телеметрия работают для обоих вариантов.

---

## Артефакт 1 — Secret Manager + IAM

Один раз на проект (замените `$PROJECT_ID`):

```bash
gcloud services enable secretmanager.googleapis.com run.googleapis.com \
  cloudbuild.googleapis.com artifactregistry.googleapis.com --project "$PROJECT_ID"

# 1. Секрет с ключом Anthropic (ключ читается из stdin — не оставляйте его в истории shell)
printf '%s' "$ANTHROPIC_KEY_VALUE" | gcloud secrets create anthropic-api-key \
  --replication-policy=automatic --data-file=- --project "$PROJECT_ID"

# 2. Выделенный сервис-аккаунт с минимальными правами (не default compute SA!)
gcloud iam service-accounts create fable5-runner \
  --display-name="Fable 5 reasoning service" --project "$PROJECT_ID"

# 3. Доступ ТОЛЬКО к этому секрету (а не roles/secretmanager.secretAccessor на проект)
gcloud secrets add-iam-policy-binding anthropic-api-key \
  --member="serviceAccount:fable5-runner@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor" --project "$PROJECT_ID"

# 4. Кто может вызывать сервис (дашборд / Agent Builder SA)
gcloud run services add-iam-policy-binding fable5-reasoning \
  --member="serviceAccount:<CALLER_SA>" --role="roles/run.invoker" \
  --region us-central1 --project "$PROJECT_ID"
```

Ротация ключа: `gcloud secrets versions add anthropic-api-key --data-file=-` + redeploy
(сервис читает `latest`). Старую версию — `gcloud secrets versions destroy`.

Принципы:
- ключ **никогда** не попадает в код, образ, env-файлы или логи;
- на Cloud Run ключ доставляется через `--set-secrets=ANTHROPIC_API_KEY=anthropic-api-key:latest`
  (Secret Manager-backed env) — это auth через Workload Identity сервис-аккаунта, без key-файлов;
- альтернатива — runtime-fetch в коде (`neuron_vision/fable5/secrets.py`), тот же IAM-биндинг;
- сервис-аккаунту не выдаётся ничего, кроме `secretAccessor` на один секрет.

## Артефакт 2 — Custom Tool для Vertex AI Agent Builder

Файл: [`infra/fable5/agent_builder_tool.json`](../infra/fable5/agent_builder_tool.json).

Два варианта в одном файле:
1. **`httpTool`** — прямой POST на `https://api.anthropic.com/v1/messages` с заголовками
   `x-api-key: {{ANTHROPIC_API_KEY}}` (биндинг на секрет в auth-конфиге тула, apiKey-in-header),
   `anthropic-version: 2023-06-01`, телом с `claude-fable-5`, `thinking: adaptive`,
   `output_config.format` (JSON Schema) и маппингом ответа `$.content[0].text`.
2. **`openapi_cloudrun_variant`** (рекомендуется) — OpenAPI-спека на Cloud Run `/analyze-defect`
   c auth через ID-токен сервис-аккаунта агента. Ключ Anthropic не попадает в Agent Builder вовсе.

## Артефакт 3 — System Prompt агента

Файл: [`infra/fable5/agent_builder_system_prompt.md`](../infra/fable5/agent_builder_system_prompt.md).
Содержит: когда вызывать `claude_fable5_reasoning` (root cause / causal / рекомендации — всегда),
когда не вызывать, как собирать вход (полный производственный контекст), как подавать результат
инженеру и как вести себя при refusal/ошибке (помеченная «предварительная оценка», без выдачи
деградированного ответа за вердикт Fable 5).

## Артефакт 4 — Python `Fable5Client`

Файл: [`src/neuron_vision/fable5/client.py`](../src/neuron_vision/fable5/client.py).

```python
from neuron_vision.fable5 import DefectAnalysisRequest, DefectObservation, Fable5Client
from neuron_vision.fable5.secrets import resolve_anthropic_api_key

client = Fable5Client(api_key=resolve_anthropic_api_key())
response = await client.reason(
    DefectAnalysisRequest(
        defects=[DefectObservation(
            defect_type="mura", location="center", severity="moderate", confidence=0.91,
        )],
        question="Why is mura rate climbing on line A since Monday?",
    )
)
print(response.result.root_cause.primary_root_cause)
print(response.meta.model_id, response.meta.estimated_cost_usd)
```

Ключевые решения (и почему):
- **`thinking={"type": "adaptive"}`, без sampling-параметров** — Fable 5 принимает только
  adaptive thinking; `temperature`/`top_p`/`top_k`/`budget_tokens` и явный `disabled` дают 400.
- **Structured output через `output_config.format`** (JSON Schema из Pydantic-моделей) +
  повторная валидация Pydantic на клиенте. Числовые ограничения (`ge`/`le`) API не поддерживает —
  `sanitize_json_schema()` вырезает их из wire-схемы, Pydantic проверяет их локально.
- **Retry** — SDK сам ретраит 429/5xx с экспоненциальным backoff (`max_retries=3`); поверх этого
  клиент делает ровно один cross-model fallback на `claude-opus-4-8` при refusal (guardrails:
  категории cyber/bio в `stop_details`), исчерпании ретраев, overload и timeout (120 с).
- **Кэш** — in-memory TTL (5 мин) по fingerprint запроса: повторный анализ той же партии дефектов
  (рефреш дашборда) не тратит токены. Интерфейс позволяет заменить на Memorystore.
- **Prompt caching** — системный промпт заморожен побайтово и помечен `cache_control: ephemeral`.
- **Стоимость** — каждая транзакция оценивается в USD (Fable 5: $10/$50 за MTok; Opus 4.8: $5/$25)
  и пишется в лог для мониторинга расходов.

## Артефакт 5 — FastAPI

Файл: [`src/neuron_vision/fable5/api.py`](../src/neuron_vision/fable5/api.py).
`POST /analyze-defect`, `POST /root-cause`, `POST /recommendations`, `GET /healthz`.
Клиент создаётся один раз в lifespan (ключ резолвится при старте), `Fable5Error` (оба
уровня fallback исчерпаны) → HTTP 503, чтобы дашборд деградировал, а не ретраил вслепую.

## Артефакт 6 — Pydantic-модели

Файл: [`src/neuron_vision/fable5/schemas.py`](../src/neuron_vision/fable5/schemas.py).
Вход: `DefectAnalysisRequest` (DefectObservation[], ProcessContext, question). Выход (LLM-схемы):
`DefectReasoning`, `RootCauseAnalysis`, `RecommendationSet`. Конверты ответов несут
`Fable5CallMeta` (модель, fallback, токены, латентность, стоимость, cache hit).

## Артефакт 7 — Dockerfile + requirements

Файлы: [`infra/fable5/Dockerfile`](../infra/fable5/Dockerfile),
[`infra/fable5/requirements.txt`](../infra/fable5/requirements.txt).
Slim-образ только с reasoning-сервисом (без Streamlit/Vertex SDK), non-root user, uvicorn на 8080.

## Артефакт 8 — cloudbuild.yaml

Файл: [`infra/fable5/cloudbuild.yaml`](../infra/fable5/cloudbuild.yaml).

```bash
gcloud artifacts repositories create neuron-vision \
  --repository-format=docker --location=us-central1   # один раз
gcloud builds submit --config infra/fable5/cloudbuild.yaml --substitutions _REGION=us-central1
```

Build → push в Artifact Registry → deploy на Cloud Run с `fable5-runner` SA,
`--set-secrets`, `--no-allow-unauthenticated`, timeout 180 c.

## Артефакт 9 — Мониторинг расходов и токенов

Каждый вызов пишет structured-лог `fable5_call` / `fable5_fallback` / `fable5_error`
(`neuron_vision/fable5/telemetry.py`): model, latency_ms, input/output tokens,
estimated_cost_usd, fallback_reason, error_type. Промпты и ответы не логируются.

Настройка в Cloud Monitoring (паттерн тот же, что в `infra/monitoring/`):

```bash
# Метрика по стоимости (distribution по полю estimated_cost_usd)
gcloud logging metrics create fable5_cost_usd \
  --description="Per-call Fable 5 cost estimate" \
  --log-filter='jsonPayload.event="fable5_call"' \
  --bucket-options=exponential-buckets,num-finite-buckets=20,growth-factor=2,scale=0.001 \
  --value-extractor='EXTRACT(jsonPayload.estimated_cost_usd)'

# Счётчик fallback'ов (рост = Fable 5 деградирует или душат rate limits)
gcloud logging metrics create fable5_fallback_count \
  --log-filter='jsonPayload.event="fable5_fallback"'

# Счётчик ошибок по типу
gcloud logging metrics create fable5_error_count \
  --log-filter='jsonPayload.event="fable5_error"'
```

Рекомендуемые алерты: суточная сумма `fable5_cost_usd` > бюджета; `fable5_fallback_count` > 5/час;
p95 `latency_ms` > 90 с; любой всплеск `fable5_error_count` c `error_type=refusal:*`. Плюс
billing-alert на стороне Anthropic Console (Fable 5 в 2 раза дороже Opus 4.8 — следите за
`fallback_used=false` долей). Cache hit видно по `meta.cached=true` в ответах.

## Артефакт 10 — Чеклист безопасности и production readiness

- [x] Ключ Anthropic только в Secret Manager; доступ — выделенный SA, биндинг на один секрет
- [x] `--no-allow-unauthenticated` + `roles/run.invoker` для конкретных вызывающих
- [x] Non-root контейнер, slim-образ без лишних SDK
- [x] Логируются только метаданные (никаких промптов/ответов/ключей)
- [x] Таймаут 120 с + SDK retry (429/5xx, exponential backoff) + fallback на Opus 4.8
- [x] Refusal (guardrails Fable 5, cyber/bio) обрабатывается: fallback + телеметрия категории
- [x] Structured output: схема enforced на сервере, повторная валидация Pydantic на клиенте
- [x] `max_tokens` stop_reason — явная ошибка, а не молчаливо обрезанный JSON
- [x] Кэш повторных запросов (TTL 5 мин) + prompt caching стабильного префикса
- [x] Метрики стоимости/токенов/fallback в Cloud Monitoring, алерты на бюджет
- [x] Unit-тесты без сети (`tests/test_fable5_client.py`), CI: ruff/black/mypy strict/pytest
- [ ] Прод: зафиксировать версии в `infra/fable5/requirements.txt` (pip-compile) перед релизом
- [ ] Прод: ротация ключа по расписанию (Secret Manager rotation + Cloud Scheduler)
- [ ] Опционально: Memorystore вместо in-memory кэша при >1 инстансе с высоким трафиком

### Smoke-тест после деплоя

```bash
URL=$(gcloud run services describe fable5-reasoning --region us-central1 --format='value(status.url)')
TOKEN=$(gcloud auth print-identity-token)
curl -s -X POST "$URL/analyze-defect" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"defects":[{"defect_type":"line_defect","location":"row 312","severity":"critical","confidence":0.97}],
       "context":{"line_id":"A","stage":"module","recent_changes":["new ACF lot 2026-06-08"]},
       "question":"Root cause?"}' | python -m json.tool
```
