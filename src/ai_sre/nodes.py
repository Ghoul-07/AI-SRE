from typing import Any, Dict, Literal, Optional
from pydantic import BaseModel, Field
from langgraph.types import interrupt
from ai_sre.state import IncidentState
from ai_sre.models import get_fast_llm, get_reasoning_llm
from ai_sre.tools import query_logs, query_metrics, query_deploys, execute_sandbox_action



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
    targeted = state.get("targeted_queries", [])

    # if targeted_queries exist, use latest filters
    query_filter = targeted[-1] if targeted else ""
    raw_logs = query_logs(service=service, query_filter=query_filter)

    llm = get_fast_llm().with_structured_output(InvestigationReport)

    prompt = f"""You are an SRE Log Investigator.
        Service: '{service}'
        Targeted Filter Applied: '{query_filter}'
        Raw Logs:
        {raw_logs}

        Extract any error patterns, exceptions, or anomalies as structured findings with exact evidence."""

    report: InvestigationReport = llm.invoke(prompt)
    findings_data = [f.model_dump() for f in report.findings]
    
    label = f"[Log Investigator (Targeted: '{query_filter}')]" if query_filter else "[Log Investigator]"
    return {
        "findings": findings_data,
        "timeline": [f"{label} {report.agent_note} (Found {len(findings_data)} clues)"],
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


# Structured diagnosis output
class Hypothesis(BaseModel):
   description:str = Field(description="Clear explaination of the suspected root cause")
   confidence:float = Field(description="Confidence score between 0.0 and 1.0")
   supporting_evidence: list[str] = Field(description="List of specific log, metric, or deploy evidence snippets supporting this")
   recommended_mitigation: str = Field(description="Immediate action recommended to restore service")

class DiagnosisReport(BaseModel):
   hypotheses: list[Hypothesis] = Field(description="Ranked list of root-cause hypotheses, highest confidence first")
   synthesis_summary: str = Field(description="Summary explaining how cross-source evidence correlates")
   needs_more_data: bool = Field(description="True if top confidence is below 0.7 and targeted investigation is needed")
   targeted_queries: Optional[list[str]] = Field(
      default=None,
      description="Specific follow-up queries or log filters if more data is needed"
    )


def diagnosis_node(state: IncidentState) -> Dict[str, Any]:
   """Fan-In Node: Correlates cross-source findings into ranked root-cause hypotheses; triggers targeted queries if confidence is low."""
   findings = state["findings"]
   alert = state["alert"]
   current_loops = state.get("loop_count", 0)
   llm = get_reasoning_llm().with_structured_output(DiagnosisReport)

   prompt = f"""You are the lead SRE Incident Commander and Diagnostic specialist.
   An incident is ongoing. Review the initial alert and the evidence gathered by parallel investigators:

   Alert Context:
   {alert}

   Accumulated Evidence ({len(findings)} across logs, metricsc and deploys):
   {findings}

   Current investigation iteration: {current_loops}
   Synthesize the evidence across sources. Correlate timestamps, error codes, and release changes.
   Rank root cause hypotheses by confidence and link concrete supporting evidence to each
   If top hypothesis confidence is < 0.70, set needs_more_data to True and supply 1-2 targeted_queries (e.g., specific log search terms or metric checks) to clarify root cause..
   """

   report: DiagnosisReport = llm.invoke(prompt)

   hypotheses_data = [h.model_dump() for h in report.hypotheses]
   top_confidence = hypotheses_data[0]["confidence"] if hypotheses_data else 0.0

   return {
        "hypotheses": hypotheses_data,
        "targeted_queries": report.targeted_queries if report.needs_more_data else [],
        "loop_count": current_loops + 1,
        "timeline": [
            f"[Diagnosis (Round {current_loops + 1})] Synthesized findings into {len(hypotheses_data)} hypotheses. Top confidence: {top_confidence:.2f} (Needs more data: {report.needs_more_data})"
        ]
    }


# Strict allowed actions list 
ActionType = Literal["rollback_deploy", "restart_service", "scale_replicas", "clear_cache"]

class ProposedAction(BaseModel):
    action_type: ActionType = Field(description="Must be one of the allow-listed action types")
    target_service: str = Field(description="Service targeted by the remediation")
    parameters: Dict[str, Any] = Field(description="Specific arguments, e.g., target version or replica count")
    expected_effect: str = Field(description="Anticipated outcome of this action on service health")
    risk_level: Literal["low", "medium", "high"] = Field(description="Potential blast radius or operational risk")
    rollback_plan: str = Field(description="What to do if this remediation fails")

class RemediationPlan(BaseModel):
    actions: list[ProposedAction]
    reasoning: str = Field(description="Why this sequence of actions was chosen based on top hypothesis")


def remediation_planner_node(state:IncidentState) -> Dict[str, Any]:
    """Node: Formulates safe remediation steps based on the top ranked hypothesis."""
    top_hypothesis = state["hypotheses"][0] if state["hypotheses"] else None
    service = state["alert"].get("service", "unknown")

    if not top_hypothesis:
        return {
            "proposed_actions": [],
            "approval_status": "rejected",
            "timeline": ["[Remediation Planner] No valid hypothesis to act on. Aborting remediation."]
        }

    llm = get_fast_llm().with_structured_output(RemediationPlan)

    prompt = f"""You are an SRE Remediation Planner.
        Top Root Cause Hypothesis:
        {top_hypothesis}

        Target Service: {service}

        Allowed actions:
        - rollback_deploy (requires parameter: 'target_version')
        - restart_service
        - scale_replicas (requires parameter: 'replicas')
        - clear_cache

        Propose a remediation plan using ONLY the allowed action types."""

    plan = llm.invoke(prompt)
    actions_data = [a.model_dump() for a in plan.actions]

    return {
       "proposed_actions" : actions_data,
       "approval_status": "pending",
       "timeline":[
          f"[Remediation Planner] Proposed {len(actions_data)} action(s). Awaiting human approval."
       ]
    }
   

def human_approval_node(state: IncidentState) -> Dict[str, Any]:
   """Node: Pauses graph execution and yields control to human-in-the-loop."""

   pending_actions = state["proposed_actions"]

   ## pauses the graph exection and waits for human input
   human_decision = interrupt({
      "message": "Human approval required to execute remediation.",
      "proposed_actions":pending_actions
   })

   decision_status = human_decision.get("status", "rejected")
   approved_action = human_decision.get("action", pending_actions[0] if pending_actions else None)

   return {
      "approval_status": decision_status,
      "approved_action": approved_action if decision_status == "approved" else None,
      "timeline": [f"[Human Gate] Incident Commander decision: {decision_status.upper()}"]
   }


## Executor and Postmortem nodes

class PostmortemReport(BaseModel):
    title: str = Field(description="Incident title with ID and service")
    severity: str = Field(description="Incident severity level")
    root_cause: str = Field(description="Detailed explanation of the root cause")
    impact: str = Field(description="Summary of client and service impact")
    remediation_summary: str = Field(description="Action taken and verification result")
    action_items: list[str] = Field(description="Preventative follow-ups and engineering action items")


def executor_node(state: IncidentState) -> Dict[str, Any]:
    """Node: Executes the approved remediation against the sandbox and verifies recovery."""
    action = state.get("approved_action")
    if not action:
        return {
            "execution_result": {"status": "skipped", "reason": "No approved action found"},
            "recovery_verified": False,
            "timeline": ["[Executor] Skipped execution: no approved action."]
        }

    # Execute via guarded allow-listed tool
    result = execute_sandbox_action(
        action_type=action["action_type"],
        target_service=action["target_service"],
        parameters=action.get("parameters", {})
    )

    is_recovered = result.get("status") == "success" and result.get("verified_metrics", {}).get("status") == "healthy"

    return {
        "execution_result": result,
        "recovery_verified": is_recovered,
        "timeline": [
            f"[Executor] Executed {action['action_type']} on {action['target_service']}. Outcome: {result.get('status').upper()}",
            f"[Executor] Recovery verified: {is_recovered} (5xx rate dropped to {result.get('verified_metrics', {}).get('http_5xx_rate', 'N/A')})"
        ]
    }


def postmortem_node(state: IncidentState) -> Dict[str, Any]:
    """Node: Synthesizes the full incident timeline into an SRE postmortem document."""
    llm = get_fast_llm().with_structured_output(PostmortemReport)

    prompt = f"""You are a Lead SRE writing an incident postmortem report.
        Incident Data:
        - ID: {state.get('incident_id')}
        - Alert: {state.get('alert')}
        - Severity: {state.get('severity')}
        - Category: {state.get('category')}
        - Top Hypotheses: {state.get('hypotheses')}
        - Approved Action: {state.get('approved_action')}
        - Execution Result: {state.get('execution_result')}
        - Recovery Verified: {state.get('recovery_verified')}
        - Timeline: {state.get('timeline')}

        Generate a comprehensive postmortem report following standard SRE practices."""

    report: PostmortemReport = llm.invoke(prompt)

    # Format into clean Markdown
    markdown_doc = f"""# Incident Postmortem: {report.title}

**Severity:** {report.severity} | **Recovery Verified:** {state.get('recovery_verified')}

## Root Cause
{report.root_cause}

## Impact
{report.impact}

## Remediation Summary
{report.remediation_summary}

## Action Items
""" + "\n".join([f"- [ ] {item}" for item in report.action_items])

    return {
        "timeline": [
            "[Postmortem Writer] Postmortem report generated successfully."
        ],
        "findings": [{"source": "postmortem", "summary": "Postmortem Markdown Generated", "evidence": markdown_doc, "significance": "normal"}]
    }