from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.scenario_state import scenario_state
from app.websocket.manager import event_publisher
import logging

logger = logging.getLogger("sentinelops.demo_api")
router = APIRouter(prefix="/api/demo", tags=["Demo Scenarios"])

@router.post("/scenario/{scenario_id}")
async def trigger_scenario(scenario_id: str):
    valid_scenarios = ["1", "2", "3", "4", "5", "6", "reset"]
    if scenario_id not in valid_scenarios:
        raise HTTPException(status_code=400, detail="Invalid scenario ID. Must be 1, 2, 3, 4, 5, 6, or 'reset'")

    if scenario_id == "reset":
        scenario_state.reset()
        logger.info("Demo scenario reset triggered.")
        await event_publisher.publish("scenario_reset", {"message": "All failure injections cleared. System returning to normal baselines."})
        return {"status": "success", "message": "Demo scenario reset successfully."}
    
    scenario_state.trigger(scenario_id)
    logger.info(f"Demo scenario {scenario_id} triggered.")
    
    await event_publisher.publish("scenario_triggered", {
        "scenario_id": scenario_id,
        "message": f"Failure scenario {scenario_id} injected into environment."
    })
    
    return {
        "status": "success",
        "scenario_id": scenario_id,
        "message": f"Failure scenario {scenario_id} successfully injected."
    }
