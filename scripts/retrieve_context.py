"""
dAnalyzer 上下文检索脚本 — Phase 1

集成意图解析器（L1→L2→L3 兜底），自动检测行业，支持 LLM 结构化转写。

用法:
    # 自动检测行业 + L2 模糊搜索
    python scripts/retrieve_context.py --query "品类分析"

    # 指定行业
    python scripts/retrieve_context.py --query "GMV趋势" --industry fmcg

    # 带 LLM 结构化转写（L1 精确路径）
    python scripts/retrieve_context.py --query "哪些品类表现不好" \
        --plan '{"industry":"fmcg","analysis_type":"diagnostic","indicators":["sales_amount","order_count"],"scenarios":["sales_trend"],"models":["attribution-model"]}'

    # 输出到文件
    python scripts/retrieve_context.py --query "上月GMV" --industry fmcg --output results.json

被 context-retriever SKILL.md 和 danalyzer-core 调用。
"""

import argparse
import json
import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from scripts.intent_parser import parse_intent


def retrieve_context(
    query: str,
    industry: str = None,
    plan_json: str = None,
    data_root: str = "knowledge/industry",
    top_k: int = 5,
    include_score: bool = False,
) -> dict:
    """
    检索行业上下文：指标定义、场景模板、模型引用、技能链建议。

    内部走 L1 → L2 → L3 三级兜底，保证任何情况下都有可用结果。
    """
    result = parse_intent(
        query=query,
        industry=industry,
        plan_json=plan_json,
        data_root=data_root,
    )

    # 限制返回数量
    indicators = result.get("indicators", [])[:top_k]
    scenarios = result.get("scenarios", [])[:3]

    output = {
        "indicators": indicators,
        "scenarios": scenarios,
        "models": result.get("models", []),
        "analysis_type": result.get("analysis_type", "descriptive"),
        "skill_chain": result.get("skill_chain", []),
        "query": query,
        "industry": result.get("industry"),
        "source": result.get("source", "unknown"),
        "keywords": result.get("keywords", []),
    }

    if include_score and "diagnostics" in result:
        output["diagnostics"] = result["diagnostics"]

    # L3 兜底时注入 routing_context 供 Agent 推理使用
    if result.get("source") == "l3_llm_fallback":
        output["routing_context"] = result.get("routing_context", {})
        output["message"] = result.get("message", "")

    return output


def main():
    parser = argparse.ArgumentParser(
        description="dAnalyzer 上下文检索 — 三级兜底",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--query", "-q", required=True,
                        help="用户自然语言查询")
    parser.add_argument("--industry", "-i", default=None,
                        help="行业代码（可选，不传则自动检测）")
    parser.add_argument("--plan", "-p", default=None,
                        help="LLM 结构化转写 JSON（L1 精确路径）")
    parser.add_argument("--data_root", default="knowledge/industry",
                        help="行业数据根目录")
    parser.add_argument("--top_k", type=int, default=5,
                        help="每类返回最大数量")
    parser.add_argument("--output", "-o",
                        help="输出到文件")
    parser.add_argument("--include_score", action="store_true",
                        help="包含诊断信息")

    args = parser.parse_args()

    result = retrieve_context(
        query=args.query,
        industry=args.industry,
        plan_json=args.plan,
        data_root=args.data_root,
        top_k=args.top_k,
        include_score=args.include_score,
    )

    output = json.dumps(result, ensure_ascii=False, indent=2, default=str)

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(output, encoding="utf-8")
        print(f"[ContextRetriever] Results → {args.output}", file=sys.stderr)
    else:
        print(output)

    # 诊断信息到 stderr
    print(f"[ContextRetriever] source={result['source']} "
          f"industry={result.get('industry')} "
          f"indicators={len(result.get('indicators',[]))} "
          f"scenarios={len(result.get('scenarios',[]))} "
          f"models={result.get('models',[])}",
          file=sys.stderr)


if __name__ == "__main__":
    main()
