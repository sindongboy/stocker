from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore", env_ignore_empty=True)

    trading_mode: str = Field("paper", alias="TRADING_MODE")
    permission_profile: str = Field("strict", alias="PERMISSION_PROFILE")

    # Kiwoom live
    kiwoom_app_key: str = Field("", alias="KIWOOM_APP_KEY")
    kiwoom_app_secret: str = Field("", alias="KIWOOM_APP_SECRET")
    kiwoom_account_number: str = Field("", alias="KIWOOM_ACCOUNT_NUMBER")
    kiwoom_api_base_url: str = Field("https://api.kiwoom.com", alias="KIWOOM_API_BASE_URL")

    # Kiwoom mock (모의투자)
    kiwoom_mock_app_key: str = Field("", alias="KIWOOM_MOCK_APP_KEY")
    kiwoom_mock_app_secret: str = Field("", alias="KIWOOM_MOCK_APP_SECRET")
    kiwoom_mock_account_number: str = Field("", alias="KIWOOM_MOCK_ACCOUNT_NUMBER")
    kiwoom_mock_api_base_url: str = Field("https://mockapi.kiwoom.com", alias="KIWOOM_MOCK_API_BASE_URL")

    # Token endpoint path — verify against official docs before changing
    kiwoom_token_path: str = Field("/oauth2/token", alias="KIWOOM_TOKEN_PATH")

    # Gemini
    gemini_api_key: str = Field("", alias="GEMINI_API_KEY")
    gemini_model_pro: str = Field("gemini-2.5-pro", alias="GEMINI_MODEL_PRO")
    gemini_model_flash: str = Field("gemini-2.5-flash", alias="GEMINI_MODEL_FLASH")

    # Global context APIs
    polygon_api_key: str = Field("", alias="POLYGON_API_KEY")
    finnhub_api_key: str = Field("", alias="FINNHUB_API_KEY")

    # Infra
    database_url: str = Field("sqlite:///./data/trading.db", alias="DATABASE_URL")
    redis_url: str = Field("redis://localhost:6379/0", alias="REDIS_URL")
    log_level: str = Field("INFO", alias="LOG_LEVEL")

    @property
    def active_app_key(self) -> str:
        return self.kiwoom_mock_app_key if self.trading_mode == "paper" else self.kiwoom_app_key

    @property
    def active_app_secret(self) -> str:
        return self.kiwoom_mock_app_secret if self.trading_mode == "paper" else self.kiwoom_app_secret

    @property
    def active_base_url(self) -> str:
        return self.kiwoom_mock_api_base_url if self.trading_mode == "paper" else self.kiwoom_api_base_url

    @property
    def active_account_number(self) -> str:
        return self.kiwoom_mock_account_number if self.trading_mode == "paper" else self.kiwoom_account_number


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
