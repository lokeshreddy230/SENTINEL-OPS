from fastapi import APIRouter, Request
from sse_starlette.sse import EventSourceResponse
from app.websocket.manager import event_publisher
import asyncio
import json
import logging

logger = logging.getLogger("sentinelops.stream")
router = APIRouter(prefix="/api/events", tags=["Stream"])

@router.get("/stream")
async def event_stream(request: Request):
    async def event_generator():
        queue = event_publisher.subscribe()
        try:
            # Yield initial connection confirmation
            yield {
                "event": "ping",
                "data": "connected"
            }
            
            while True:
                if await request.is_disconnected():
                    logger.info("Client disconnected from event stream")
                    break
                
                try:
                    # Bounded wait for new events to allow periodic disconnection checks
                    message = await asyncio.wait_for(queue.get(), timeout=3.0)
                    yield {
                        "event": message["type"],
                        "data": json.dumps(message["data"])
                    }
                except asyncio.TimeoutError:
                    # Keep-alive heartbeat
                    yield {
                        "event": "heartbeat",
                        "data": "ping"
                    }
        except Exception as e:
            logger.error(f"Error in event stream: {e}")
        finally:
            event_publisher.unsubscribe(queue)

    return EventSourceResponse(event_generator())
