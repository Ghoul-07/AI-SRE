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
  human_approval_node)

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

workflow.add_edge("diagnosis", "remediation_planner")
workflow.add_edge("remediation_planner", "human_approval")
workflow.add_edge("human_approval", END)

checkpointer = MemorySaver()
app = workflow.compile(checkpointer=checkpointer)

