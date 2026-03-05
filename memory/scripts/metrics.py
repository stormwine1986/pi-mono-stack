"""
Pi Memory Subsystem — Prometheus Metrics Registry
All custom metrics are defined here for centralized management.
"""
from prometheus_client import Counter, Gauge, Histogram

# =====================================================
# Phase 1: Process-level metrics are auto-collected
#           by prometheus_client's ProcessCollector.
#           No manual definitions needed.
# =====================================================

# =====================================================
# Phase 2: Worker & Observer core pipeline
# =====================================================

# Observer: messages consumed from Redis Streams
OBSERVER_MESSAGES = Counter(
    "memory_observer_messages_total",
    "Total messages consumed by the Memory Observer",
    ["stream", "action"],  # stream=agent_in|agent_out, action=cached|paired|skipped|prompt_miss
)

# Worker: serial thread pool queue depth
WORKER_QUEUE_SIZE = Gauge(
    "memory_worker_queue_size",
    "Number of dehydration tasks pending in the serial worker pool",
)

# Worker: end-to-end extraction duration (mem0.add)
EXTRACTION_DURATION = Histogram(
    "memory_extraction_duration_seconds",
    "Duration of a single memory extraction via Mem0 SDK",
    ["status"],  # success / failed
    buckets=[0.5, 1, 2, 5, 10, 20, 30, 60],
)

# Worker: extraction task count
EXTRACTION_TOTAL = Counter(
    "memory_extraction_total",
    "Total extraction tasks processed",
    ["status"],  # success / failed
)

# =====================================================
# Phase 3: API & Audit layer
# =====================================================

# API: search latency
SEARCH_DURATION = Histogram(
    "memory_search_duration_seconds",
    "Duration of a /search request",
    buckets=[0.05, 0.1, 0.25, 0.5, 1, 2, 5],
)

# API: search count
SEARCH_TOTAL = Counter(
    "memory_search_total",
    "Total /search requests served",
)

# Audit: memory alteration events
AUDIT_EVENTS = Counter(
    "memory_audit_events_total",
    "Total memory alteration events recorded by auditor",
    ["action"],  # ADD / UPDATE / DELETE
)

# =====================================================
# Initialization (to ensure metrics show up as 0)
# =====================================================
def init_metrics():
    # Observer
    for stream in ["agent_in", "agent_out"]:
        for action in ["cached", "paired", "skipped", "prompt_miss"]:
            OBSERVER_MESSAGES.labels(stream=stream, action=action).inc(0)
    
    # Extraction
    for status in ["success", "failed"]:
        EXTRACTION_DURATION.labels(status=status).observe(0)
        EXTRACTION_TOTAL.labels(status=status).inc(0)
    
    # Audit
    for action in ["ADD", "UPDATE", "DELETE"]:
        AUDIT_EVENTS.labels(action=action).inc(0)

init_metrics()

