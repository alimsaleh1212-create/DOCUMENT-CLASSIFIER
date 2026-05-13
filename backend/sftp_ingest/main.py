from __future__ import annotations

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import Settings
from app.infra.blob import MinioBlob
from app.infra.queue import RQQueue
from app.infra.sftp import SFTPClient
from app.infra.vault import VaultClient
from sftp_ingest.processor import run_forever


def build_worker(
    settings: Settings,
) -> tuple[SFTPClient, MinioBlob, RQQueue, async_sessionmaker]:
    vault = VaultClient(settings.vault_addr, settings.vault_token)
    postgres_dsn = vault.get_postgres_dsn()
    minio_access_key, minio_secret_key = vault.get_minio_credentials()
    sftp_user, sftp_password = vault.get_sftp_credentials()

    sftp = SFTPClient(
        host=settings.sftp_host,
        port=settings.sftp_container_port,
        user=sftp_user,
        password=sftp_password,
    )
    blob = MinioBlob(
        endpoint=settings.minio_endpoint,
        access_key=minio_access_key,
        secret_key=minio_secret_key,
    )
    queue = RQQueue(redis_url=f"redis://{settings.redis_host}:{settings.redis_port}/0")
    engine = create_async_engine(postgres_dsn, echo=False)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    return sftp, blob, queue, session_factory


async def main() -> None:
    settings = Settings()
    sftp, blob, queue, session_factory = build_worker(settings)
    await run_forever(
        sftp=sftp,
        blob=blob,
        queue=queue,
        session_factory=session_factory,
        poll_interval_seconds=settings.sftp_poll_interval_seconds,
        max_bytes=settings.sftp_max_file_bytes,
    )
