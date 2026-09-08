"""Application configuration from environment variables."""
import os
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_key: str = ""
    gemini_api_key: str = ""
    data_gov_api_key: str = ""
    adzuna_app_id: str = ""
    adzuna_app_key: str = ""
    admin_api_key: str = ""
    cors_origins: str = ""
    environment: str = "development"
    use_demo_data: bool = True
    auto_sync_enabled: bool = True
    sync_interval_hours: int = 24
    refresh_interval_minutes: int = 60
    sync_sources: str = "all"
    sync_on_startup: bool = False
    jwt_secret_key: str = ""
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440
    demo_auth_enabled: bool = False
    admin_password: str = ""

    @property
    def is_production(self) -> bool:
        render_env = os.getenv("RENDER")
        if render_env is not None and render_env.strip() != "" and render_env.strip() != "0" and render_env.strip().lower() != "false":
            return True
        env_val = (os.getenv("ENVIRONMENT") or self.environment or "").strip().lower()
        return env_val in ("production", "prod")

    @model_validator(mode="after")
    def validate_production_demo_auth(self) -> "Settings":
        if self.is_production and self.demo_auth_enabled:
            raise ValueError("FATAL: Demo authentication cannot be enabled in production mode (DEMO_AUTH_ENABLED=true).")
        return self

    @property
    def effective_refresh_interval_minutes(self) -> int:
        if "refresh_interval_minutes" in self.model_fields_set:
            return max(1, self.refresh_interval_minutes)
        if "sync_interval_hours" in self.model_fields_set:
            return max(1, self.sync_interval_hours * 60)
        return max(1, self.refresh_interval_minutes)

    @property
    def ai_available(self) -> bool:
        return bool(self.gemini_api_key)

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
