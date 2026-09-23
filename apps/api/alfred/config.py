"""Runtime configuration and the cap limits that keep the free tier solvent.

Every knob here is an env var prefixed ``ALFRED_`` (e.g.
``ALFRED_ANTHROPIC_API_KEY``) or a line in a local ``.env`` file.

The caps are the whole reason the product can be free: a user physically
cannot trigger more than ``llm_calls_per_day`` paid model calls, so the
worst-case cost per user per day is bounded and computable.

Backward compatibility: this project was previously named LeetLearn and its
env vars were prefixed ``LEETLEARN_``. Anyone with an existing ``.env`` from
before the rename should not have their deployment silently break, so
``_apply_legacy_env`` below fills in any field left unset by an ``ALFRED_``
var from the matching old ``LEETLEARN_`` var, with a deprecation warning.
Prefer ``ALFRED_*`` in new configuration — the ``LEETLEARN_*`` fallback may be
removed in a future release.
"""

from __future__ import annotations

import os
import warnings
from functools import lru_cache

from dotenv import dotenv_values
from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_LEGACY_ENV_PREFIX = "LEETLEARN_"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="ALFRED_", env_file=".env", extra="ignore", populate_by_name=True
    )

    # --- storage ---
    database_url: str = "sqlite:///./alfred.db"

    # --- model layer ---
    # Empty key => the app still runs fully; every LLM path degrades to the
    # offline card/heuristic path instead of erroring.
    anthropic_api_key: str | None = None
    opus_model: str = "claude-opus-4-8"      # deep review, card generation
    haiku_model: str = "claude-haiku-4-5"    # cheap personalized nudges, classification
    # Which model backend powers the optional LLM paths:
    #   auto      -> local Ollama if reachable, else Anthropic if a key is set, else offline
    #   ollama    -> local only (free, private)   anthropic -> paid API   off -> offline only
    llm_backend: str = "auto"
    ollama_host: str = "http://127.0.0.1:11434"
    ollama_model: str = "qwen2.5:7b"

    # --- cap limits (the cost fence) ---
    # Card hints are DB reads (~free), so their cap only exists to stop abuse.
    card_hints_per_day: int = 40
    # LLM-backed calls are the only ones that cost money. This is the real fence.
    # Worst case per user/day at Haiku 4.5 (~$0.006/call): 25 * $0.006 = $0.15.
    llm_calls_per_day: int = 25
    # Deep Opus reviews are the priciest path; capped tighter.
    llm_reviews_per_day: int = 8

    # --- gamification ---
    daily_solve_goal: int = 1
    streak_freezes_default: int = 2

    # --- auth ---
    # GitHub OAuth -> signed JWT. The extension drives the browser half via
    # chrome.identity.launchWebAuthFlow; the secret never leaves the server.
    github_client_id: str | None = None
    github_client_secret: str | None = None
    jwt_secret: str | None = None
    jwt_ttl_days: int = 30

    # The dev bypass (`Bearer llt_<user_id>`) accepts any user id with no proof
    # of identity — it is an impersonation hole by construction. It therefore
    # defaults OFF and must be switched on deliberately for local work; a
    # deployment that forgets to configure auth fails closed rather than open.
    dev_auth_enabled: bool = False

    # --- CORS ---
    # Comma-separated. Extension origins are matched by regex in main.py instead,
    # since their ids differ per install; this list is for the web dashboard.
    cors_origins: str = "http://localhost:5173,http://localhost:8000"

    # --- vault integration (optional, ecosystem-wide) ---
    # Root of the shared Markdown vault other agents in this ecosystem (e.g.
    # Friday/jarvisOS) also read and write. Unprefixed — VAULT_PATH, not
    # ALFRED_VAULT_PATH — because it names a location shared across agents,
    # not an Alfred-specific setting. Unset by default: every vault-touching
    # function in `vault.py` is then a true no-op (no filesystem access at
    # all), so Alfred works completely standalone with zero vault configured.
    vault_path: str | None = Field(default=None, validation_alias="VAULT_PATH")

    @property
    def github_oauth_configured(self) -> bool:
        return bool(self.github_client_id and self.github_client_secret)

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @model_validator(mode="before")
    @classmethod
    def _apply_legacy_env(cls, data: object) -> object:
        """Fill in fields left unset by ``ALFRED_*`` from the old ``LEETLEARN_*``
        name, so a `.env` written before the LeetLearn -> Alfred rename keeps
        working. ``ALFRED_*`` always wins when both are set.
        """
        if not isinstance(data, dict):
            data = dict(data) if data else {}
        # `.env` values are parsed by pydantic-settings internally and never
        # exported to os.environ, so an old LEETLEARN_* line written there has
        # to be read the same way to be found.
        env_file = cls.model_config.get("env_file")
        file_values = dotenv_values(env_file) if env_file and os.path.exists(env_file) else {}
        for field in cls.model_fields:
            # `field in data` means an ALFRED_* source (env, dotenv, or an
            # explicit kwarg — including an explicit `None`) already decided
            # this value; only an *absent* key falls through to the legacy
            # LEETLEARN_* name.
            if field in data:
                continue
            legacy_key = f"{_LEGACY_ENV_PREFIX}{field.upper()}"
            legacy_value = os.environ.get(legacy_key, file_values.get(legacy_key))
            if legacy_value is not None:
                warnings.warn(
                    f"{legacy_key} is deprecated; set ALFRED_{field.upper()} instead. "
                    "The LEETLEARN_* fallback will be removed in a future release.",
                    DeprecationWarning,
                    stacklevel=2,
                )
                data[field] = legacy_value
        return data


@lru_cache
def get_settings() -> Settings:
    return Settings()
