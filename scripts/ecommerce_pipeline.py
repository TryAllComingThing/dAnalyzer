"""
dAnalyzer 电商端到端数据管道演示

演示完整链路: 用户输入 → 上下文检索 → 数据查询 → 分析 → 安全扫描

用法:
    # 使用默认测试数据
    python scripts/ecommerce_pipeline.py

    # 指定查询和数据文件
    python scripts/ecommerce_pipeline.py --query "各品类GMV和订单量" --data tests/data/sample/test_orders.csv

    # 输出到文件
    python scripts/ecommerce_pipeline.py --output output/pipeline_result.json
"""

import argparse
import csv
import json
import sys
import time
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional

_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from scripts.industry.store import IndustryStore
from scripts.industry.retriever import IndustryRetriever
from scripts.industry_analyzers import analyze_for_industry
from scripts.security_scan import security_scan


def step1_retrieve_context(query: str, industry: str = "ecommerce") -> dict:
    """
    步骤 1: 上下文检索

    调用 IndustryRetriever 获取匹配的指标定义、公式、表映射。
    """
    store = IndustryStore(industry)
    retriever = IndustryRetriever(store)
    return retriever.search(query, top_k=5,
                            use_fts=True, use_vector=True, use_rrf=True)


def step2_load_data(csv_path: str, required_fields: List[str] = None) -> List[Dict]:
    """
    步骤 2: 数据加载

    使用 dAnalyzer 的 CSV 数据读取方式加载数据。
    """
    rows = []
    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)

    if required_fields:
        for f in required_fields:
            if f not in rows[0]:
                print(f"  [Pipeline] Warning: field '{f}' not found in CSV", file=sys.stderr)

    return rows


def step3_analyze(rows: List[Dict], query: str, industry: str = "ecommerce") -> dict:
    """
    步骤 3: 数据分析

    根据行业调用对应的分析函数。
    """
    start = time.time()
    result = analyze_for_industry(rows, query, industry)
    elapsed_ms = round((time.time() - start) * 1000, 2)
    result["analysis_time_ms"] = elapsed_ms
    return result


def step4_security_scan(data: List[Dict]) -> dict:
    """
    步骤 4: 安全扫描

    强制安全关卡，检测 P0 敏感数据并脱敏 P1/P2 字段。
    """
    return security_scan(data)


def run_pipeline(query: str, csv_path: str,
                 industry: str = "ecommerce") -> dict:
    """
    运行全链路数据分析管道。

    Args:
        query: 用户输入 (如 "各品类 GMV 和订单量")
        csv_path: 数据文件路径
        industry: 行业代码

    Returns:
        {
            "pipeline": "ecommerce",
            "query": "...",
            "steps": {
                "context_retrieval": {...},
                "data_loading": {...},
                "analysis": {...},
                "security": {...}
            },
            "summary": {...}
        }
    """
    pipeline_start = time.time()
    steps = {}

    # === Step 1: 上下文检索 ===
    print("\n[Pipeline] Step 1/4: 上下文检索...", file=sys.stderr)
    s1_start = time.time()
    context = step1_retrieve_context(query, industry)
    s1_time = round((time.time() - s1_start) * 1000, 2)
    steps["context_retrieval"] = {
        "indicators": [
            {"code": i.get("code"), "name": i.get("name"),
             "formula": i.get("formula"), "table": i.get("table_name")}
            for i in context["indicators"]
        ],
        "scenarios": [s.get("name") for s in context["scenarios"]],
        "method": context["method"],
        "time_ms": s1_time,
    }
    print(f"  → {len(context['indicators'])} indicators, "
          f"{len(context['scenarios'])} scenarios ({s1_time}ms)", file=sys.stderr)

    # === Step 2: 数据加载 ===
    print("\n[Pipeline] Step 2/4: 数据加载...", file=sys.stderr)
    s2_start = time.time()
    required_fields = {
        "ecommerce": ["category", "actual_amount", "order_id"],
        "finance": ["loan_id", "balance", "classification"],
        "logistics": ["waybill_id", "status", "weight"],
        "manufacturing": ["order_id", "planned_qty", "actual_qty"],
    }.get(industry, [])
    rows = step2_load_data(csv_path, required_fields)
    s2_time = round((time.time() - s2_start) * 1000, 2)
    steps["data_loading"] = {
        "source": csv_path,
        "total_rows": len(rows),
        "time_ms": s2_time,
    }
    print(f"  → {len(rows)} rows loaded ({s2_time}ms)", file=sys.stderr)

    # === Step 3: 分析 ===
    print("\n[Pipeline] Step 3/4: 数据分析...", file=sys.stderr)
    s3_start = time.time()
    analysis_result = step3_analyze(rows, query, industry)
    s3_time = round((time.time() - s3_start) * 1000, 2)
    steps["analysis"] = {
        "query": query,
        "industry": industry,
        **analysis_result,
        "time_ms": s3_time,
    }
    print(f"  → analysis complete ({s3_time}ms)", file=sys.stderr)

    # === Step 4: 安全扫描 ===
    print("\n[Pipeline] Step 4/4: 安全扫描...", file=sys.stderr)
    s4_start = time.time()

    # 根据行业提取安全扫描输入
    scan_input = []
    if "category_breakdown" in analysis_result:
        scan_input = [{
            "category": b["category"],
            "gmv": b["gmv"],
            "order_count": b["order_count"],
            "gmv_share_pct": b["gmv_share_pct"],
        } for b in analysis_result["category_breakdown"]]
    elif "classification_distribution" in analysis_result:
        scan_input = [{"classification": k, "count": v}
                      for k, v in analysis_result["classification_distribution"].items()]
    elif "delivery_rate" in analysis_result:
        scan_input = [{"metric": k, "value": v}
                      for k, v in analysis_result.items()
                      if isinstance(v, (int, float))]
    else:
        scan_input = [{"metric": k, "value": v}
                      for k, v in analysis_result.items()
                      if isinstance(v, (int, float, str)) and k != "analysis_time_ms"]

    security_result = step4_security_scan(scan_input)
    s4_time = round((time.time() - s4_start) * 1000, 2)
    steps["security"] = {
        "pass": security_result["pass"],
        "level": security_result["level"],
        "blocked": security_result["blocked"],
        "masked": security_result["masked"],
        "time_ms": s4_time,
    }
    print(f"  → {security_result['level']} ({s4_time}ms)", file=sys.stderr)

    if not security_result["pass"]:
        print(f"  ⛔ BLOCKED: {security_result['blocked']}", file=sys.stderr)

    total_time = round((time.time() - pipeline_start) * 1000, 2)

    summary = {
        "total_indicators": len(steps["context_retrieval"]["indicators"]),
        "total_scenarios": len(steps["context_retrieval"]["scenarios"]),
        "total_rows_loaded": steps["data_loading"]["total_rows"],
        "security_pass": security_result["pass"],
        "security_level": security_result["level"],
    }
    # 保留行业特定汇总字段（向后兼容）
    if "total_gmv" in analysis_result:
        summary["total_gmv"] = analysis_result["total_gmv"]
    if "total_orders" in analysis_result:
        summary["total_orders"] = analysis_result["total_orders"]
    if "category_breakdown" in analysis_result:
        summary["categories"] = len(analysis_result["category_breakdown"])

    result = {
        "pipeline": industry,
        "query": query,
        "steps": steps,
        "output": security_result.get("clean_data", []),
        "timing": {
            "total_ms": total_time,
            "breakdown": {k: v.get("time_ms", 0) for k, v in steps.items()},
        },
        "summary": summary,
    }

    # 可选: 记录度量
    try:
        from metrics.collector import MetricsCollector
        collector = MetricsCollector()
        collector.record_run(result)
    except Exception as e:
        print(f"  [Metrics] Warning: {e}", file=sys.stderr)

    return result


def main():
    parser = argparse.ArgumentParser(
        description="dAnalyzer 电商数据分析端到端管道",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--query", "-q",
                        default="各品类 GMV 和订单量",
                        help="分析查询语句")
    parser.add_argument("--data", "-d",
                        default="tests/data/sample/test_orders.csv",
                        help="数据文件路径 (CSV)")
    parser.add_argument("--industry", "-i", default="ecommerce",
                        help="行业代码")
    parser.add_argument("--output", "-o",
                        help="输出到文件")

    args = parser.parse_args()

    result = run_pipeline(
        query=args.query,
        csv_path=args.data,
        industry=args.industry,
    )

    output = json.dumps(result, ensure_ascii=False, indent=2)

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(output, encoding="utf-8")
        print(f"\n[Pipeline] Results written to {args.output}", file=sys.stderr)
    else:
        print(output)


if __name__ == "__main__":
    main()
