from mem0 import Memory
from config import config
import logging

logger = logging.getLogger("mem0-client")

class MemoryClient:
    _instance = None
    _memory = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MemoryClient, cls).__new__(cls)
        return cls._instance

    @property
    def memory(self):
        if self._memory is None:
            logger.info("Initializing Mem0 Memory with ChromaDB backend...")
            mem0_config = {
                "llm": {
                    "provider": "openai",
                    "config": {
                        "model": "local-model",
                        "api_key": "not-needed",
                        "openai_base_url": config.LLAMA_SERVER_URL
                    }
                },
                "embedder": {
                    "provider": "openai",
                    "config": {
                        "model": "local-model",
                        "api_key": "not-needed",
                        "openai_base_url": config.LLAMA_EMBEDDING_URL,
                        "embedding_dims": config.EMBEDDING_DIMS
                    }
                },
                "vector_store": {
                    "provider": "chroma",
                    "config": {
                        "collection_name": "pi_memory_v1",
                        "path": "/data/chroma_db"
                    }
                },
                "history_db_path": config.HISTORY_DB_PATH,
                "version": "v1.1" # AUDN default
            }
            try:
                self._memory = Memory.from_config(mem0_config)
                logger.info("Mem0 Memory initialized successfully.")
            except Exception as e:
                logger.error(f"Failed to initialize Mem0: {e}")
                raise
        return self._memory

    def add_interaction(self, user_id, agent_id, prompt, response):
        """Adds a pair of interaction to the memory."""
        messages = [
            {"role": "user", "content": prompt},
            {"role": "assistant", "content": response}
        ]
        return self.memory.add(messages, user_id=user_id, metadata={"source_agent_id": agent_id})

    def search(self, query, user_id, agent_id=None, limit=5):
        """Searches for memories."""
        return self.memory.search(query, user_id=user_id, limit=limit)

    def get_all(self, user_id):
        """Retrieves all memories for a user."""
        return self.memory.get_all(user_id=user_id)

memory_client = MemoryClient()
