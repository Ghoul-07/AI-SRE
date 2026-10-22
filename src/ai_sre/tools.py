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

def execute_sandbox_action(action_type: str, target_service: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
    """
    Executes an action against the sandboxed target environment.
    Guarded by strict allow-list per PRD Section 8.
    """
    allowed_actions = ["rollback_deploy", "restart_service", "scale_replicas", "clear_cache"]
    if action_type not in allowed_actions:
        return {
            "status": "failed",
            "error": f"Action '{action_type}' is not in the allow-list: {allowed_actions}"
        }

    # Simulate sandbox execution effect
    if action_type == "rollback_deploy":
        target_version = parameters.get("target_version", "v2.4.0")
        return {
            "status": "success",
            "message": f"Successfully rolled back {target_service} to {target_version}",
            "verified_metrics": {
                "http_5xx_rate": "0.2%",
                "p99_latency_ms": 110,
                "status": "healthy"
            }
        }
    elif action_type == "restart_service":
        return {
            "status": "success",
            "message": f"Service {target_service} restarted cleanly.",
            "verified_metrics": {"status": "healthy"}
        }
    elif action_type == "scale_replicas":
        replicas = parameters.get("replicas", 3)
        return {
            "status": "success",
            "message": f"Scaled {target_service} replicas to {replicas}.",
            "verified_metrics": {"status": "healthy"}
        }
    elif action_type == "clear_cache":
        return {
            "status": "success",
            "message": f"Cache cleared for {target_service}.",
            "verified_metrics": {"status": "healthy"}
        }

    return {"status": "failed", "error": "Unknown execution failure"}