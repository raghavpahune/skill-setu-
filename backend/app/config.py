"""Application configuration from environment variables."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_key: str = ""
    gemini_api_key: str = ""
    data_gov_api_key: str = ""
    admin_api_key: str = ""
    cors_origins: str = ""
    use_demo_data: bool = True
    auto_sync_enabled: bool = True
    sync_interval_hours: int = 24
    sync_on_startup: bool = False
    jwt_secret_key: str = ""
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440
    demo_auth_enabled: bool = True

    @property
    def ai_available(self) -> bool:
        return bool(self.gemini_api_key)

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
