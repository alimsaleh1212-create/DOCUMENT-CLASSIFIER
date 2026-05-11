from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import Settings

settings = Settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup checks — refuse to start if any invariant is violated
    # 1. Vault reachable + JWT signing key resolves
    # 2. Casbin policy table is non-empty
    # 3. (worker only) classifier.pt exists, SHA matches, top-1 >= threshold
    yield
    # Shutdown: close cache backend, DB engine


app = FastAPI(
    title="Document Classifier",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "X-Cache"],
)
