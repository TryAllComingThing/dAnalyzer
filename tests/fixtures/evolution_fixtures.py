"""V4 自进化系统测试夹具

提供预定义的 observation pairs、session 序列、信号数据，
覆盖 correction / supplement / refinement / reinforcement / counterfactual / preference 场景。
"""

from __future__ import annotations

from datetime import datetime

from learn.ingest.models import (
    Candidate,
    DetectionMethod,
    DetectedSignal,
    Observation,
    ObservationContext,
    SignalType,
    TimePeriod,
    TriggerSource,
)


def _ctx(query_raw: str, trigger: TriggerSource = TriggerSource.NEW_QUERY,
         period: TimePeriod = TimePeriod.NORMAL) -> ObservationContext:
    return ObservationContext(
        time_period=period,
        query_raw=query_raw,
        trigger_source=trigger,
    )


# ============================================================
# Observation Pairs
# ============================================================

def make_correction_pair() -> tuple[Observation, Observation]:
    """纠正信号: 完全不相交的 indicators"""
    prev = Observation(
        turn=1, query="品类表现", industry="fmcg",
        indicators_retrieved=["sales_amount", "order_count"],
        scenarios_retrieved=["category_analysis"],
        context=_ctx("品类表现"),
        source="l1_exact", template_matched="category_overview",
        user_anon_id="u_001",
    )
    curr = Observation(
        turn=2, query="我要的是毛利率和动销情况", industry="fmcg",
        indicators_retrieved=["gross_margin_rate", "sell_through_rate"],
        scenarios_retrieved=["category_analysis"],
        context=_ctx("我要的是毛利率和动销情况", TriggerSource.CORRECTION),
        source="l1_exact", template_matched="category_health_diagnostic",
        user_anon_id="u_001",
    )
    return prev, curr


def make_partial_correction_pair() -> tuple[Observation, Observation]:
    """部分重叠纠正: 替换比例 >= 50% + 否定词"""
    prev = Observation(
        turn=1, query="看品类表现", industry="fmcg",
        indicators_retrieved=["sales_amount", "order_count", "sku_count"],
        scenarios_retrieved=["category_analysis"],
        context=_ctx("看品类表现"),
        source="l1_exact", template_matched="category_overview",
        user_anon_id="u_001",
    )
    curr = Observation(
        turn=2, query="不对，我要的是毛利率和动销", industry="fmcg",
        indicators_retrieved=["gross_margin_rate", "sell_through_rate", "order_count"],
        scenarios_retrieved=["category_analysis"],
        context=_ctx("不对，我要的是毛利率和动销", TriggerSource.CORRECTION),
        source="l2_match", template_matched="category_health_diagnostic",
        user_anon_id="u_001",
    )
    return prev, curr


def make_supplement_pair() -> tuple[Observation, Observation]:
    """补充信号: 纯扩充"""
    prev = Observation(
        turn=1, query="毛利率和动销率", industry="fmcg",
        indicators_retrieved=["gross_margin_rate", "sell_through_rate"],
        scenarios_retrieved=["category_analysis"],
        context=_ctx("毛利率和动销率"),
        source="l1_exact", template_matched="category_health_diagnostic",
        user_anon_id="u_002",
    )
    curr = Observation(
        turn=2, query="再加上库存周转", industry="fmcg",
        indicators_retrieved=["gross_margin_rate", "sell_through_rate", "inventory_turnover"],
        scenarios_retrieved=["category_analysis"],
        context=_ctx("再加上库存周转", TriggerSource.FOLLOW_UP),
        source="l1_exact", template_matched="category_health_diagnostic",
        user_anon_id="u_002",
    )
    return prev, curr


def make_refinement_pair() -> tuple[Observation, Observation]:
    """调整信号: 部分重叠，无否定词"""
    prev = Observation(
        turn=1, query="品类销售趋势", industry="fmcg",
        indicators_retrieved=["sales_amount", "order_count", "conversion_rate"],
        scenarios_retrieved=["category_analysis"],
        context=_ctx("品类销售趋势"),
        source="l1_exact",
        user_anon_id="u_003",
    )
    curr = Observation(
        turn=2, query="只看销售额和转化率，按周看", industry="fmcg",
        indicators_retrieved=["sales_amount", "conversion_rate"],
        scenarios_retrieved=["category_analysis"],
        context=_ctx("只看销售额和转化率，按周看", TriggerSource.FOLLOW_UP),
        source="l1_exact",
        user_anon_id="u_003",
    )
    return prev, curr


def make_unrelated_pair() -> tuple[Observation, Observation]:
    """不相关: scenario 变化"""
    prev = Observation(
        turn=1, query="品类表现", industry="fmcg",
        indicators_retrieved=["sales_amount"],
        scenarios_retrieved=["category_analysis"],
        context=_ctx("品类表现"),
        source="l1_exact",
        user_anon_id="u_004",
    )
    curr = Observation(
        turn=2, query="渠道效率如何", industry="fmcg",
        indicators_retrieved=["channel_revenue_share"],
        scenarios_retrieved=["channel_analysis"],
        context=_ctx("渠道效率如何"),
        source="l1_exact",
        user_anon_id="u_004",
    )
    return prev, curr


def make_narrowing_pair() -> tuple[Observation, Observation]:
    """纯缩减: 用户自己缩小范围（不产生信号）"""
    prev = Observation(
        turn=1, query="品类全貌", industry="fmcg",
        indicators_retrieved=["sales_amount", "order_count", "sku_count"],
        scenarios_retrieved=["category_analysis"],
        context=_ctx("品类全貌"),
        source="l1_exact",
        user_anon_id="u_001",
    )
    curr = Observation(
        turn=2, query="只看销售额就行", industry="fmcg",
        indicators_retrieved=["sales_amount"],
        scenarios_retrieved=["category_analysis"],
        context=_ctx("只看销售额就行", TriggerSource.FOLLOW_UP),
        source="l1_exact",
        user_anon_id="u_001",
    )
    return prev, curr


# ============================================================
# Session Sequences
# ============================================================

def make_five_turn_session() -> list[Observation]:
    """5-turn session，含纠正 + 补充 + 扩展"""
    return [
        Observation(
            turn=1, query="品类表现", industry="fmcg",
            indicators_retrieved=["sales_amount", "order_count"],
            scenarios_retrieved=["category_analysis"],
            context=_ctx("品类表现"),
            source="l1_exact", template_matched="category_overview",
            user_anon_id="u_001",
        ),
        Observation(
            turn=2, query="我要的是毛利率和动销", industry="fmcg",
            indicators_retrieved=["gross_margin_rate", "sell_through_rate"],
            scenarios_retrieved=["category_analysis"],
            context=_ctx("我要的是毛利率和动销", TriggerSource.CORRECTION),
            source="l1_exact", template_matched="category_health_diagnostic",
            user_anon_id="u_001",
        ),
        Observation(
            turn=3, query="再加上库存周转", industry="fmcg",
            indicators_retrieved=["gross_margin_rate", "sell_through_rate", "inventory_turnover"],
            scenarios_retrieved=["category_analysis"],
            context=_ctx("再加上库存周转", TriggerSource.FOLLOW_UP),
            source="l1_exact", template_matched="category_health_diagnostic",
            user_anon_id="u_001",
        ),
        Observation(
            turn=4, query="按渠道拆解看看", industry="fmcg",
            indicators_retrieved=["gross_margin_rate", "sell_through_rate", "inventory_turnover", "channel_revenue_share"],
            scenarios_retrieved=["category_analysis", "channel_analysis"],
            context=_ctx("按渠道拆解看看", TriggerSource.FOLLOW_UP),
            source="l1_exact", template_matched="category_health_diagnostic",
            user_anon_id="u_001",
        ),
        Observation(
            turn=5, query="导出一份报告", industry="fmcg",
            indicators_retrieved=["gross_margin_rate", "sell_through_rate", "inventory_turnover", "channel_revenue_share"],
            scenarios_retrieved=["category_analysis", "channel_analysis"],
            context=_ctx("导出一份报告", TriggerSource.FOLLOW_UP),
            source="l1_exact", template_matched="category_health_diagnostic",
            skill_chain_actual=["data-query", "data-analysis", "visual", "report"],
            user_anon_id="u_001",
        ),
    ]


# ============================================================
# Counterfactual Scenarios
# ============================================================

def make_counterfactual_observation() -> Observation:
    """用户纠正的指标在 candidates 中（rank 4,5）但不在 retrieved 中"""
    return Observation(
        turn=2, query="不对，我要毛利率和动销", industry="fmcg",
        indicators_retrieved=["sales_amount", "order_count", "sku_count"],
        indicators_candidates=[
            Candidate(id="sales_amount", score=0.95, rank=1),
            Candidate(id="order_count", score=0.88, rank=2),
            Candidate(id="sku_count", score=0.81, rank=3),
            Candidate(id="gross_margin_rate", score=0.62, rank=4),
            Candidate(id="sell_through_rate", score=0.58, rank=5),
        ],
        scenarios_retrieved=["category_analysis"],
        context=_ctx("不对，我要毛利率和动销", TriggerSource.CORRECTION),
        user_anon_id="u_005",
    )


def make_pure_correction_observation() -> Observation:
    """用户纠正的指标完全不在 candidates 中"""
    return Observation(
        turn=2, query="我要利润率指标", industry="fmcg",
        indicators_retrieved=["sales_amount", "order_count"],
        indicators_candidates=[
            Candidate(id="sales_amount", score=0.95, rank=1),
            Candidate(id="order_count", score=0.88, rank=2),
        ],
        scenarios_retrieved=["category_analysis"],
        context=_ctx("我要利润率指标", TriggerSource.CORRECTION),
        user_anon_id="u_006",
    )


# ============================================================
# Preference Scenarios
# ============================================================

def make_preference_observation_chart() -> Observation:
    """用户更换了图表类型"""
    return Observation(
        turn=3, query="用折线图展示", industry="fmcg",
        indicators_retrieved=["gross_margin_rate", "sell_through_rate"],
        scenarios_retrieved=["category_analysis"],
        context=_ctx("用折线图展示", TriggerSource.FOLLOW_UP),
        source="l1_exact", template_matched="category_health_diagnostic",
        skill_chain_actual=["data-query", "data-analysis", "visual"],
        user_anon_id="u_007",
    )


# ============================================================
# Multi-Session Signals (for clustering tests)
# ============================================================

def make_correction_signals_for_clustering() -> list[DetectedSignal]:
    """5 条同方向纠正信号，来自 3 个不同 session（用于聚类测试）"""
    base = {
        "type": SignalType.CORRECTION,
        "industry": "fmcg",
        "scenario": "category_analysis",
        "indicators_before": ["sales_amount"],
        "indicators_after": ["gross_margin_rate"],
        "detection_method": DetectionMethod.DISJOINT,
    }
    return [
        DetectedSignal(
            session_id="s001", turn_pair=(1, 2),
            query_before="品类表现", query_after="我要毛利率",
            user_anon_id="u_001", **base,  # type: ignore[arg-type]
        ),
        DetectedSignal(
            session_id="s001", turn_pair=(3, 4),
            query_before="品类概况", query_after="不是，要毛利",
            user_anon_id="u_001", **base,  # type: ignore[arg-type]
        ),
        DetectedSignal(
            session_id="s002", turn_pair=(1, 2),
            query_before="看下品类", query_after="看毛利率",
            user_anon_id="u_002", **base,  # type: ignore[arg-type]
        ),
        DetectedSignal(
            session_id="s003", turn_pair=(1, 2),
            query_before="品类情况", query_after="那个毛利率",
            user_anon_id="u_003", **base,  # type: ignore[arg-type]
        ),
        DetectedSignal(
            session_id="s004", turn_pair=(2, 3),
            query_before="看看品类", query_after="我要看利润率",
            user_anon_id="u_001", **base,  # type: ignore[arg-type]
        ),
    ]


def make_signals_mixed() -> list[DetectedSignal]:
    """混合信号：3 条 correction + 2 条 supplement（用于属性测试）"""
    corrections = make_correction_signals_for_clustering()[:3]
    supplements = [
        DetectedSignal(
            type=SignalType.SUPPLEMENT,
            session_id="s001", turn_pair=(2, 3),
            industry="fmcg", scenario="category_analysis",
            indicators_before=["gross_margin_rate"],
            indicators_after=["gross_margin_rate", "inventory_turnover"],
            detection_method=DetectionMethod.PURE_ADDITION,
            user_anon_id="u_001",
        ),
        DetectedSignal(
            type=SignalType.SUPPLEMENT,
            session_id="s002", turn_pair=(1, 2),
            industry="fmcg", scenario="category_analysis",
            indicators_before=["gross_margin_rate"],
            indicators_after=["gross_margin_rate", "net_margin_rate"],
            detection_method=DetectionMethod.PURE_ADDITION,
            user_anon_id="u_002",
        ),
    ]
    return corrections + supplements
