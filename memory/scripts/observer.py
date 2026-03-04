import json
import logging
import time
import redis
from config import config
from worker import memory_worker

logger = logging.getLogger("mem0-observer")
logging.basicConfig(level=logging.INFO)

class StreamObserver:
    def __init__(self):
        self.r = redis.from_url(config.REDIS_URL, decode_responses=True)
        self.group_name = "mem0-observer-group"
        self.consumer_name = "observer-1"
        self.prompt_cache_prefix = "mem0:prompt:"
        self.cache_ttl = 1800 # 30 minutes
        
        self._setup_groups()

    def _setup_groups(self):
        for stream in [config.AGENT_IN_STREAM, config.AGENT_OUT_STREAM]:
            try:
                self.r.xgroup_create(stream, self.group_name, id="$", mkstream=True)
                logger.info(f"Created consumer group {self.group_name} for stream {stream}")
            except redis.exceptions.ResponseError as e:
                if "BUSYGROUP" not in str(e):
                    logger.error(f"Error creating group: {e}")

    def run(self):
        logger.info("Starting Redis Stream Observer...")
        while True:
            try:
                # Read from agent_in and agent_out
                streams = {config.AGENT_IN_STREAM: ">", config.AGENT_OUT_STREAM: ">"}
                results = self.r.xreadgroup(self.group_name, self.consumer_name, streams, count=10, block=2000)
                
                if not results:
                    continue

                for stream_name, messages in results:
                    for msg_id, data in messages:
                        payload_raw = data.get("payload")
                        if not payload_raw:
                            self.r.xack(stream_name, self.group_name, msg_id)
                            continue
                        
                        try:
                            payload = json.loads(payload_raw)
                        except Exception as e:
                            logger.error(f"Failed to parse payload in {stream_name}: {e}")
                            self.r.xack(stream_name, self.group_name, msg_id)
                            continue

                        if stream_name == config.AGENT_IN_STREAM:
                            self._handle_agent_in(payload)
                        elif stream_name == config.AGENT_OUT_STREAM:
                            self._handle_agent_out(payload)
                        
                        self.r.xack(stream_name, self.group_name, msg_id)
            except Exception as e:
                logger.error(f"Error in observer loop: {e}")
                time.sleep(2)

    def _handle_agent_in(self, payload):
        task_id = payload.get("id")
        prompt = payload.get("prompt")
        if task_id and prompt:
            # Cache prompt for matching with output later
            key = f"{self.prompt_cache_prefix}{task_id}"
            self.r.setex(key, self.cache_ttl, prompt)
            logger.debug(f"Cached prompt for task {task_id}")

    def _handle_agent_out(self, payload):
        # We only care about successful completion for memory
        if payload.get("status") != "success":
            return

        task_id = payload.get("id")
        user_id = payload.get("user_id")
        agent_id = payload.get("agent_id", "0")
        response = payload.get("response")
        source = payload.get("source")

        if not all([task_id, user_id, response]) or source == "internal":
            return

        # Retrieve cached prompt
        key = f"{self.prompt_cache_prefix}{task_id}"
        prompt = self.r.get(key)
        
        if prompt:
            logger.info(f"Pairing prompt and response for task {task_id}, user {user_id}")
            memory_worker.submit_interaction(user_id, agent_id, prompt, response)
            # Cleanup cache
            self.r.delete(key)
        else:
            logger.warning(f"Response received for task {task_id} but prompt not found in cache")

if __name__ == "__main__":
    observer = StreamObserver()
    observer.run()
