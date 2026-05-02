"""RFM 用户分群

提供 RFM 计算和用户分群功能，供 model 技能调用。

用法:
    from scripts.rfm_segmentation import calculate_rfm, segment_users

    rfm = calculate_rfm(orders, reference_date)
    segments = segment_users(rfm)
"""

from __future__ import annotations

from datetime import datetime


def calculate_rfm(orders: list[dict], reference_date: datetime) -> dict[str, dict]:
    """从订单数据计算 RFM 值。

    Args:
        orders: 订单列表，每条包含 user_id, order_date (str "%Y-%m-%d"), amount
        reference_date: 参考日期，用于计算 recency

    Returns:
        dict: user_id -> {"recency": int, "frequency": int, "monetary": float}
    """
    rfm: dict[str, dict] = {}

    for row in orders:
        user_id = row["user_id"]
        try:
            order_date = datetime.strptime(row["order_date"], "%Y-%m-%d")
        except (ValueError, KeyError):
            continue
        try:
            amount = float(row.get("amount", 0))
        except (ValueError, TypeError):
            amount = 0.0

        if user_id not in rfm:
            rfm[user_id] = {
                "recency": (reference_date - order_date).days,
                "frequency": 0,
                "monetary": 0.0,
            }

        rfm[user_id]["frequency"] += 1
        rfm[user_id]["monetary"] += amount
        # recency 取最小值（最近一次）
        days = (reference_date - order_date).days
        if days < rfm[user_id]["recency"]:
            rfm[user_id]["recency"] = days

    return rfm


def segment_users(rfm: dict[str, dict]) -> dict[str, str]:
    """基于 RFM 值将用户分为 5 个群组。

    分群规则:
        高价值客户:   R <= 7,  F >= 3, M >= 1000
        潜力客户:     R <= 7,  F < 3
        流失风险客户: R > 30,  F >= 5
        流失客户:     R > 30,  F < 5
        普通客户:     其他

    Args:
        rfm: user_id -> {"recency", "frequency", "monetary"}

    Returns:
        dict: user_id -> segment_name
    """
    segments: dict[str, str] = {}

    for user_id, v in rfm.items():
        r = v["recency"]
        f = v["frequency"]
        m = v["monetary"]

        if r <= 7 and f >= 3 and m >= 1000:
            segment = "高价值客户"
        elif r <= 7 and f < 3:
            segment = "潜力客户"
        elif r > 30 and f >= 5:
            segment = "流失风险客户"
        elif r > 30:
            segment = "流失客户"
        else:
            segment = "普通客户"

        segments[user_id] = segment

    return segments
