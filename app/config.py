from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    ULTRA_SECRET_API_KEY: str

    class Config:
        env_file = ".env"


settings = Settings()
