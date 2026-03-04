import threading
import logging
from config import config
from observer import StreamObserver
from api import app
import uvicorn

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mem0-main")

def run_observer():
    try:
        logger.info("Initializing Memory Observer thread...")
        observer = StreamObserver()
        observer.run()
    except Exception as e:
        logger.error(f"Observer thread failed: {e}")

if __name__ == "__main__":
    logger.info("Starting Pi Memory Subsystem (Single Process Mode)...")
    
    # Start observer in a separate thread (share the same process/memory space)
    observer_thread = threading.Thread(target=run_observer, name="ObserverThread", daemon=True)
    observer_thread.start()
    
    # Run API in the main thread
    try:
        logger.info(f"Launching API on port {config.MEM_API_PORT}...")
        uvicorn.run(app, host="0.0.0.0", port=config.MEM_API_PORT)
    except Exception as e:
        logger.error(f"API failed: {e}")
