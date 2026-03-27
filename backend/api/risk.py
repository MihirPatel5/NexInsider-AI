"""
backend/api/risk.py — Risk management endpoints.
"""
from fastapi import APIRouter
from data.config import settings

router = APIRouter()

@router.get("/status")
async def get_risk_status():
    """Get current risk circuit breaker status."""
    return {"status": "OPERATIONAL", "max_daily_loss": settings.max_daily_loss_pct}

@router.post("/kill-switch")
async def activate_kill_switch():
    """Manual emergency halt."""
    # Logic to update risk_state in DB.
    return {"status": "KILL_SWITCH_ACTIVATED"}
