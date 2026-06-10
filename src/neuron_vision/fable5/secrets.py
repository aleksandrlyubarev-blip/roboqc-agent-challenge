"""
Anthropic API key resolution for Cloud Run / Vertex AI Agent Builder.

Resolution order:

1. ``ANTHROPIC_API_KEY`` env var — local development only. On Cloud Run the
   recommended setup is *not* a plain env var but ``--set-secrets``, which
   makes this same variable a Secret Manager reference (the key never lives
   in the service config or image).
2. Runtime fetch from Secret Manager via ``google-cloud-secret-manager``,
   using the service account's Workload Identity (no key files anywhere).

Only metadata is ever logged — never the secret value.
"""

from __future__ import annotations

import logging
import os

logger = logging.getLogger("neuron_vision.fable5.secrets")

DEFAULT_SECRET_ID = "anthropic-api-key"


class SecretResolutionError(RuntimeError):
    """Raised when no Anthropic API key can be resolved."""


def _fetch_from_secret_manager(project_id: str, secret_id: str, version: str) -> str:
    """Fetch one secret version. Import is local so the dependency stays optional."""

    from google.cloud import secretmanager

    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/{project_id}/secrets/{secret_id}/versions/{version}"
    response = client.access_secret_version(request={"name": name})
    payload: str = response.payload.data.decode("utf-8").strip()
    logger.info(
        "anthropic_key_loaded",
        extra={"source": "secret_manager", "secret_id": secret_id, "version": version},
    )
    return payload


def resolve_anthropic_api_key(
    project_id: str | None = None,
    secret_id: str | None = None,
    version: str = "latest",
) -> str:
    """
    Resolve the Anthropic API key for this process.

    Raises:
        SecretResolutionError: if neither the env var nor Secret Manager
            yields a key.
    """

    env_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    if env_key:
        logger.info("anthropic_key_loaded", extra={"source": "env"})
        return env_key

    project = project_id or os.getenv("GOOGLE_CLOUD_PROJECT") or ""
    secret = secret_id or os.getenv("ANTHROPIC_SECRET_ID") or DEFAULT_SECRET_ID
    if not project:
        raise SecretResolutionError(
            "No ANTHROPIC_API_KEY env var and GOOGLE_CLOUD_PROJECT is unset — "
            "cannot query Secret Manager."
        )

    try:
        return _fetch_from_secret_manager(project, secret, version)
    except SecretResolutionError:
        raise
    except Exception as exc:  # noqa: BLE001 — surface a single typed error to callers
        raise SecretResolutionError(
            f"Failed to read secret '{secret}' in project '{project}': {type(exc).__name__}"
        ) from exc
