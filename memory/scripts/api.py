from fastapi import FastAPI, HTTPException, Response
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
import os
import json
from pydantic import BaseModel
from typing import Optional, List
import time
from mem0_client import memory_client
from config import config
from metrics import SEARCH_DURATION, SEARCH_TOTAL

app = FastAPI(title="Pi Memory Service")

@app.get("/metrics")
async def metrics():
    """Exposes Prometheus metrics directly without trailing slash redirects."""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

class SearchRequest(BaseModel):
    query: str
    user_id: str
    agent_id: Optional[str] = None
    limit: Optional[int] = 5
    score_threshold: Optional[float] = 1.0

class MemoryItem(BaseModel):
    id: str
    memory: str
    score: Optional[float] = None
    metadata: Optional[dict] = None

class SearchResponse(BaseModel):
    results: List[MemoryItem]
    total: int


@app.post("/search", response_model=SearchResponse)
async def search(req: SearchRequest):
    try:
        SEARCH_TOTAL.inc()
        start_time = time.monotonic()
        raw_results = memory_client.search(
            query=req.query,
            user_id=req.user_id,
            agent_id=req.agent_id,
            limit=req.limit
        )
        SEARCH_DURATION.observe(time.monotonic() - start_time)
        
        import logging
        api_logger = logging.getLogger("mem0-api")
        api_logger.info(f"DEBUG: raw_search_results: {raw_results}")

        results = []
        
        # Handle if raw_results is a dict with a 'results' or 'memories' key
        raw_list = []
        if isinstance(raw_results, dict):
            raw_list = raw_results.get("results", raw_results.get("memories", []))
        else:
            raw_list = raw_results

        # Mem0 search returns a list of dictionaries
        for r in raw_list:
            # Handle if r is a dict or an object
            memory_text = r.get("memory") if isinstance(r, dict) else getattr(r, "memory", "")
            memory_id = r.get("id") if isinstance(r, dict) else getattr(r, "id", "unknown")
            score = r.get("score", 0.0) if isinstance(r, dict) else getattr(r, "score", 0.0)
            metadata = r.get("metadata") if isinstance(r, dict) else getattr(r, "metadata", None)
            
            results.append(MemoryItem(
                id=memory_id,
                memory=memory_text,
                score=score,
                metadata=metadata
            ))
            
        # Filter by threshold if provided
        if req.score_threshold is not None:
            results = [r for r in results if r.score <= req.score_threshold]
            
        return SearchResponse(results=results, total=len(results))
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/memories", response_model=SearchResponse)
async def get_memories(user_id: str):
    try:
        import logging
        api_logger = logging.getLogger("mem0-api")
        raw_data = memory_client.get_all(user_id=user_id)
        api_logger.info(f"DEBUG: raw_data for user {user_id}: {raw_data}") 
        
        # Mem0 get_all returns a dict with a 'memories' key (list)
        # or sometimes a direct list depending on the provider/version
        raw_list = []
        if isinstance(raw_data, dict):
            # Mem0 can return results under 'memories' or 'results' key
            raw_list = raw_data.get("memories", raw_data.get("results", []))
        elif isinstance(raw_data, list):
            raw_list = raw_data
            
        results = []
        for m in raw_list:
            memory_text = m.get("memory") if isinstance(m, dict) else getattr(m, "memory", "")
            memory_id = m.get("id") if isinstance(m, dict) else getattr(m, "id", "unknown")
            metadata = m.get("metadata") if isinstance(m, dict) else getattr(m, "metadata", None)

            results.append(MemoryItem(
                id=memory_id,
                memory=memory_text,
                metadata=metadata
            ))
            
        return SearchResponse(results=results, total=len(results))
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/history")
async def get_history(user_id: Optional[str] = None, limit: int = 20):
    """Returns the last N events from the daily audit logs, optionally filtered by user_id."""
    try:
        events = []
        if os.path.exists(config.AUDIT_LOG_DIR):
            # List files in AUDIT_LOG_DIR and sort them by name descending (latest first)
            log_files = sorted(
                [f for f in os.listdir(config.AUDIT_LOG_DIR) if f.startswith("memory_audit_") and f.endswith(".jsonl")],
                reverse=True
            )

            for log_file in log_files:
                log_path = os.path.join(config.AUDIT_LOG_DIR, log_file)
                with open(log_path, "r") as f:
                    lines = f.readlines()
                    for line in reversed(lines):
                        event = json.loads(line)
                        if user_id and event.get("user_id") != user_id:
                            continue
                        events.append(event)
                        if len(events) >= limit:
                            return {"events": events}
        return {"events": events}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=config.MEM_API_PORT)
