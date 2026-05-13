from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {"extra": "forbid"}

    vault_addr: str = "http://localhost:8200"
    vault_token: str = ""

    api_port: int = 8000
    db_port: int = 5432
    redis_port: int = 6379
    minio_port: int = 9000
    minio_console_port: int = 9001
    sftp_port: int = 2222
    redis_host: str = "redis"
    minio_endpoint: str = "minio:9000"
    sftp_host: str = "sftp"
    sftp_container_port: int = 22
    sftp_poll_interval_seconds: int = 5
    sftp_max_file_bytes: int = 50 * 1024 * 1024

    cors_origins: list[str] = ["http://localhost:5173"]
    model_threshold_top1: float = 0.85
    cache_default_ttl: int = 60
    use_fakes: bool = False  # set via env: USE_FAKES=1 (alias: WORKER_USE_FAKES)
