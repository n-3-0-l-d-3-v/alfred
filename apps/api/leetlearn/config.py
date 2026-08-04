"""Runtime configuration and the cap limits that keep the free tier solvent.

Every knob here is an env var prefixed ``LEETLEARN_`` (e.g.
``LEETLEARN_ANTHROPIC_API_KEY``) or a line in a local ``.env`` file.

The caps are the whole reason the product can be free: a user physically
cannot trigger more than ``llm_calls_per_day`` paid model calls, so the
worst-case cost per user per day is bounded and computable.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="LEETLEARN_", env_file=".env", extra="ignore")

    # --- storage ---
    database_url: str = "sqlite:///./leetlearn.db"

    # --- model layer ---
    # Empty key => the app still runs fully; every LLM path degrades to the
    # offline card/heuristic path instead of erroring.
    anthropic_api_key: str | None = None
    opus_model: str = "claude-opus-4-8"      # deep review, card generation
    haiku_model: str = "claude-haiku-4-5"    # cheap personalized nudges, classification

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

    @property
    def github_oauth_configured(self) -> bool:
        return bool(self.github_client_id and self.github_client_secret)

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
