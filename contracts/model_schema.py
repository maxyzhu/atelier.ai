from pydantic import BaseModel
from enum import Enum
from typing import Optional
from uuid import uuid4


# ============================================================
# Scoring Type Definitions
# ============================================================


class CriteriaType(str, Enum):
    NUMERIC = "numeric"
    BOOLEAN = "boolean"
    RANGE = "range"
    COUNT = "count"
    MATCH = "match"
    VISUAL = "visual"


class NumericCriteria(BaseModel):
    id: str
    description: str
    type: CriteriaType = CriteriaType.NUMERIC
    target: float
    tolerance: float
    unit: str  # "m" | "mm" | "deg" | "count"


class BooleanCriteria(BaseModel):
    id: str
    description: str
    type: CriteriaType = CriteriaType.BOOLEAN
    expected: bool


class RangeCriteria(BaseModel):
    id: str
    description: str
    type: CriteriaType = CriteriaType.RANGE
    min: float
    max: float
    unit: str


class CountCriteria(BaseModel):
    id: str
    description: str
    type: CriteriaType = CriteriaType.COUNT
    target: int
    tolerance: int


class MatchCriteria(BaseModel):
    id: str
    description: str
    type: CriteriaType = CriteriaType.MATCH
    expected: str


class VisualCriteria(BaseModel):
    id: str
    description: str
    type: CriteriaType = CriteriaType.VISUAL
    check_description: str
    viewpoint: str


Criteria = (
    NumericCriteria
    | BooleanCriteria
    | RangeCriteria
    | CountCriteria
    | MatchCriteria
    | VisualCriteria
)


# ============================================================
# Schema 1: Gateway Input (Human → Gateway)
# ============================================================


class GatewayInput(BaseModel):
    request: str
    file_location: str
    # Auto-generated
    request_id: str = ""

    def model_post_init(self, __context):
        if not self.request_id:
            self.request_id = str(uuid4())


# ============================================================
# Schema 2: Gateway ↔ SubLLM Communication
# ============================================================


class AgentName(str, Enum):
    MODELING_3D = "3DModelingLLM"
    MATERIAL = "MaterialLLM"
    EXPORT_VIEW = "ExportViewLLM"
    CHECK = "CheckLLM"


class ScoringStandards(BaseModel):
    criteria: list[Criteria]
    pass_threshold: str = "all_criteria_met"


class TaskContext(BaseModel):
    file_location: str
    notes: str = ""


class TaskDispatch(BaseModel):
    task_id: str
    agent: AgentName
    request: str
    scoring_standards: ScoringStandards
    context: TaskContext
    max_iterations: int = 3


class ScoreResult(BaseModel):
    criteria_id: str
    passed: bool
    actual_value: float | int | bool | str
    confidence: float
    note: str = ""


class ContextUpdates(BaseModel):
    modifications_made: str
    model_state_summary: str


class TaskStatus(str, Enum):
    COMPLETED = "completed"
    MAX_ITERATIONS_REACHED = "max_iterations_reached"


class TaskComplete(BaseModel):
    task_id: str
    agent: AgentName
    status: TaskStatus
    iterations_used: int
    self_scores: list[ScoreResult]
    context_updates: ContextUpdates


# ============================================================
# Schema 3: FSM State
# ============================================================


class AgentStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    PASSED = "passed"
    FAILED_LOCKED = "failed_locked"


class AgentState(BaseModel):
    status: AgentStatus = AgentStatus.PENDING
    rework_count: int = 0


class TerminationReason(str, Enum):
    ALL_PASSED = "all_passed"
    MAX_REWORK_REACHED = "max_rework_reached"
    NONE = ""


class FSMState(BaseModel):
    request_id: str
    current_phase: AgentName
    pipeline: list[AgentName] = [
        AgentName.MODELING_3D,
        AgentName.MATERIAL,
        AgentName.EXPORT_VIEW,
        AgentName.CHECK,
    ]
    agents: dict[AgentName, AgentState]
    terminal: bool = False
    termination_reason: TerminationReason = TerminationReason.NONE

    # FSM rework logic:
    # 1. Find earliest failed agent from CheckLLM result
    # 2. Lock all agents before it (status → passed)
    # 3. Reset it and all downstream agents to pending
    # 4. Increment rework_count on the failed agent
    # 5. If rework_count > 2 → failed_locked, continue pipeline, return with warning


# ============================================================
# Schema 4: Gateway ↔ CheckLLM Communication
# ============================================================


class SubLLMResult(BaseModel):
    agent: AgentName
    status: TaskStatus
    self_scores: list[ScoreResult]
    context_updates: ContextUpdates


class CheckInput(BaseModel):
    task_id: str
    agent: AgentName = AgentName.CHECK
    original_request: str
    overall_scoring_standards: ScoringStandards
    context: TaskContext
    sub_llm_results: list[SubLLMResult]


class OverallStatus(str, Enum):
    PASSED = "passed"
    FAILED = "failed"


class ReworkRecommendation(BaseModel):
    earliest_failed_agent: AgentName
    reason: str


class CheckOutput(BaseModel):
    task_id: str
    agent: AgentName = AgentName.CHECK
    overall_status: OverallStatus
    overall_scores: list[ScoreResult]
    rework_recommendation: Optional[ReworkRecommendation] = None


# ============================================================
# Schema 5: Gateway → Outside (Final Response)
# ============================================================


class ResponseStatus(str, Enum):
    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"
    FAILED = "failed"


class AgentSummary(BaseModel):
    agent: AgentName
    status: AgentStatus
    iterations_used: int = 0
    rework_count: int = 0


class Warning(BaseModel):
    agent: AgentName
    issue: str
    criteria_id: str


class PipelineSummary(BaseModel):
    total_rework_cycles: int = 0
    agents: list[AgentSummary]


class GatewayResponse(BaseModel):
    request_id: str
    status: ResponseStatus
    original_request: str
    file_location: str
    overall_scores: list[ScoreResult]
    pipeline_summary: PipelineSummary
    warnings: list[Warning] = []
