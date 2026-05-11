from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import Settings

settings = Settings()

engine = create_async_engine(
    "postgresql+asyncpg://placeholder:placeholder@localhost:5432/docclass",
    echo=False,
)

async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_session():
    async with async_session_factory() as session:
        yield session
