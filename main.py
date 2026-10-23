import os
import uuid
from psycopg_pool import ConnectionPool
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.types import Command
from dotenv import load_dotenv

from ai_sre.graph import build_workflow, DATABASE_URL

load_dotenv()


def main():
    # Persistent connection pool to Postgres
    connection_kwargs = {"autocommit": True, "prepare_threshold": 0}
    
    with ConnectionPool(conninfo=DATABASE_URL, kwargs=connection_kwargs) as pool:
        checkpointer = PostgresSaver(pool)
        # Initializes checkpointer schema and tables if they don't exist
        checkpointer.setup()

        # Compile graph with Postgres checkpointer
        workflow = build_workflow()
        app = workflow.compile(checkpointer=checkpointer)

        print("Select Mode:")
        print("  [1] Start New Incident Alert Run")
        print("  [2] Resume an Existing Incident from Postgres by ID")
        mode = input("Choice (1 or 2): ").strip()

        if mode == "1":
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
                "loop_count": 0,
                "targeted_queries": [],
                "proposed_actions": [],
                "approved_action": None,
                "approval_status": "pending",
                "execution_result": None,
                "recovery_verified": False,
                "timeline": [f"[System] Incident created for {sample_alert['service']}"],
            }

            config = {"configurable": {"thread_id": incident_id}}

            print("\n" + "=" * 60)
            print(f"🚨 STARTING NEW INCIDENT: {incident_id}")
            print("=" * 60)

            # Runs until human interrupt
            app.invoke(initial_state, config=config)

            print(f"\n✅ Graph reached interrupt and state is persisted in Postgres!")
            print(f"Incident ID / Thread ID: {incident_id}")
            print("You can kill this process now or choose to resume it immediately.")

        elif mode == "2":
            incident_id = input("Enter Incident Thread ID to resume (e.g., INC-xxxxxx): ").strip()
            config = {"configurable": {"thread_id": incident_id}}

        else:
            print("Invalid option.")
            return

        # Check snapshot stored in Postgres
        snapshot = app.get_state(config)
        if not snapshot.tasks or not snapshot.tasks[0].interrupts:
            print("Graph is not waiting at an approval gate.")
            return

        interrupt_data = snapshot.tasks[0].interrupts[0].value
        proposed_actions = interrupt_data.get("proposed_actions", [])

        print("\n" + "-" * 60)
        print(f"🛑 LOADED FROM POSTGRES: HUMAN APPROVAL REQUIRED FOR {incident_id}")
        print("-" * 60)
        for idx, act in enumerate(proposed_actions, start=1):
            print(f"[{idx}] {act['action_type']} on {act['target_service']} (Risk: {act['risk_level']})")

        choice = input("\nEnter action number to approve, or 'r' to reject: ").strip().lower()

        if choice == "r":
            resume_payload = {"status": "rejected", "action": None}
        else:
            try:
                selected_action = proposed_actions[int(choice) - 1]
                resume_payload = {"status": "approved", "action": selected_action}
            except (ValueError, IndexError):
                resume_payload = {"status": "rejected", "action": None}

        print("\nResuming from Postgres checkpoint...")
        final_state = app.invoke(Command(resume=resume_payload), config=config)

        print("\n" + "=" * 60)
        print("📋 FINAL TIMELINE (RECOVERED & COMPLETED)")
        print("=" * 60)
        for event in final_state["timeline"]:
            print(event)


if __name__ == "__main__":
    main()