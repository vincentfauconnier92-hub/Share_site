from pydantic import model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    ENV: str = "development"
    SECRET_KEY: str = "change_me"
    API_SECRET_KEY: str = ""
    DATABASE_URL: str = "postgresql://trading:trading@db:5432/trading"

    ALPACA_API_KEY: str = ""
    ALPACA_SECRET_KEY: str = ""
    ALPACA_BASE_URL: str = "https://paper-api.alpaca.markets"

    BINANCE_API_KEY: str = ""
    BINANCE_SECRET_KEY: str = ""
    BINANCE_TESTNET: bool = True

    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_CHAT_ID: str = ""

    FRONTEND_URL: str = "http://localhost:3000"

    JWT_SECRET_KEY: str = ""
    JWT_EXPIRE_HOURS: int = 24

    class Config:
        env_file = ".env"

    @model_validator(mode="after")
    def _validate_secrets(self) -> "Settings":
        # JWT_SECRET_KEY hérite de API_SECRET_KEY si non défini
        if not self.JWT_SECRET_KEY:
            object.__setattr__(self, "JWT_SECRET_KEY", self.API_SECRET_KEY or self.SECRET_KEY)

        if self.ENV == "production":
            errors = []
            if not self.API_SECRET_KEY:
                errors.append("API_SECRET_KEY doit être défini en production")
            if self.SECRET_KEY in ("change_me", ""):
                errors.append("SECRET_KEY doit être changé en production")
            if "trading:trading" in self.DATABASE_URL:
                errors.append("DATABASE_URL utilise des credentials par défaut non sécurisés")
            if len(self.JWT_SECRET_KEY) < 32:
                errors.append("JWT_SECRET_KEY doit faire au moins 32 caractères en production")
            if errors:
                raise ValueError("Erreurs de configuration production :\n" + "\n".join(f"  - {e}" for e in errors))
        return self


settings = Settings()
