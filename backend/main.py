"""ComplyForge FastAPI entrypoint.

Run from `backend/` with `uvicorn main:app --reload --port 8000`.

Lifespan handler creates `generated_pdfs/` and `audit_logs/` relative to the
current working directory (i.e. `backend/`) so the analyze and enforcement
routers can write files immediately.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import analyze as analyze_router
from app.routers import enforcement as enforcement_router

CREATE_DIRS = ("generated_pdfs", "audit_logs")

ALLOWED_ORIGINS = (
    "http://localhost:5173",  # Vite dev server
    "http://localhost:3000",  # alt dev port
)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    for d in CREATE_DIRS:
        Path(d).mkdir(parents=True, exist_ok=True)
    yield


app = FastAPI(
    title="ComplyForge",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(ALLOWED_ORIGINS),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(analyze_router.router)
app.include_router(enforcement_router.router)


@app.get("/")
async def root() -> dict:
    return {
        "name": "ComplyForge",
        "version": "0.1.0",
        "status": "ready",
        "agents": ["classifier", "doc_agent", "policy_agent"],
    }


__all__ = ["app", "lifespan"]
