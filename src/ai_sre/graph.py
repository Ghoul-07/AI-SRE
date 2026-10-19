from langgraph.graph import StateGraph, START, END
from ai_sre.state import IncidentState
from ai_sre.nodes import intake_node, triage_node, log_investigator_node, metrics_investigator_node, deploy_investigator_node

# initialize graph with state schema
workflow = StateGraph(IncidentState)

# register the nodes
workflow.add_node("intake", intake_node)
workflow.add_node("triage", triage_node)
workflow.add_node("log_investigator", log_investigator_node)
workflow.add_node("metrics_investigator", metrics_investigator_node)
workflow.add_node("deploy_investigator", deploy_investigator_node)

# connect the nodes with edges
# START -> intake -> triage
workflow.add_edge(START, "intake")
workflow.add_edge("intake", "triage")

# Fan-out: triage triggers all 3 investigators concurrently
workflow.add_edge("triage", "log_investigator")
workflow.add_edge("triage", "metrics_investigator")
workflow.add_edge("triage", "deploy_investigator")

# All three route to END for now
workflow.add_edge("log_investigator", END)
workflow.add_edge("metrics_investigator", END)
workflow.add_edge("deploy_investigator", END)

app = workflow.compile()

