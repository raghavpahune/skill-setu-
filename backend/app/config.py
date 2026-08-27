"""Application configuration from environment variables."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_key: str = ""
    gemini_api_key: str = ""
    data_gov_api_key: str = ""
    use_demo_data: bool = True
    auto_sync_enabled: bool = True
    sync_interval_hours: int = 24
    sync_on_startup: bool = False

    @property
    def ai_available(self) -> bool:
        return bool(self.gemini_api_key)

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
