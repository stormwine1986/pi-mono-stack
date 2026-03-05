import logging
import time
from concurrent.futures import ThreadPoolExecutor
from mem0_client import memory_client
from metrics import WORKER_QUEUE_SIZE, EXTRACTION_DURATION, EXTRACTION_TOTAL

logger = logging.getLogger("mem0-worker")
logging.basicConfig(level=logging.INFO)

class MemoryWorker:
    def __init__(self, max_workers=1):
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        logger.info(f"Memory Worker initialized with SERIAL thread (max_workers=1)")

    def submit_interaction(self, user_id, agent_id, prompt, response):
        """Asynchronously adds interaction to Mem0."""
        WORKER_QUEUE_SIZE.inc()
        self.executor.submit(self._task_add_memory, user_id, agent_id, prompt, response)

    def _task_add_memory(self, user_id, agent_id, prompt, response):
        start_time = time.monotonic()
        try:
            logger.info(f"Processing memory for user: {user_id}, agent: {agent_id}")
            result = memory_client.add_interaction(user_id, agent_id, prompt, response)
            
            elapsed = time.monotonic() - start_time
            EXTRACTION_DURATION.labels(status="success").observe(elapsed)
            EXTRACTION_TOTAL.labels(status="success").inc()
            
            logger.info(f"Memory added successfully for {user_id}")
            return result
        except Exception as e:
            elapsed = time.monotonic() - start_time
            EXTRACTION_DURATION.labels(status="failed").observe(elapsed)
            EXTRACTION_TOTAL.labels(status="failed").inc()
            logger.error(f"Failed to add memory for {user_id}: {str(e)}")
            return None
        finally:
            WORKER_QUEUE_SIZE.dec()

memory_worker = MemoryWorker()
