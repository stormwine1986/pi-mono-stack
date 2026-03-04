
import json
import logging
import time
import redis
import os
from datetime import datetime
from config import config

logger = logging.getLogger("memory-audit")

class MemoryAuditor:
    def __init__(self):
        self.r = redis.from_url(config.REDIS_URL, decode_responses=True)
        self.log_dir = config.AUDIT_LOG_DIR
        os.makedirs(self.log_dir, exist_ok=True)

    def get_log_path(self):
        """Returns the current day's log path."""
        day_str = datetime.utcnow().strftime("%Y%m%d")
        return os.path.join(self.log_dir, f"memory_audit_{day_str}.jsonl")

    def record_event(self, event_type, user_id, memory_id, fact, metadata=None):
        """
        Records a memory event to file and Redis.
        event_type: ADD, DELETE, UPDATE, etc.
        """
        event = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "event": event_type,
            "user_id": user_id,
            "memory_id": memory_id,
            "fact": fact,
            "metadata": metadata or {}
        }
        
        # 1. Log to file (JSONL)
        try:
            log_path = self.get_log_path()
            with open(log_path, "a") as f:
                f.write(json.dumps(event) + "\n")
        except Exception as e:
            logger.error(f"Failed to write to audit log: {e}")

        # 2. Publish to Redis Stream
        try:
            self.r.xadd(config.AUDIT_STREAM, {"payload": json.dumps(event)})
        except Exception as e:
            logger.error(f"Failed to publish to redis stream: {e}")

        logger.info(f"Audit: {event_type} | User: {user_id} | Fact: {fact[:50]}...")

    def record_interaction_results(self, user_id, results, source_metadata=None):
        """
        Processes the raw results from mem0.add() and records individual events.
        results: The 'results' list from mem0 return.
        """
        if not results or not isinstance(results, list):
            return

        for res in results:
            event_type = res.get("event")
            # Mem0 uses ADD, DELETE, UPDATE, NONE
            if event_type == "NONE":
                continue
                
            self.record_event(
                event_type=event_type,
                user_id=user_id,
                memory_id=res.get("id"),
                fact=res.get("memory"),
                metadata=source_metadata
            )

auditor = MemoryAuditor()
