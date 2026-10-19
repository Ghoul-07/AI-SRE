from langgraph.graph import StateGraph, START, END
from ai_sre.state import IncidentState
from ai_sre.nodes import intake_node, triage_node

# initialize graph with state schema
workflow = StateGraph(IncidentState)

# register the nodes
workflow.add_node("intake", intake_node)
workflow.add_node("triage", triage_node)

# connect the nodes with edges
# START -> intake -> triage -> END
workflow.add_edge(START, "intake")
workflow.add_edge("intake", "triage")
workflow.add_edge("triage", END)

app = workflow.compile()

