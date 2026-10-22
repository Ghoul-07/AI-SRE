from typing import Annotated, Any, Dict, List, Optional
from typing_extensions import TypedDict
import operator

def append_list(existing : List[Any], new : List[Any]) -> List[Any]:
  """Helper to append items to a list instead of overwriting."""
  return existing + new

class IncidentState(TypedDict):
  # Core incident identifiers
  incident_id: str
  alert: Dict[str, Any]
  severity: str
  category: Optional[str]

  # Reducer: operator.add or custom appender allows parallel branches
  # to add findings without wiping each other out
  findings: Annotated[List[Dict[str, Any]], append_list]
  hypotheses: Annotated[List[Dict[str, Any]], append_list]

  # Loop tracking and targeted follow up queries
  loop_count: int
  targeted_queries: List[str]

  # Action and human approval gate
  proposed_actions: List[Dict[str, Any]]
  approved_action: Optional[Dict[str, Any]]
  approval_status: str  # 'pending', 'approved', 'rejected'
  
  # Execution & post-recovery
  execution_result: Optional[Dict[str, Any]]
  recovery_verified: bool
  
  # Audit trail & token tracking
  timeline: Annotated[List[str], append_list]
  

