from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from mem0_client import memory_client
from config import config

app = FastAPI(title="Pi Memory Service")

class SearchRequest(BaseModel):
    query: str
    user_id: str
    agent_id: Optional[str] = None
    limit: Optional[int] = 5

class MemoryItem(BaseModel):
    id: str
    memory: str
    score: Optional[float] = None
    metadata: Optional[dict] = None

class SearchResponse(BaseModel):
    results: List[MemoryItem]
    total: int

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "embedder": config.LLAMA_EMBEDDING_URL,
        "llm": config.LLAMA_SERVER_URL,
        "dimensions": config.EMBEDDING_DIMS
    }

@app.post("/search", response_model=SearchResponse)
async def search(req: SearchRequest):
    try:
        raw_results = memory_client.search(
            query=req.query,
            user_id=req.user_id,
            agent_id=req.agent_id,
            limit=req.limit
        )
        
        results = []
        # Mem0 search returns a list of dictionaries
        for r in raw_results:
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=config.MEM_API_PORT)
