import uuid
from ai_sre.graph import app

def main():
    sample_alert = {
        "service": "checkout-service",
        "metric": "http_5xx_rate",
        "threshold": "5%",
        "current_value": "24.5%",
        "timestamp": "2026-10-19T10:30:00Z",
        "message": "High rate of 500 errors observed after v2.4.1 rollout"
    }

    # Prepare initial state
    initial_state = {
        "incident_id": f"INC-{uuid.uuid4().hex[:6]}",
        "alert": sample_alert,
        "severity": "",
        "category": None,
        "findings": [],
        "hypotheses": [],
        "proposed_actions": [],
        "approved_action": None,
        "approval_status": "pending",
        "execution_result": None,
        "recovery_verified": False,
        "timeline": [f"[System] Incident created for {sample_alert['service']}"]
    }

    print("Running Incident Response Graph...\n")
    final_state = app.invoke(initial_state)

    print("--- Execution Summary ---")
    print(f"Incident ID : {final_state['incident_id']}")
    print(f"Severity    : {final_state['severity']}")
    print(f"Category    : {final_state['category']}")
    print("\n--- Timeline Output ---")
    for event in final_state["timeline"]:
        print(event)

if __name__ == "__main__":
    main()