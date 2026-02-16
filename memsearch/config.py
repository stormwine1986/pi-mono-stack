import os

class Config:
    REDIS_URL = os.getenv("REDIS_URL", "redis://127.0.0.1:6379")
    MEM_CTL_CHANNEL = "mem_ctl"
    MEMORY_DIR = "/home/pi-mono/.pi/agent/workspace/memory/"

config = Config()
