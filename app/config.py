from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_HOST: str = "localhost"
    DATABASE_PORT: int = 5432
    DATABASE_NAME: str = "travelhub"
    DATABASE_USER: str = "travelhub_app"
    DATABASE_PASSWORD: str = ""

    KAFKA_BOOTSTRAP_SERVERS: str = "localhost:9092"
    KAFKA_TOPIC_PMS_SYNC: str = "pms-sync-queue"
    KAFKA_ENABLED: bool = True

    JWT_ISSUER: str = "https://auth.travelhub.app"
    JWT_AUDIENCE: str = "travelhub-api"

    SERVICE_NAME: str = "pms-integration-services"
    SERVICE_PORT: int = 8000

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"postgresql+asyncpg://{self.DATABASE_USER}:{self.DATABASE_PASSWORD}"
            f"@{self.DATABASE_HOST}:{self.DATABASE_PORT}/{self.DATABASE_NAME}"
        )

    @property
    def DATABASE_URL_SYNC(self) -> str:
        return (
            f"postgresql+psycopg2://{self.DATABASE_USER}:{self.DATABASE_PASSWORD}"
            f"@{self.DATABASE_HOST}:{self.DATABASE_PORT}/{self.DATABASE_NAME}"
        )

    class Config:
        env_file = ".env"


settings = Settings()
