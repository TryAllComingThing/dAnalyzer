"""
行业数据分析器

为不同行业提供特定的数据分析函数，供 ecommerce_pipeline.py 调度。
"""

import csv
import time
from collections import defaultdict
from typing import List, Dict, Callable


def analyze_ecommerce(rows: List[Dict], query: str) -> dict:
    """电商分析: 按品类聚合 GMV 和订单量"""
    category_stats = defaultdict(lambda: {"gmv": 0.0, "order_count": 0})

    for row in rows:
        cat = row.get("category", "未知")
        try:
            amount = float(row.get("actual_amount", 0))
        except (ValueError, TypeError):
            amount = 0.0
        category_stats[cat]["gmv"] += amount
        category_stats[cat]["order_count"] += 1

    sorted_cats = sorted(
        category_stats.items(), key=lambda x: x[1]["gmv"], reverse=True
    )

    breakdown = []
    for cat, stats in sorted_cats:
        breakdown.append({
            "category": cat,
            "gmv": round(stats["gmv"], 2),
            "order_count": stats["order_count"],
            "gmv_share_pct": 0.0,
        })

    total_gmv = sum(b["gmv"] for b in breakdown)
    for b in breakdown:
        if total_gmv > 0:
            b["gmv_share_pct"] = round(b["gmv"] / total_gmv * 100, 1)

    return {
        "total_gmv": round(total_gmv, 2),
        "total_orders": sum(b["order_count"] for b in breakdown),
        "category_breakdown": breakdown,
    }


def analyze_logistics(rows: List[Dict], query: str) -> dict:
    """物流分析: 配送效率统计"""
    total = len(rows)
    delivered = sum(1 for r in rows if r.get("status") == "已签收")
    total_weight = 0.0
    delivery_hours = []

    for r in rows:
        try:
            total_weight += float(r.get("weight", 0))
        except (ValueError, TypeError):
            pass
        pickup = r.get("pickup_time", "")
        sign = r.get("sign_time", "")
        if pickup and sign and r.get("status") == "已签收":
            try:
                from datetime import datetime
                p = datetime.strptime(pickup, "%Y-%m-%d %H:%M")
                s = datetime.strptime(sign, "%Y-%m-%d %H:%M")
                delivery_hours.append((s - p).total_seconds() / 3600)
            except (ValueError, TypeError):
                pass

    avg_delivery_hours = round(
        sum(delivery_hours) / len(delivery_hours), 2
    ) if delivery_hours else 0

    return {
        "total_waybills": total,
        "delivered": delivered,
        "delivery_rate": round(delivered / total * 100, 1) if total else 0,
        "total_weight_kg": round(total_weight, 1),
        "avg_delivery_hours": avg_delivery_hours,
        "in_transit": sum(1 for r in rows if r.get("status") == "运输中"),
    }


def analyze_finance(rows: List[Dict], query: str) -> dict:
    """金融分析: 贷款风险统计"""
    total_loans = len(rows)
    total_balance = 0.0
    total_loan_amount = 0.0
    npl_balance = 0.0
    classification_dist = defaultdict(int)
    status_dist = defaultdict(int)

    for r in rows:
        try:
            balance = float(r.get("balance", 0))
            loan_amount = float(r.get("loan_amount", 0))
        except (ValueError, TypeError):
            balance = 0.0
            loan_amount = 0.0

        total_balance += balance
        total_loan_amount += loan_amount

        classification = r.get("classification", "未知")
        classification_dist[classification] += 1

        status = r.get("status", "未知")
        status_dist[status] += 1

        if classification in ("次级", "可疑", "损失"):
            npl_balance += balance

    npl_ratio = round(npl_balance / total_balance * 100, 2) if total_balance else 0

    return {
        "total_loans": total_loans,
        "total_loan_amount": round(total_loan_amount, 2),
        "total_balance": round(total_balance, 2),
        "npl_balance": round(npl_balance, 2),
        "npl_ratio": npl_ratio,
        "classification_distribution": dict(classification_dist),
        "status_distribution": dict(status_dist),
    }


def analyze_manufacturing(rows: List[Dict], query: str) -> dict:
    """制造分析: 生产质量统计"""
    total_orders = len(rows)
    total_planned = 0
    total_actual = 0
    total_defect = 0
    total_rework = 0

    for r in rows:
        try:
            total_planned += int(r.get("planned_qty", 0))
            total_actual += int(r.get("actual_qty", 0))
            total_defect += int(r.get("defect_qty", 0))
            total_rework += int(r.get("rework_qty", 0))
        except (ValueError, TypeError):
            pass

    capacity_rate = round(total_actual / total_planned * 100, 1) if total_planned else 0
    defect_rate = round(total_defect / total_actual * 100, 2) if total_actual else 0
    rework_rate = round(total_rework / total_actual * 100, 2) if total_actual else 0

    yield_rate = round(
        (total_actual - total_defect) / total_actual * 100, 1
    ) if total_actual else 0

    return {
        "total_orders": total_orders,
        "total_planned": total_planned,
        "total_actual": total_actual,
        "total_defect": total_defect,
        "capacity_utilization_pct": capacity_rate,
        "defect_rate_pct": defect_rate,
        "rework_rate_pct": rework_rate,
        "yield_rate_pct": yield_rate,
    }


# 行业代码 → 分析函数映射
ANALYZER_MAP: Dict[str, Callable] = {
    "fmcg": analyze_ecommerce,
}


def analyze_for_industry(rows: List[Dict], query: str, industry: str = "fmcg") -> dict:
    """
    根据行业调度对应的分析函数

    Args:
        rows: CSV 数据行列表
        query: 查询语句
        industry: 行业代码

    Returns:
        分析结果字典
    """
    analyzer = ANALYZER_MAP.get(industry, analyze_ecommerce)
    return analyzer(rows, query)
