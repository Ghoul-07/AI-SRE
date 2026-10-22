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
        "message": "High rate of 500 errors observed after v2.4.1 rollout",
    }

    initial_state = {
        "incident_id": incident_id,
        "alert": sample_alert,
        "severity": "",
        "category": None,
        "findings": [],
        "hypotheses": [],
        "loop_count":0,
        "targeted_queries":[],
        "proposed_actions": [],
        "approved_action": None,
        "approval_status": "pending",
        "execution_result": None,
        "recovery_verified": False,
        "timeline": [f"[System] Incident created for {sample_alert['service']}"],
    }

    config = {"configurable": {"thread_id": incident_id}}

    print("=" * 60)
    print(f" STARTING INCIDENT PIPELINE [{incident_id}]")
    print("=" * 60)

    # 1. Run the graph until the interrupt pauses it
    app.invoke(initial_state, config=config)

    # 2. Inspect the graph checkpoint
    snapshot = app.get_state(config)

    # Check if the graph is waiting at the human gate
    if not snapshot.tasks or not snapshot.tasks[0].interrupts:
        print("Graph finished without requiring approval.")
        return

    interrupt_data = snapshot.tasks[0].interrupts[0].value
    proposed_actions = interrupt_data.get("proposed_actions", [])

    print("\n🛑 AGENT PAUSED: HUMAN APPROVAL REQUIRED")
    print("-" * 60)
    print(f"Message: {interrupt_data.get('message')}")
    print("\nProposed Actions from Remediation Planner:")
    for idx, act in enumerate(proposed_actions, start=1):
        print(f"\n[{idx}] Action    : {act['action_type']}")
        print(f"    Service   : {act['target_service']}")
        print(f"    Risk Level: {act['risk_level'].upper()}")
        print(f"    Parameters: {act['parameters']}")
        print(f"    Expected  : {act['expected_effect']}")

    print("\n" + "-" * 60)
    print("Choose an option:")
    print("  [1-N] Approve a specific action by number")
    print("  [r]   Reject all actions (proceed directly to postmortem)")
    print("-" * 60)

    # 3. Read real human input from the terminal
    user_choice = input("Enter choice: ").strip().lower()

    if user_choice == "r":
        resume_payload = {
            "status": "rejected",
            "action": None,
        }
        print("\n❌ Action rejected by Incident Commander.")
    else:
        try:
            choice_idx = int(user_choice) - 1
            if 0 <= choice_idx < len(proposed_actions):
                selected_action = proposed_actions[choice_idx]
                resume_payload = {
                    "status": "approved",
                    "action": selected_action,
                }
                print(
                    f"\n✅ Approved Action: {selected_action['action_type']} on {selected_action['target_service']}"
                )
            else:
                print("\nInvalid selection. Defaulting to rejection.")
                resume_payload = {"status": "rejected", "action": None}
        except ValueError:
            print("\nInvalid input. Defaulting to rejection.")
            resume_payload = {"status": "rejected", "action": None}

    # 4. Resume the graph using the human choice
    print("\nResuming graph execution...")
    final_state = app.invoke(Command(resume=resume_payload), config=config)

    print("\n" + "=" * 60)
    print("📋 FINAL INCIDENT TIMELINE")
    print("=" * 60)
    for event in final_state["timeline"]:
        print(event)

    # Display postmortem
    postmortem = next(
        (f for f in final_state["findings"] if f["source"] == "postmortem"), None
    )
    if postmortem:
        print("\n" + "=" * 60)
        print(postmortem["evidence"])
        print("=" * 60)


if __name__ == "__main__":
    main()