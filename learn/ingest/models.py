"""V4 自进化系统核心数据模型

所有数据结构使用 frozen dataclass —— 信号一旦生成不可变。
Pydantic 用于持久化数据的 schema 校验。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Literal

# ============================================================
# 枚举
# ============================================================


class SignalType(str, Enum):
    CORRECTION = "correction"
    SUPPLEMENT = "supplement"
    REFINEMENT = "refinement"
    EXTENSION = "extension"
    REINFORCEMENT = "reinforcement"
    COUNTERFACTUAL = "counterfactual"
    PREFERENCE_CHART = "preference_chart"
    PREFERENCE_REPORT = "preference_report"
    L3_FALLBACK = "l3_fallback"
    L1_MISS = "l1_miss"


class TriggerSource(str, Enum):
    NEW_QUERY = "new_query"
    CORRECTION = "correction"
    FOLLOW_UP = "follow_up"


class TimePeriod(str, Enum):
    MONTH_END = "month_end"
    PROMO_PERIOD = "promo_period"
    QUARTER_END = "quarter_end"
    NORMAL = "normal"


class HypothesisType(str, Enum):
    KEYWORD_ADJUSTMENT = "keyword_adjustment"
    INDICATOR_WEIGHT = "indicator_weight"
    INDICATOR_COMBINATION = "indicator_combination"
    TEMPLATE_ROUTING = "template_routing"
    TEMPLATE_CONTENT = "template_content"
    TEMPLATE_DISCOVERY = "template_discovery"
    INTENT_NEW = "intent_new"
    PREFERENCE_CHART = "preference_chart"
    PREFERENCE_REPORT = "preference_report"


class HypothesisStatus(str, Enum):
    PENDING_VALIDATION = "pending_validation"
    FULL_APPLIED = "full_applied"
    PROGRESSIVE = "progressive"
    MATURE = "mature"
    FROZEN = "frozen"
    DEFUNCT = "defunct"
    DISCARDED = "discarded"
    DRAFT = "draft"


class DetectionMethod(str, Enum):
    DISJOINT = "disjoint_indicators"
    PARTIAL_REPLACEMENT = "partial_replacement_with_negation"
    PURE_ADDITION = "pure_addition"
    CANDIDATE_INTERSECTION = "candidate_intersection"
    UI_SELECTION_DIFF = "ui_selection_diff"
    STRUCTURED_COMPARISON = "structured_comparison"


class PatchOp(str, Enum):
    ADJUST_WEIGHT = "adjust_weight"
    ADD_INDICATOR = "add_indicator"
    DEMOTE_INDICATOR = "demote_indicator"
    PROMOTE_INDICATOR = "promote_indicator"
    ADD_STEP = "add_step"
    TOGGLE_OPTIONAL = "toggle_optional"
    CREATE_DRAFT = "create_draft"


# ============================================================
# 基础数据类
# ============================================================


@dataclass(frozen=True)
class Candidate:
    """检索候选项 —— intent_parser 返回的 top-N 候选"""
    id: str
    score: float
    rank: int


@dataclass(frozen=True)
class ObservationContext:
    """observation 的上下文字段"""
    time_period: TimePeriod
    query_raw: str
    trigger_source: TriggerSource
    query_intent_hint: str | None = None


@dataclass(frozen=True)
class Observation:
    """单轮 observation 记录 (v2)

    在 session 结束时由 analyze-observe hook 生成。
    """
    turn: int
    query: str
    industry: str
    indicators_retrieved: list[str]
    scenarios_retrieved: list[str]
    context: ObservationContext
    source: Literal["l1_exact", "l2_match", "l3_fallback"] = "l2_match"
    indicators_candidates: list[Candidate] = field(default_factory=list)
    models_retrieved: list[str] = field(default_factory=list)
    analysis_type: str = ""
    skill_chain_planned: list[str] = field(default_factory=list)
    skill_chain_actual: list[str] = field(default_factory=list)
    template_matched: str | None = None
    user_anon_id: str = ""
    error: str | None = None


@dataclass(frozen=True)
class DetectedSignal:
    """检测到的信号

    由 signal_detector / reinforcement_detector / counterfactual_check /
    preference_detector 产出，写入 JSONL。
    """
    type: SignalType
    session_id: str
    turn_pair: tuple[int, int]
    industry: str
    scenario: str
    ts: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    indicators_before: list[str] = field(default_factory=list)
    indicators_after: list[str] = field(default_factory=list)
    template_before: str | None = None
    template_after: str | None = None
    query_before: str = ""
    query_after: str = ""
    detection_method: DetectionMethod = DetectionMethod.STRUCTURED_COMPARISON
    replacement_ratio: float = 0.0
    replaced_indicators: list[str] = field(default_factory=list)
    added_indicators: list[str] = field(default_factory=list)
    kept_indicators: list[str] = field(default_factory=list)
    candidate_hit: bool = False
    hit_ranks: list[int] = field(default_factory=list)
    user_anon_id: str = ""


@dataclass(frozen=True)
class CounterfactualResult:
    """反事实检测结果"""
    candidate_hit: bool
    hit_indicators: list[str]
    hit_ranks: list[int]
    user_selected: list[str]
    indicators_retrieved: list[str]


@dataclass(frozen=True)
class CounterRecord:
    """Session 级健康计数器"""
    session: str
    date: str
    total_queries: int = 0
    l1_hits: int = 0
    l2_hits: int = 0
    l3_fallbacks: int = 0
    plan_validation_failures: int = 0
    corrections: int = 0
    supplements: int = 0
    refinements: int = 0
    errors: int = 0
    by_scenario: dict[str, dict[str, int]] = field(default_factory=dict)


# ============================================================
# 聚类与假设
# ============================================================


@dataclass(frozen=True)
class SignalCluster:
    """聚类结果 —— 一组相关信号的聚合"""
    signal_type: SignalType
    industry: str
    scenario: str
    signal_ids: list[str]
    frequency: int
    unique_sessions: int
    direction_count: int
    user_anon_ids: list[str]
    details: dict = field(default_factory=dict)


@dataclass(frozen=True)
class ConfidenceBreakdown:
    """置信度四维分解"""
    frequency_score: float
    consistency_score: float
    diversity_score: float
    proximity_bonus: float
    raw_confidence: float
    frequency_sat: int
    diversity_sat: int


@dataclass(frozen=True)
class Evidence:
    """假设的证据链"""
    signal_type: SignalType
    signal_ids: list[str]
    frequency: int
    period_days: int
    unique_sessions: int
    user_diversity_ratio: float = 1.0


@dataclass(frozen=True)
class HypothesisTarget:
    """假设的修改目标"""
    layer: Literal["canonical", "template", "routing", "industry"]
    file: str
    path: str
    field: str | None = None


@dataclass(frozen=True)
class Hypothesis:
    """进化假设"""
    id: str
    type: HypothesisType
    industry: str
    evidence: Evidence
    target: HypothesisTarget
    confidence: float
    validated_confidence: float | None = None
    pass_rate: float | None = None
    status: HypothesisStatus = HypothesisStatus.PENDING_VALIDATION
    current: dict | None = None
    suggested: dict | None = None
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    dimension: str = ""


# ============================================================
# 补丁与权重爬坡
# ============================================================


@dataclass(frozen=True)
class PatchOperation:
    """单个补丁操作"""
    op: PatchOp
    target: str
    delta: float = 0.0
    current_weight: float = 0.0
    max_weight: float | None = None
    reason: str = ""


@dataclass(frozen=True)
class PropagationEntry:
    """语义传播条目"""
    indicator: str
    delta: float
    reason: str  # "direct_correction" | "semantic_propagation" | "cross_industry_transfer"
    mapping_confidence: float = 1.0


@dataclass(frozen=True)
class Patch:
    """进化补丁文件内容"""
    id: str
    status: HypothesisStatus
    type: HypothesisType
    created: str
    last_updated: str
    target: HypothesisTarget
    operations: list[PatchOperation]
    propagation: list[PropagationEntry] = field(default_factory=list)
    evidence: Evidence | None = None
    validated_confidence: float = 0.0
    schema_version: int = 2


@dataclass(frozen=True)
class ClimbResult:
    """权重爬坡评估结果"""
    hypothesis_id: str
    current_weight: float
    new_weight: float
    weeks_active: int
    weeks_frozen: int
    action: Literal["climb", "freeze", "decay", "defunct", "mature", "hold"]
    reason: str


# ============================================================
# 验证
# ============================================================


@dataclass(frozen=True)
class ValidationResult:
    """单条假设的验证结果"""
    hypothesis_id: str
    passed: bool
    pass_rate: float
    validated_confidence: float
    holdout_count: int
    passed_count: int
    degradation_found: bool
    degraded_queries: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class BatchValidationResult:
    """批量验证结果"""
    all_passed: bool
    hypothesis_results: list[ValidationResult]
    combo_passed: bool
    combo_degradation: bool
    conflicting_pairs: list[tuple[str, str]] = field(default_factory=list)


# ============================================================
# 模板
# ============================================================


@dataclass(frozen=True)
class DeviationReport:
    """模板偏离度报告"""
    template_id: str
    weeks: int
    usage_count: int
    indicator_stats: dict[str, dict[str, int]]  # indicator_id -> {accepted, replaced, skipped, supplemented}
    step_stats: dict[str, dict[str, int]]       # step_skill -> {executed, skipped, supplemented}
    triggers: list[str]  # 触发的调整类型列表


@dataclass(frozen=True)
class TemplateAdjustment:
    """模板原子调整"""
    template_id: str
    adjustment_type: str  # add_indicator | demote_indicator | promote_indicator | toggle_optional | add_optional_step
    target: str           # indicator_id or step_skill
    action: dict
    priority: int
    reason: str


@dataclass(frozen=True)
class DraftTemplate:
    """草稿模板"""
    id: str
    name: str
    status: Literal["draft", "active", "defunct"]
    version: int
    routing_weight: float
    indicators: dict[str, list[dict]]
    steps: list[dict]
    applicability: dict
    evidence_signals: list[str]
    weeks_active: int = 0
    acceptance_count: int = 0
    rejection_count: int = 0


# ============================================================
# 主动学习
# ============================================================


@dataclass(frozen=True)
class ClarificationRequest:
    """主动学习反问"""
    options: list[dict]
    question: str
    gap: float
    session_clarifications: int


# ============================================================
# 健康监控
# ============================================================


@dataclass(frozen=True)
class WindowMetrics:
    """48h 监控窗口指标"""
    scenario: str
    query_count: int
    l3_rate: float
    l1_rate: float
    correction_rate: float
    baseline_l3_rate: float
    baseline_correction_rate: float
    l3_degradation: bool = False
    correction_degradation: bool = False
    sufficient_samples: bool = False


@dataclass(frozen=True)
class DegradationResult:
    """退化判定结果"""
    degraded: bool
    reason: str
    window_metrics: WindowMetrics | None = None
    action: Literal["freeze", "alert", "none"] = "none"


@dataclass(frozen=True)
class WeeklyReport:
    """周级健康报告"""
    week_start: str
    total_queries: int
    signal_efficiency: float        # (correction+supplement) / total
    reinforcement_rate: float       # reinforcements / total
    counterfactual_hit_rate: float  # counterfactuals / corrections
    l3_rate: float
    draft_promotion_rate: float
    weight_freeze_rate: float
    health_status: Literal["healthy", "watch", "degrading"]
