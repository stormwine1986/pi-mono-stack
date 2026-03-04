import os

class Config:
    REDIS_URL = os.getenv("REDIS_URL", "redis://127.0.0.1:6379")
    LLAMA_SERVER_URL = os.getenv("LLAMA_SERVER_URL", "http://127.0.0.1:18080/v1")
    LLAMA_EMBEDDING_URL = os.getenv("LLAMA_EMBEDDING_URL", "http://127.0.0.1:18081/v1")
    MEM_API_PORT = int(os.getenv("MEM_API_PORT", "18090"))
    
    # Redis Channels & Streams
    AGENT_IN_STREAM = "agent_in"
    AGENT_OUT_STREAM = "agent_out"
    
    # Persistence
    MILVUS_URI = "/data/mem0_milvus.db"
    HISTORY_DB_PATH = "/data/mem0_history.db"
    
    # Embedding Dimensions
    EMBEDDING_DIMS = 512

config = Config()
