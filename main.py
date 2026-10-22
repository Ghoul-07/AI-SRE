import uuid
from langgraph.types import Command
from ai_sre.graph import app

def main():
    incident_id = f"INC-{uuid.uuid4().hex[:6]}"
    sample_alert = {
        "service": "checkout-service",
        "metric": "http_5xx_rate",
        "threshold": "5%",
        "current_value": "24.5%",
        "timestamp": "2026-10-19T10:30:00Z",
        "message": "High rate of 500 errors observed after v2.4.1 rollout"
    }

    initial_state = {
        "incident_id": incident_id,
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

    # Thread config tracks the execution snapshot in the checkpointer
    config = {"configurable": {"thread_id": incident_id}}

    print("--- STEP 1: Running Graph Until Human Approval Interrupt ---")
    state = app.invoke(initial_state, config=config)

    # Check the state of the graph
    current_snapshot = app.get_state(config)
    print("\n[Graph Paused]")
    print(f"Next Node to Execute: {current_snapshot.next}")
    
    if current_snapshot.tasks and current_snapshot.tasks[0].interrupts:
        interrupt_payload = current_snapshot.tasks[0].interrupts[0].value
        print("\nInterrupt Payload from Agent:")
        print(f"  Message: {interrupt_payload['message']}")
        for action in interrupt_payload["proposed_actions"]:
            print(f"  Action: {action['action_type']} on {action['target_service']} (Risk: {action['risk_level']})")
            print(f"  Parameters: {action['parameters']}")
            print(f"  Expected Effect: {action['expected_effect']}")

    print("\n--- STEP 2: Human Resumes Graph with Approval ---")
    # Resume by sending a Command back to the same thread
    resumed_state = app.invoke(
        Command(resume={"status": "approved", "action": interrupt_payload["proposed_actions"][0]}),
        config=config
    )

    print("\n=== FINAL TIMELINE AFTER RESUME ===")
    for event in resumed_state["timeline"]:
        print(event)
    print(f"\nFinal Approval Status: {resumed_state['approval_status']}")
    print(f"Approved Action       : {resumed_state['approved_action']}")

if __name__ == "__main__":
    main()