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

    print("Running Incident Response Graph with Parallel Investigators...\n")
    final_state = app.invoke(initial_state)

    print("=== TIMELINE ===")
    for event in final_state["timeline"]:
        print(event)

    print("\n=== RANKED HYPOTHESES (DIAGNOSIS) ===")
    for idx, hyp in enumerate(final_state["hypotheses"], start=1):
        print(f"\nHypothesis #{idx} [Confidence: {hyp['confidence'] * 100:.0f}%]:")
        print(f"  Description: {hyp['description']}")
        print(f"  Mitigation : {hyp['recommended_mitigation']}")
        print("  Supporting Evidence:")
        for ev in hyp["supporting_evidence"]:
            print(f"    - {ev}")

if __name__ == "__main__":
    main()