from typing import Any, Dict
from pydantic import BaseModel, Field
from ai_sre.state import IncidentState
from ai_sre.models import get_fast_llm

# Output schema for Intake
class AlertEvaluation(BaseModel):
  severity: str = Field(
      description="Incident severity: P1 (critical outage), P2 (major degradation), P3 (minor), or P4 (informational)"
  )
  summary: str = Field(
      description="A clean one-sentence summary of the alert"
  )

# Output schema for Triage

class TriageDecision(BaseModel):
  category: str = Field(
      description="Category: resource, deploy, dependency, or data"
  )
  target_investigators: list[str] = Field(
      description="List of investigators to trigger: 'logs', 'metrics', 'deploy'"
  )
  reasoning: str = Field(
      description="Why these investigators are needed"
  )

def intake_node(state : IncidentState) -> Dict[str, Any]:
  """Node 1. Parses raw alerts and establishes baseline incident metadata."""

  alert = state["alert"]
  llm = get_fast_llm().with_structured_output(AlertEvaluation)

  prompt = f"Analyze this production alert and assign severity (P1-P4): \n{alert}"

  result: AlertEvaluation = llm.invoke(prompt)

  return {
    "severity": result.severity,
    "timeline": [
        f"[Intake] Alert normalized. Severity set to {result.severity}: {result.summary}"
    ],
  }

def triage_node(state: IncidentState) -> Dict[str, Any]:
  """Node 2: Classifies failures types and plans investigation paths."""

  alert = state["alert"]
  severity = state["severity"]
  llm = get_fast_llm().with_structured_output(TriageDecision)

  prompt = f"""Given this {severity} alert:
    {alert}

    Classify category and choose which investigators to run ('logs', 'metrics', 'deploy')."""

  decision: TriageDecision = llm.invoke(prompt)

  return {
      "category": decision.category,
      "timeline": [
          f"[Triage] Classified as {decision.category}. Routing to: {', '.join(decision.target_investigators)}"
      ],
  }