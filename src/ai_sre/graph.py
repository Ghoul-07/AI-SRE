from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from ai_sre.state import IncidentState
from ai_sre.nodes import (
  intake_node, 
  triage_node, 
  log_investigator_node, 
  metrics_investigator_node, 
  deploy_investigator_node, 
  diagnosis_node,
  remediation_planner_node,
  human_approval_node,
  executor_node,
  postmortem_node)

def diagnosis_confidence_router(state: IncidentState) -> str:
    """
    Conditional Edge: Checks if confidence is high enough to proceed to remediation.
    Caps investigation loop at 2 iterations per PRD Section 6.2 Step 4.
    """
    hypotheses = state.get("hypotheses", [])
    top_confidence = hypotheses[0]["confidence"] if hypotheses else 0.0
    loop_count = state.get("loop_count", 0)

    # If confidence is below threshold and we haven't hit loop cap, loop back
    if top_confidence < 0.70 and loop_count < 2:
        return "reinvestigate"
    return "remediation_planner"

def approval_router(state:IncidentState) -> str:
  """routes based on human gate decision."""
  if state.get("approval_status") == "approved":
    return "executor"
  return "postmortem"


# initialize graph with state schema
workflow = StateGraph(IncidentState)

# register the nodes
workflow.add_node("intake", intake_node)
workflow.add_node("triage", triage_node)
workflow.add_node("log_investigator", log_investigator_node)
workflow.add_node("metrics_investigator", metrics_investigator_node)
workflow.add_node("deploy_investigator", deploy_investigator_node)
workflow.add_node("diagnosis", diagnosis_node)
workflow.add_node("remediation_planner", remediation_planner_node)
workflow.add_node("human_approval", human_approval_node)
workflow.add_node("executor", executor_node)
workflow.add_node("postmortem", postmortem_node)

# connect the nodes with edges

workflow.add_edge(START, "intake")
workflow.add_edge("intake", "triage")

# Fan-out: triage triggers all 3 investigators concurrently
workflow.add_edge("triage", "log_investigator")
workflow.add_edge("triage", "metrics_investigator")
workflow.add_edge("triage", "deploy_investigator")

# Fan-in: All 3 investigators merge in diagnosis
workflow.add_edge("log_investigator", "diagnosis")
workflow.add_edge("metrics_investigator", "diagnosis")
workflow.add_edge("deploy_investigator", "diagnosis")

workflow.add_conditional_edges(
  "diagnosis",
  diagnosis_confidence_router,
  {
    "reinvestigate": "log_investigator",
    "remediation_planner":"remediation_planner"
  }
)

workflow.add_edge("remediation_planner", "human_approval")

workflow.add_conditional_edges(
  "human_approval",
  approval_router,
  {
    "executor":"executor",
    "postmortem":"postmortem"
  }
)

workflow.add_edge("executor", "postmortem")
workflow.add_edge("postmortem", END)

checkpointer = MemorySaver()
app = workflow.compile(checkpointer=checkpointer)

