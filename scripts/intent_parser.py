"""
意图解析器 — Phase 1 结构化语义解析 + L1→L2→L3 兜底

用法:
    python scripts/intent_parser.py --query "哪些品类表现不好" --industry fmcg
    python scripts/intent_parser.py --plan '<json>' --query "..." --industry fmcg

流程:
    L1: LLM 结构化转写 → 校验层 → SELECT by code（精确命中）
    L2: 降级 → FTS5 + N-gram 向量 + RRF 模糊检索
    L3: 最终兜底 → 返回空 signal，由 Agent LLM 直接推理
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Optional, List, Dict, Union

_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from learn.ingest.models import ClarificationRequest


def load_intent_routing() -> dict:
    """加载意图路由配置"""
    routing_path = _project_root / "knowledge" / "intent-routing.yaml"
    if not routing_path.exists():
        return {}
    import yaml
    with open(routing_path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_live_registry(data_root: str = "knowledge/industry") -> dict:
    """
    实时扫描 knowledge/ 目录构建注册表。
    缓存 60 秒避免重复扫描。
    """
    import time
    now = time.time()
    cache_key = f"_registry_cache_{data_root}"
    if hasattr(load_live_registry, cache_key):
        cached = getattr(load_live_registry, cache_key)
        if now - cached.get("ts", 0) < 60:
            return cached["data"]

    from scripts.registry_scanner import build_registry
    registry = build_registry(data_root)
    setattr(load_live_registry, cache_key, {"ts": now, "data": registry})
    return registry


def merge_routing_with_registry(routing: dict, registry: dict) -> dict:
    """
    合并静态 intent-routing.yaml 与动态注册表。
    动态注册表覆盖 available_industries（从文件系统实时扫描），
    intents 定义仍使用静态配置。
    """
    if not registry:
        return routing

    merged = dict(routing) if routing else {}

    # 从动态注册表构建 available_industries
    live_industries = []
    for code, data in registry.get("industries", {}).items():
        live_industries.append({
            "code": code,
            "name": data.get("name", code),
            "trigger_keywords": data.get("trigger_keywords", []),
            "indicator_count": data.get("indicator_count", 0),
            "scenario_count": data.get("scenario_count", 0),
        })

    merged["available_industries"] = live_industries

    # 动态补充 model_files
    live_models = {}
    for mcode, mdata in registry.get("models", {}).items():
        live_models[mcode] = mdata.get("file", f"knowledge/model/{mcode}.md")
    if live_models:
        merged["model_files"] = {**live_models, **merged.get("model_files", {})}

    return merged


def validate_plan(plan: dict, routing: dict) -> dict:
    """
    校验 LLM 转写结果，返回诊断报告。

    Returns:
        {
            "valid": bool,
            "errors": [str],
            "warnings": [str],
            "industry_ok": bool,
            "indicator_hits": [str],     # 命中的 code
            "indicator_misses": [str],   # 不存在的 code
            "scenario_hits": [str],
            "scenario_misses": [str],
        }
    """
    result = {
        "valid": True, "errors": [], "warnings": [],
        "industry_ok": False,
        "indicator_hits": [], "indicator_misses": [],
        "scenario_hits": [], "scenario_misses": [],
    }

    if not plan:
        result["valid"] = False
        result["errors"].append("plan is empty")
        return result

    # ── 行业校验 ──
    available = [ind["code"] for ind in routing.get("available_industries", [])]
    industry = plan.get("industry", "")
    if industry and industry in available:
        result["industry_ok"] = True
    elif industry:
        result["errors"].append(f"unknown industry '{industry}', available: {available}")
    else:
        result["warnings"].append("industry not specified")

    # ── 分析类型校验 ──
    valid_types = ["descriptive", "diagnostic", "predictive", "prescriptive", "exploratory"]
    if plan.get("analysis_type") and plan["analysis_type"] not in valid_types:
        result["warnings"].append(
            f"unknown analysis_type '{plan['analysis_type']}', valid: {valid_types}"
        )

    # ── 置信度校验 ──
    confidence = plan.get("confidence")
    if confidence is not None and (not isinstance(confidence, (int, float)) or confidence < 0 or confidence > 1):
        result["warnings"].append(f"confidence out of range: {confidence}")

    return result


def validate_codes_against_store(
    plan: dict, store, routing: dict
) -> dict:
    """
    用 IndustryStore 校验 indicator/scenario code 是否存在。
    不存在的 code 尝试从 routing 的 default_indicators 补齐。
    """
    result = {
        "indicator_hits": [],
        "indicator_misses": [],
        "scenario_hits": [],
        "scenario_misses": [],
    }

    for code in plan.get("indicators", []):
        if store.get_indicator(code):
            result["indicator_hits"].append(code)
        else:
            result["indicator_misses"].append(code)

    for code in plan.get("scenarios", []):
        if store.get_scenario(code):
            result["scenario_hits"].append(code)
        else:
            result["scenario_misses"].append(code)

    return result


def repair_from_scenario(valid_codes: set, valid_scenarios: set, store) -> set:
    """
    从命中的 scenario 反查 required_indicators 补齐缺失指标。
    """
    for scn_code in valid_scenarios:
        scn = store.get_scenario(scn_code)
        if not scn:
            continue
        required = scn.get("required_indicators", [])
        if isinstance(required, str):
            try:
                required = json.loads(required)
            except json.JSONDecodeError:
                required = []
        for req in required:
            if req not in valid_codes and store.get_indicator(req):
                valid_codes.add(req)
    return valid_codes


def supplement_from_routing(
    plan: dict, valid_codes: set, valid_scenarios: set, routing: dict
) -> tuple:
    """
    从 intent-routing.yaml 的 intent 定义补齐缺失指标/场景。
    匹配 plan 中的 intent_id 或 industry + keywords。
    """
    intent_id = plan.get("intent_id") or plan.get("intent")
    matched_intent = None

    for intent in routing.get("intents", []):
        if intent_id and intent.get("id") == intent_id:
            matched_intent = intent
            break

    if not matched_intent:
        # 用 analysis_type 匹配第一个对应 intent
        atype = plan.get("analysis_type", "")
        for intent in routing.get("intents", []):
            if intent.get("analysis_type") == atype:
                matched_intent = intent
                break

    if not matched_intent:
        return valid_codes, valid_scenarios

    for code in matched_intent.get("default_indicators", []):
        if code not in valid_codes:
            valid_codes.add(code)

    for code in matched_intent.get("default_scenarios", []):
        if code not in valid_scenarios:
            valid_scenarios.add(code)

    return valid_codes, valid_scenarios


def execute_l1_exact(plan: dict, store, routing: dict) -> dict:
    """
    L1: 精确查询 — 用 LLM 输出的 indicator/scenario code 直接查 DB。
    """
    code_check = validate_codes_against_store(plan, store, routing)

    valid_codes = set(code_check["indicator_hits"])
    valid_scenarios = set(code_check["scenario_hits"])

    # 反查补齐
    valid_codes = repair_from_scenario(valid_codes, valid_scenarios, store)

    # 从 routing 补齐
    valid_codes, valid_scenarios = supplement_from_routing(
        plan, valid_codes, valid_scenarios, routing
    )

    # 判定 L1 是否足够
    if len(valid_codes) >= 2:
        indicators = []
        for code in valid_codes:
            ind = store.get_indicator(code)
            if ind:
                indicators.append(ind)
        scenarios = []
        for code in valid_scenarios:
            scn = store.get_scenario(code)
            if scn:
                scenarios.append(scn)

        return {
            "source": "l1_exact",
            "indicators": indicators,
            "scenarios": scenarios,
            "models": plan.get("models", []),
            "analysis_type": plan.get("analysis_type", "descriptive"),
            "skill_chain": plan.get("skill_chain", []),
            "query": plan.get("query", ""),
            "diagnostics": {
                "code_check": code_check,
                "valid_indicators": len(indicators),
                "valid_scenarios": len(scenarios),
            },
        }

    # L1 不够 → 返回部分结果标记
    return {
        "source": "l1_insufficient",
        "insufficient": True,
        "indicators": [store.get_indicator(c) for c in valid_codes if store.get_indicator(c)],
        "scenarios": [store.get_scenario(c) for c in valid_scenarios if store.get_scenario(c)],
        "models": plan.get("models", []),
        "diagnostics": {"code_check": code_check},
    }


def execute_l2_fts(query: str, store, routing: dict) -> dict:
    """
    L2: 降级 → FTS5 + N-gram 向量 + RRF 模糊检索（原有能力，零改动）。
    """
    from scripts.industry.retriever import IndustryRetriever

    retriever = IndustryRetriever(store)
    results = retriever.search(
        query,
        top_k=8,
        use_fts=True,
        use_vector=True,
        use_rrf=True,
    )

    if not results["indicators"] and not results["scenarios"]:
        return {"source": "l2_empty", "indicators": [], "scenarios": [],
                "models": [], "analysis_type": "descriptive"}

    # 尝试从 routing 匹配一个 intent 来注入 models + analysis_type
    matched = _match_intent_from_query(query, routing)

    return {
        "source": "l2_fts_fallback",
        "indicators": results["indicators"],
        "scenarios": results["scenarios"],
        "models": matched.get("models", []),
        "analysis_type": matched.get("analysis_type", "descriptive"),
        "skill_chain": matched.get("skill_chain", []),
        "query": query,
        "keywords": results.get("keywords", []),
        "method": results.get("method", ""),
        "method": results.get("method", "fts"),
    }


def execute_l3_llm_fallback(query: str, routing: dict) -> dict:
    """
    L3: 最终兜底 — 返回空 signal + 上下文信息。
    Agent 收到此 signal 后需用 LLM 自身知识完成分析。

    返回的 routing_context 包含可用行业/模型列表，供 Agent LLM 推理使用。
    """
    return {
        "source": "l3_llm_fallback",
        "indicators": [],
        "scenarios": [],
        "models": [],
        "analysis_type": "descriptive",
        "skill_chain": [],
        "query": query,
        "routing_context": {
            "available_industries": routing.get("available_industries", []),
            "available_intents": [
                {"id": i["id"], "keywords": i.get("keywords", [])[:5],
                 "analysis_type": i.get("analysis_type")}
                for i in routing.get("intents", [])
            ],
            "model_files": routing.get("model_files", {}),
            "analysis_type_chains": routing.get("analysis_type_chains", {}),
        },
        "message": (
            "L1 (structured parse) and L2 (FTS search) both failed. "
            "Agent should use the provided routing_context plus its own "
            "knowledge to analyze: " + query
        ),
    }


def _match_intent_from_query(query: str, routing: dict) -> dict:
    """从 query 中匹配最可能的 intent（简单关键词匹配）"""
    scored = _score_intents(query, routing)
    return scored[0][1] if scored else {}


def _score_intents(query: str, routing: dict) -> list[tuple[int, dict]]:
    """对 intents 按关键词匹配度评分，返回 [(score, intent), ...] 降序"""
    if not query or not routing:
        return []
    scored: list[tuple[int, dict]] = []
    for intent in routing.get("intents", []):
        score = 0
        for kw in intent.get("keywords", []):
            if kw in query:
                score += len(kw)
        for nkw in intent.get("negative_keywords", []):
            if nkw in query:
                score -= len(nkw)
        if score > 0:
            scored.append((score, intent))
    scored.sort(key=lambda x: x[0], reverse=True)
    return scored


def _load_active_learning_config() -> dict:
    """加载主动学习配置"""
    config_path = _project_root / "learn" / "data" / "config.yaml"
    if not config_path.exists():
        return {"enabled": False, "confidence_gap_threshold": 0.10, "max_clarifications_per_session": 3}
    import yaml
    with open(config_path, encoding="utf-8") as f:
        config = yaml.safe_load(f) or {}
    al = config.get("evolution", {}).get("active_learning", {})
    return {
        "enabled": al.get("enabled", False),
        "confidence_gap_threshold": al.get("confidence_gap_threshold", 0.10),
        "max_clarifications_per_session": al.get("max_clarifications_per_session", 3),
    }


def _check_active_learning(
    query: str, routing: dict, session_clarifications: int,
) -> "ClarificationRequest | None":
    """主动学习反问检查

    top-2 intent 得分差距 < 阈值时触发反问。
    """
    al_config = _load_active_learning_config()
    if not al_config["enabled"]:
        return None
    if session_clarifications >= al_config["max_clarifications_per_session"]:
        return None

    scored = _score_intents(query, routing)
    if len(scored) < 2:
        return None

    top_score = scored[0][0]
    second_score = scored[1][0]
    gap = (top_score - second_score) / max(top_score, 1)

    if gap < al_config["confidence_gap_threshold"]:
        return ClarificationRequest(
            options=[
                {"id": scored[0][1].get("id", ""), "name": scored[0][1].get("name", ""),
                 "score": top_score, "indicators": scored[0][1].get("default_indicators", [])[:3]},
                {"id": scored[1][1].get("id", ""), "name": scored[1][1].get("name", ""),
                 "score": second_score, "indicators": scored[1][1].get("default_indicators", [])[:3]},
            ],
            question=f"你要看的是「{scored[0][1].get('name', '选项A')}」还是「{scored[1][1].get('name', '选项B')}」？",
            gap=round(gap, 4),
            session_clarifications=session_clarifications,
        )
    return None


def detect_industry(query: str, routing: dict) -> Optional[str]:
    """从 query 检测行业"""
    if not query or not routing:
        return None
    best = None
    best_score = 0
    for ind in routing.get("available_industries", []):
        score = 0
        for kw in ind.get("trigger_keywords", []):
            if kw in query:
                score += len(kw)
        if score > best_score:
            best_score = score
            best = ind["code"]
    return best if best_score > 0 else None


def parse_intent(
    query: str,
    industry: Optional[str] = None,
    plan_json: Optional[str] = None,
    data_root: str = "knowledge/industry",
    session_clarifications: int = 0,
) -> Union[dict, "ClarificationRequest"]:
    """
    意图解析主入口 — L1 → L2 → L3 三级兜底。

    Args:
        query: 用户原始输入
        industry: 行业代码（可选，不传则自动检测）
        plan_json: LLM 结构化转写 JSON（可选，不传则直接走 L2）
        data_root: 行业数据根目录
        session_clarifications: 当前 session 已反问次数（主动学习用）

    Returns:
        dict 或 ClarificationRequest（主动学习反问）
    """
    from scripts.industry.store import IndustryStore

    routing = load_intent_routing()
    registry = load_live_registry(data_root)
    routing = merge_routing_with_registry(routing, registry)

    # 自动检测行业
    if not industry:
        industry = detect_industry(query, routing) or "fmcg"

    # 主动学习反问检查（feature flag 控制）
    clarification = _check_active_learning(query, routing, session_clarifications)
    if clarification is not None:
        return clarification

    try:
        store = IndustryStore(industry, data_root)
    except Exception:
        store = None

    if store is not None:
        # ── L1: 尝试结构化解析 ──
        plan = None
        if plan_json:
            try:
                plan = json.loads(plan_json)
            except json.JSONDecodeError:
                pass

        if plan:
            plan.setdefault("query", query)
            plan.setdefault("industry", industry)

            # 校验
            validation = validate_plan(plan, routing)
            if validation["valid"] or not validation["errors"]:
                l1_result = execute_l1_exact(plan, store, routing)
                if not l1_result.get("insufficient"):
                    l1_result["industry"] = industry
                    l1_result["plan"] = plan
                    return l1_result

                # L1 不足 → 合并 L2 结果
                l2_result = execute_l2_fts(query, store, routing)
                merged = {
                    "source": "l1_l2_mixed",
                    "indicators": _dedupe_by_code(
                        l1_result["indicators"] + l2_result.get("indicators", [])
                    ),
                    "scenarios": _dedupe_by_code(
                        l1_result["scenarios"] + l2_result.get("scenarios", [])
                    ),
                    "models": list(set(
                        l1_result.get("models", []) + l2_result.get("models", [])
                    )),
                    "analysis_type": l1_result.get("analysis_type")
                    or l2_result.get("analysis_type", "descriptive"),
                    "skill_chain": l1_result.get("skill_chain")
                    or l2_result.get("skill_chain", []),
                    "industry": industry,
                    "diagnostics": {"l1": l1_result.get("diagnostics"), "l2_source": l2_result.get("source")},
                }
                return merged

        # ── L2: FTS 模糊检索 ──
        l2_result = execute_l2_fts(query, store, routing)
        if l2_result["indicators"] or l2_result["scenarios"]:
            l2_result["industry"] = industry
            return l2_result

    # ── L3: 最终兜底 ──
    l3_result = execute_l3_llm_fallback(query, routing)
    l3_result["industry"] = industry
    return l3_result


def _dedupe_by_code(items: List[Dict]) -> List[Dict]:
    """按 code 去重，保留首次出现"""
    seen = set()
    result = []
    for item in items:
        code = item.get("code", "")
        if code and code not in seen:
            seen.add(code)
            result.append(item)
    return result


def main():
    parser = argparse.ArgumentParser(
        description="dAnalyzer 意图解析器 — L1→L2→L3 三级兜底",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 带 LLM 转写 plan (L1 主路径)
  python scripts/intent_parser.py --query "品类表现不好" --plan '{"indicators":["sales_amount"]}' --industry fmcg

  # 无 plan，直接走 L2
  python scripts/intent_parser.py --query "品类分析" --industry fmcg

  # 自动检测行业
  python scripts/intent_parser.py --query "不良率趋势"
""",
    )
    parser.add_argument("--query", "-q", required=True, help="用户原始查询")
    parser.add_argument("--industry", "-i", help="行业代码（可选，自动检测）")
    parser.add_argument("--plan", "-p", help="LLM 结构化转写 JSON")
    parser.add_argument("--data_root", default="knowledge/industry",
                        help="行业数据根目录")
    parser.add_argument("--output", "-o", help="输出到文件")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="打印诊断信息到 stderr")
    parser.add_argument("--session-clarifications", type=int, default=0,
                        help="当前 session 反问次数（主动学习用）")

    args = parser.parse_args()

    result = parse_intent(
        query=args.query,
        industry=args.industry,
        plan_json=args.plan,
        data_root=args.data_root,
        session_clarifications=args.session_clarifications,
    )

    if args.verbose:
        if isinstance(result, dict):
            print(f"[IntentParser] source={result['source']} industry={result.get('industry')} "
                  f"indicators={len(result.get('indicators',[]))} "
                  f"scenarios={len(result.get('scenarios',[]))} "
                  f"models={result.get('models',[])}",
                  file=sys.stderr)
        else:
            print(f"[IntentParser] active_learning clarification question={result.question} "
                  f"gap={result.gap} options={len(result.options)}",
                  file=sys.stderr)

    if isinstance(result, dict):
        output = json.dumps(result, ensure_ascii=False, indent=2, default=str)
    else:
        output = json.dumps({
            "type": "clarification_request",
            "question": result.question,
            "options": result.options,
            "gap": result.gap,
            "session_clarifications": result.session_clarifications,
        }, ensure_ascii=False, indent=2, default=str)

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(output, encoding="utf-8")
        print(f"[IntentParser] Results → {args.output}", file=sys.stderr)
    else:
        print(output)


if __name__ == "__main__":
    main()
