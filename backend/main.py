"""
backend/main.py — FastAPI entrypoint.
Orchestrates API routers, WebSockets, and startup/shutdown lifecycle.
"""
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from data.config import settings
from backend.api import data, signals, orders, risk, portfolio

app = FastAPI(
    title="Algo Trading System API",
    description="Production-grade AI trading backend",
    version="1.0.0",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(data.router,      prefix="/api/v1/data",      tags=["Data"])
app.include_router(signals.router,   prefix="/api/v1/signals",   tags=["Signals"])
app.include_router(orders.router,    prefix="/api/v1/orders",    tags=["Orders"])
app.include_router(risk.router,      prefix="/api/v1/risk",      tags=["Risk"])
app.include_router(portfolio.router, prefix="/api/v1/portfolio", tags=["Portfolio"])


@app.on_event("startup")
async def startup_event():
    logger.info(f"═══ Starting Algo Trading API | env={settings.environment} ═══")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("═══ Shutting down Algo Trading API ═══")


@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": "1.0.0"}
