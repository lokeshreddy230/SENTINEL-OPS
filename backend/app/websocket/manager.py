import asyncio
import json
import logging
from typing import List, Dict, Any

logger = logging.getLogger("sentinelops.event_manager")

class EventPublisher:
    def __init__(self):
        self._listeners: List[asyncio.Queue] = []

    def subscribe(self) -> asyncio.Queue:
        queue = asyncio.Queue()
        self._listeners.append(queue)
        logger.info(f"New stream client subscribed. Active listeners: {len(self._listeners)}")
        return queue

    def unsubscribe(self, queue: asyncio.Queue):
        if queue in self._listeners:
            self._listeners.remove(queue)
            logger.info(f"Stream client disconnected. Active listeners: {len(self._listeners)}")

    async def publish(self, event_type: str, data: Dict[str, Any]):
        message = {
            "type": event_type,
            "data": data
        }
        logger.info(f"Publishing real-time event: {event_type}")
        
        # Dispatch to all listeners
        for queue in self._listeners:
            try:
                await queue.put(message)
            except Exception as e:
                logger.error(f"Error publishing to listener queue: {e}")

# Global singleton event publisher
event_publisher = EventPublisher()
