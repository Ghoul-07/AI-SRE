from typing import Any, Dict, List

# Simulated telemetry datastore
MOCK_LOGS = [
    {"timestamp": "2026-10-19T10:25:00Z", "service": "checkout-service", "level": "INFO", "message": "Service started successfully on port 8080"},
    {"timestamp": "2026-10-19T10:28:12Z", "service": "checkout-service", "level": "ERROR", "message": "NullPointerException at PaymentGatewayAdapter.java:42"},
    {"timestamp": "2026-10-19T10:29:45Z", "service": "checkout-service", "level": "ERROR", "message": "Failed to serialize payment token payload; aborting transaction"},
    {"timestamp": "2026-10-19T10:30:02Z", "service": "checkout-service", "level": "ERROR", "message": "HTTP 500 returned to client for endpoint /api/v1/checkout"},
]

MOCK_METRICS = {
    "checkout-service": {
        "http_5xx_rate": "24.5%",
        "p99_latency_ms": 320,
        "cpu_utilization": "18%",
        "memory_usage_mb": 412
    }
}

MOCK_DEPLOYS = [
    {"version": "v2.4.0", "deployed_at": "2026-10-18T14:00:00Z", "author": "dev-alice", "status": "stable"},
    {"version": "v2.4.1", "deployed_at": "2026-10-19T10:20:00Z", "author": "dev-bob", "commit": "Update payment processor schema", "status": "deployed"},
]


def query_logs(service: str, query_filter: str = "") -> List[Dict[str, Any]]:
    """Fetches recent log entries matching the service and an optional filter string."""
    entries = [entry for entry in MOCK_LOGS if entry["service"] == service]
    if query_filter:
        entries = [e for e in entries if query_filter.lower() in e["message"].lower() or query_filter.lower() in e["level"].lower()]
    return entries


def query_metrics(service: str) -> Dict[str, Any]:
    """Retrieves current operational metrics for a given target service."""
    return MOCK_METRICS.get(service, {})


def query_deploys(service: str) -> List[Dict[str, Any]]:
    """Retrieves deployment history and recent releases for a target service."""
    return MOCK_DEPLOYS