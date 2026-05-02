"""
知识库注册表扫描器 — Phase 2

动态扫描 knowledge/ 目录，构建可用的行业、指标、场景、模型注册表。
新增行业/指标/场景无需手动更新 intent-routing.yaml，自动出现在检索上下文中。

用法:
    # 输出完整注册表
    python scripts/registry_scanner.py

    # 输出 LLM 上下文卡片（精简版，注入 Step 2.5 prompt）
    python scripts/registry_scanner.py --format context-card

    # 输出行业列表
    python scripts/registry_scanner.py --industries-only

    # 输出到文件
    python scripts/registry_scanner.py --output registry.json
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List, Dict

_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from scripts.industry.store import IndustryStore


def scan_industries(data_root: str = "knowledge/industry") -> Dict[str, dict]:
    """
    扫描 knowledge/industry/ 下所有行业目录（排除 _base 和隐藏目录）。
    对每个行业，从 IndustryStore (SQLite) 读取当前可用的指标和场景。
    自动生成触发关键词（从指标/场景的名称和关键词字段拼接）。
    """
    root = Path(data_root)
    if not root.exists():
        return {}

    industries = {}
    for d in sorted(root.iterdir()):
        if not d.is_dir() or d.name.startswith("_") or d.name.startswith("."):
            continue

        industry_code = d.name
        try:
            store = IndustryStore(industry_code, data_root)
        except Exception as e:
            print(f"[RegistryScanner] Warning: skip {industry_code}: {e}", file=sys.stderr)
            continue

        indicators = {}
        trigger_keywords = set()

        for ind in store.get_all_indicators():
            code = ind.get("code", "")
            kw = ind.get("keywords", [])
            if isinstance(kw, str):
                try:
                    kw = json.loads(kw)
                except json.JSONDecodeError:
                    kw = []

            indicators[code] = {
                "name": ind.get("name", code),
                "keywords": kw,
                "formula": ind.get("formula", ""),
                "importance": ind.get("importance", 0),
            }
            trigger_keywords.update(kw)
            trigger_keywords.add(ind.get("name", ""))

        scenarios = {}
        for scn in store.get_all_scenarios():
            code = scn.get("code", "")
            kw = scn.get("keywords", [])
            if isinstance(kw, str):
                try:
                    kw = json.loads(kw)
                except json.JSONDecodeError:
                    kw = []

            required = scn.get("required_indicators", [])
            if isinstance(required, str):
                try:
                    required = json.loads(required)
                except json.JSONDecodeError:
                    required = []

            scenarios[code] = {
                "name": scn.get("name", code),
                "keywords": kw,
                "required_indicators": required,
                "satisfaction": scn.get("satisfaction", 0),
            }
            trigger_keywords.update(kw)
            trigger_keywords.add(scn.get("name", ""))

        # 只保留有区分度的关键词（过滤太通用的词）
        generic_words = {"元", "%", "单", "小时", "金额", "数量"}
        filtered_keywords = sorted(
            [k for k in trigger_keywords if k and len(k) > 1 and k not in generic_words],
            key=lambda k: -len(k)
        )[:30]

        industries[industry_code] = {
            "name": _industry_display_name(industry_code),
            "indicator_count": len(indicators),
            "scenario_count": len(scenarios),
            "indicators": indicators,
            "scenarios": scenarios,
            "trigger_keywords": filtered_keywords,
        }

    return industries


def scan_models(model_root: str = "knowledge/model") -> Dict[str, dict]:
    """扫描 knowledge/model/ 下所有模型定义文件"""
    root = Path(model_root)
    if not root.exists():
        return {}

    models = {}
    for f in sorted(root.iterdir()):
        if f.is_dir() or f.name.startswith(".") or f.suffix != ".md":
            continue
        code = f.stem
        name = _extract_model_name(f)
        models[code] = {
            "name": name,
            "file": f"{model_root}/{f.name}",
        }
    return models


def build_registry(data_root: str = "knowledge/industry",
                   model_root: str = "knowledge/model") -> dict:
    """构建完整注册表"""
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "data_root": data_root,
        "industries": scan_industries(data_root),
        "models": scan_models(model_root),
    }


def build_context_card(registry: dict) -> str:
    """
    构建 LLM 上下文卡片 — 紧凑文本格式，注入 Step 2.5 prompt。
    包含所有可用行业、指标 code、场景 code、模型 file，供 LLM 精准填 plan JSON。
    """
    lines = []
    lines.append("## 可用知识库资源（动态扫描）\n")

    # 行业 + 指标/场景
    for code, ind_data in registry.get("industries", {}).items():
        name = ind_data.get("name", code)
        lines.append(f"### {name} (`{code}`)")
        lines.append(f"触发词: {', '.join(ind_data.get('trigger_keywords', [])[:12])}")
        lines.append("")

        indicators = ind_data.get("indicators", {})
        if indicators:
            lines.append("| indicator_code | 名称 | 公式 |")
            lines.append("|---|---|---|")
            for icode, idata in indicators.items():
                formula = (idata.get("formula", "") or "")[:60]
                lines.append(f"| `{icode}` | {idata['name']} | {formula} |")
            lines.append("")

        scenarios = ind_data.get("scenarios", {})
        if scenarios:
            lines.append("| scenario_code | 名称 | 必需指标 |")
            lines.append("|---|---|---|")
            for scode, sdata in scenarios.items():
                required = ", ".join(f"`{r}`" for r in sdata.get("required_indicators", []))
                lines.append(f"| `{scode}` | {sdata['name']} | {required} |")
            lines.append("")

    # 模型
    models = registry.get("models", {})
    if models:
        lines.append("### 可用分析模型\n")
        lines.append("| model_file | 名称 |")
        lines.append("|---|---|")
        for mcode, mdata in models.items():
            lines.append(f"| `{mcode}` | {mdata['name']} |")
        lines.append("")

    # 分析类型 → 技能链参考
    lines.append("### 分析类型 → 技能链（从 intent-routing.yaml）\n")
    try:
        import yaml
        routing_path = _project_root / "knowledge" / "intent-routing.yaml"
        if routing_path.exists():
            routing = yaml.safe_load(routing_path.read_text(encoding="utf-8"))
            chains = routing.get("analysis_type_chains", {})
            lines.append("| analysis_type | skill_chain |")
            lines.append("|---|---|")
            for atype, chain in chains.items():
                lines.append(f"| `{atype}` | {' → '.join(chain)} |")
    except Exception:
        pass

    return "\n".join(lines)


def _industry_display_name(code: str) -> str:
    """行业代码 → 中文名"""
    names = {
        "fmcg": "快消",
    }
    return names.get(code, code)


def _extract_model_name(filepath: Path) -> str:
    """从模型 markdown 文件提取名称"""
    try:
        first_line = filepath.read_text(encoding="utf-8").split("\n")[0]
        return first_line.lstrip("# ").strip()
    except Exception:
        return filepath.stem


def main():
    parser = argparse.ArgumentParser(
        description="dAnalyzer 知识库注册表扫描器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--data_root", default="knowledge/industry",
                        help="行业数据根目录")
    parser.add_argument("--model_root", default="knowledge/model",
                        help="模型目录")
    parser.add_argument("--format", choices=["json", "context-card"],
                        default="json", help="输出格式")
    parser.add_argument("--industries-only", action="store_true",
                        help="仅输出行业列表")
    parser.add_argument("--output", "-o", help="输出到文件")

    args = parser.parse_args()

    registry = build_registry(args.data_root, args.model_root)

    if args.industries_only:
        output = {
            "industries": list(registry["industries"].keys()),
            "models": list(registry["models"].keys()),
            "generated_at": registry["generated_at"],
        }
    elif args.format == "context-card":
        output = build_context_card(registry)
        # context-card 是文本，不包装 JSON
        if args.output:
            Path(args.output).write_text(output, encoding="utf-8")
            print(f"[RegistryScanner] Context card → {args.output}", file=sys.stderr)
        else:
            print(output)
        return
    else:
        output = registry

    json_output = json.dumps(output, ensure_ascii=False, indent=2, default=str)

    if args.output:
        Path(args.output).write_text(json_output, encoding="utf-8")
        print(f"[RegistryScanner] Registry → {args.output}", file=sys.stderr)
    else:
        print(json_output)


if __name__ == "__main__":
    main()
