from typing import Any, Dict
from pydantic import BaseModel, Field
from ai_sre.state import IncidentState
from ai_sre.models import get_fast_llm
from ai_sre.tools import query_logs, query_metrics, query_deploys

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

from ai_sre.tools import query_logs, query_metrics, query_deploys


# Strict finding schema 
class InvestigationFinding(BaseModel):
    source: str = Field(description="Must be 'logs', 'metrics', or 'deploy'")
    summary: str = Field(description="One-line finding summary")
    evidence: str = Field(
        description="Exact log message, metric query value, or commit reference"
    )
    significance: str = Field(
        description="Significance: 'critical', 'warning', or 'normal'"
    )


class InvestigationReport(BaseModel):
    findings: list[InvestigationFinding]
    agent_note: str = Field(description="Brief summary of the investigator's verdict")


def log_investigator_node(state: IncidentState) -> Dict[str, Any]:
    """Node: Inspects raw logs around the alert window."""
    service = state["alert"].get("service", "unknown")
    raw_logs = query_logs(service=service)

    llm = get_fast_llm().with_structured_output(InvestigationReport)
    prompt = f"""You are an SRE Log Investigator.
      Analyze these raw logs for service '{service}' during the incident window:
      {raw_logs}

      Extract any error patterns, exceptions, or anomalies as structured findings with exact evidence."""

    report: InvestigationReport = llm.invoke(prompt)

    findings_data = [f.model_dump() for f in report.findings]
    return {
        "findings": findings_data,
        "timeline": [f"[Log Investigator] {report.agent_note} (Found {len(findings_data)} clues)"],
    }


def metrics_investigator_node(state: IncidentState) -> Dict[str, Any]:
    """Node: Checks latency, error rates, CPU, and saturation."""
    service = state["alert"].get("service", "unknown")
    telemetry = query_metrics(service=service)

    llm = get_fast_llm().with_structured_output(InvestigationReport)
    prompt = f"""You are an SRE Metrics Investigator.
      Analyze these system and application metrics for service '{service}':
      {telemetry}

      Alert context:
      {state['alert']}

      Extract metric anomalies and saturation patterns with exact numerical evidence."""

    report: InvestigationReport = llm.invoke(prompt)

    findings_data = [f.model_dump() for f in report.findings]
    return {
        "findings": findings_data,
        "timeline": [f"[Metrics Investigator] {report.agent_note} (Found {len(findings_data)} clues)"],
    }


def deploy_investigator_node(state: IncidentState) -> Dict[str, Any]:
    """Node: Cross-references recent releases, commits, and config changes."""
    service = state["alert"].get("service", "unknown")
    deploy_history = query_deploys(service=service)

    llm = get_fast_llm().with_structured_output(InvestigationReport)
    prompt = f"""You are an SRE Deploy Investigator.
      Analyze recent deployment history for service '{service}' relative to the incident:
      {deploy_history}

      Identify suspect releases, rollback candidates, or schema changes."""

    report: InvestigationReport = llm.invoke(prompt)

    findings_data = [f.model_dump() for f in report.findings]
    return {
        "findings": findings_data,
        "timeline": [f"[Deploy Investigator] {report.agent_note} (Found {len(findings_data)} clues)"],
    }


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