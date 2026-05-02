"""多模态偏好信号检测器

检测用户对图表类型和报告格式的偏好。
当系统推荐的类型与用户实际选择不同时，产生 preference 信号。
"""

from __future__ import annotations

from learn.ingest.models import DetectedSignal, DetectionMethod, Observation, SignalType


def detect_preference(
    observation: Observation,
    user_chart_choice: str | None = None,
    recommended_chart: str | None = None,
    user_report_choice: str | None = None,
    recommended_report: str | None = None,
) -> list[DetectedSignal]:
    """检测多模态偏好信号。

    Args:
        observation: 当前 observation
        user_chart_choice: 用户实际选择的图表类型（如 "line_chart"）
        recommended_chart: 系统推荐的图表类型（如 "heatmap"）
        user_report_choice: 用户实际选择的报告格式（如 "excel"）
        recommended_report: 系统推荐的报告格式（如 "pdf"）

    Returns:
        0-2 个 preference 信号
    """
    signals: list[DetectedSignal] = []

    if user_chart_choice and recommended_chart and user_chart_choice != recommended_chart:
        signals.append(DetectedSignal(
            type=SignalType.PREFERENCE_CHART,
            session_id="",
            turn_pair=(observation.turn, observation.turn),
            industry=observation.industry,
            scenario=observation.scenarios_retrieved[0] if observation.scenarios_retrieved else "",
            indicators_before=[recommended_chart],
            indicators_after=[user_chart_choice],
            template_before=observation.template_matched,
            query_before=f"recommended:{recommended_chart}",
            query_after=f"selected:{user_chart_choice}",
            detection_method=DetectionMethod.UI_SELECTION_DIFF,
            user_anon_id=observation.user_anon_id,
        ))

    if user_report_choice and recommended_report and user_report_choice != recommended_report:
        signals.append(DetectedSignal(
            type=SignalType.PREFERENCE_REPORT,
            session_id="",
            turn_pair=(observation.turn, observation.turn),
            industry=observation.industry,
            scenario=observation.scenarios_retrieved[0] if observation.scenarios_retrieved else "",
            indicators_before=[recommended_report],
            indicators_after=[user_report_choice],
            template_before=observation.template_matched,
            query_before=f"recommended:{recommended_report}",
            query_after=f"selected:{user_report_choice}",
            detection_method=DetectionMethod.UI_SELECTION_DIFF,
            user_anon_id=observation.user_anon_id,
        ))

    return signals
