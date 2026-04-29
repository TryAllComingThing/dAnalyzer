"""
dAnalyzer 上下文检索脚本

用法:
    python scripts/retrieve_context.py --query "配送时效" --industry logistics
    python scripts/retrieve_context.py --query "上月GMV" --industry ecommerce --output results.json

被 context-retriever SKILL.md 调用，在生成 SQL 前注入行业上下文。
"""

import argparse
import json
import sys
from pathlib import Path

# 确保项目根目录在 sys.path 中
_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from scripts.industry.store import IndustryStore
from scripts.industry.retriever import IndustryRetriever


def retrieve_context(query: str, industry: str = "ecommerce",
                     data_root: str = "data/industry",
                     top_k: int = 5, include_score: bool = False) -> dict:
    """
    检索行业上下文：匹配的指标定义、场景模板、表映射。

    Args:
        query: 用户自然语言查询
        industry: 行业代码 (ecommerce/logistics/manufacturing/finance)
        data_root: 行业数据根目录
        top_k: 每个类别最大返回数
        include_score: 是否包含相关性评分

    Returns:
        {
            "indicators": [{"code": "...", "name": "...", "formula": "...", ...}],
            "scenarios": [{"code": "...", "name": "...", ...}],
            "query": "...",
            "industry": "...",
            "method": "fts+vector+rrf"
        }
    """
    store = IndustryStore(industry, data_root)
    retriever = IndustryRetriever(store)
    results = retriever.search(query, top_k=top_k,
                               use_fts=True, use_vector=True, use_rrf=True)

    output = {
        "indicators": results["indicators"],
        "scenarios": results["scenarios"],
        "query": results["query"],
        "industry": industry,
        "method": results["method"],
    }

    if include_score:
        output["scores"] = results["scores"]

    return output


def main():
    parser = argparse.ArgumentParser(
        description="dAnalyzer 行业上下文检索",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--query", "-q", required=True,
                        help="用户输入的自然语言查询")
    parser.add_argument("--industry", "-i", default="ecommerce",
                        help="行业代码 (ecommerce/logistics/manufacturing/finance)")
    parser.add_argument("--data_root", default="data/industry",
                        help="行业数据根目录")
    parser.add_argument("--top_k", type=int, default=5,
                        help="每类返回最大数量")
    parser.add_argument("--output", "-o",
                        help="输出到文件 (默认输出到 stdout)")
    parser.add_argument("--include_score", action="store_true",
                        help="包含相关性评分")

    args = parser.parse_args()
    result = retrieve_context(
        query=args.query,
        industry=args.industry,
        data_root=args.data_root,
        top_k=args.top_k,
        include_score=args.include_score,
    )

    output = json.dumps(result, ensure_ascii=False, indent=2)

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(output, encoding="utf-8")
        print(f"[ContextRetriever] Results written to {args.output}")
    else:
        print(output)


if __name__ == "__main__":
    main()
