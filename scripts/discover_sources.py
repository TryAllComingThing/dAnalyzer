"""
数据源发现脚本 — 读取 datasources.yaml，输出结构化上下文卡片。

用法:
    python3 dAnalyzer/scripts/discover_sources.py
    python3 dAnalyzer/scripts/discover_sources.py --format json

三层输出:
    files[]          — 全量（人工注册，≤10 个），含 path + size + 行数 + 字段
    file_discovery[] — name + size 仅，上限 30/目录，超出汇总
    databases[]      — name + type + 表名列表，不展开字段
"""

import argparse
import json
import sys
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATASOURCES_PATH = PROJECT_ROOT / "connectors" / "datasources.yaml"

# ── helpers ──────────────────────────────────────────────────

def _file_info(filepath: Path) -> dict:
    """获取单个文件的基本信息"""
    info = {
        "name": filepath.name,
        "size_mb": round(filepath.stat().st_size / (1024 * 1024), 2),
    }
    # csv 估算行数（只读首行判头 + wc -l）
    if filepath.suffix in (".csv", ".tsv"):
        try:
            with open(filepath, encoding="utf-8", errors="replace") as f:
                header = f.readline().rstrip("\n")
            info["columns"] = [c.strip() for c in header.split(",")]
            # 快速行数估算
            import subprocess
            result = subprocess.run(
                ["wc", "-l", str(filepath)],
                capture_output=True, text=True, timeout=5,
            )
            lines = int(result.stdout.strip().split()[0]) - 1  # minus header
            info["row_estimate"] = lines
        except Exception:
            pass
    elif filepath.suffix == ".json":
        try:
            with open(filepath, encoding="utf-8", errors="replace") as f:
                data = json.load(f)
            if isinstance(data, list):
                info["row_estimate"] = len(data)
                if data and isinstance(data[0], dict):
                    info["columns"] = list(data[0].keys())
            elif isinstance(data, dict):
                info["keys"] = list(data.keys())
        except Exception:
            pass
    return info


def _size_fmt(mb: float) -> str:
    if mb < 0.01:
        return f"{mb * 1024:.0f}KB"
    return f"{mb:.1f}MB"


# ── discovery ─────────────────────────────────────────────────

def discover(yaml_path: str | Path = None) -> dict:
    """主入口：读取 yaml，扫描文件系统，返回结构化数据源清单"""
    path = Path(yaml_path) if yaml_path else DATASOURCES_PATH
    if not path.exists():
        return {"error": f"datasources.yaml not found at {path}"}

    config = yaml.safe_load(path.read_text(encoding="utf-8"))

    result = {"files": [], "discovered": [], "databases": []}

    # ── 0. files[] 预置文件 ──
    for f_entry in config.get("files", []):
        fpath = PROJECT_ROOT / f_entry["path"]
        info = {
            "name": f_entry["name"],
            "path": f_entry["path"],
            "description": f_entry.get("description", ""),
            "industry": f_entry.get("industry", ""),
            "exists": fpath.exists(),
        }
        if fpath.exists():
            info.update(_file_info(fpath))
        # schema_hint 补充
        hint = f_entry.get("schema_hint", {})
        if hint.get("columns"):
            info["schema_columns"] = hint["columns"]
        result["files"].append(info)

    # ── 1. file_discovery 动态扫描 ──
    discovery_cfg = config.get("file_discovery", {})
    search_paths = discovery_cfg.get("search_paths", [])
    extensions = list(discovery_cfg.get("extensions", {}).keys())
    if not extensions:
        extensions = ["csv", "tsv", "json", "jsonl", "xlsx", "xls"]

    MAX_PER_DIR = 30

    seen = set(f["name"] for f in result["files"])  # 去重

    for sp in search_paths:
        spath = PROJECT_ROOT / sp
        if not spath.is_dir():
            continue

        matched = []
        for ext in extensions:
            matched.extend(spath.glob(f"*.{ext}"))

        matched.sort(key=lambda p: p.stat().st_size, reverse=True)

        dir_result = {"search_path": sp, "files": [], "overflow": 0}
        for fp in matched:
            if fp.name in seen:
                continue
            seen.add(fp.name)
            if len(dir_result["files"]) >= MAX_PER_DIR:
                dir_result["overflow"] = len(matched) - MAX_PER_DIR
                break
            fi = _file_info(fp)
            fi.pop("columns", None)  # 动态发现的文件不展开字段
            fi.pop("row_estimate", None)
            dir_result["files"].append(fi)

        if dir_result["files"] or dir_result["overflow"]:
            result["discovered"].append(dir_result)

    # ── 2. databases[] ──
    for db in config.get("databases", []):
        db_info = {
            "name": db["name"],
            "type": db["type"],
            "description": db.get("description", ""),
            "industry": db.get("industry", ""),
        }
        hint = db.get("schema_hint", {})
        tables = hint.get("tables", [])
        db_info["tables"] = [
            {
                "name": t["name"],
                "description": t.get("description", ""),
                "row_estimate": t.get("row_estimate"),
                "columns": [c["name"] for c in t.get("columns", [])],
            }
            for t in tables
        ]
        db_info["table_count"] = len(tables)
        result["databases"].append(db_info)

    return result


# ── formatters ────────────────────────────────────────────────

def format_context_card(data: dict) -> str:
    """紧凑文本格式，给 Agent 注入上下文"""
    lines = ["## 可用数据源\n"]

    # --- files ---
    files = data.get("files", [])
    if files:
        lines.append("### 预置文件\n")
        for f in files:
            exists = "✓" if f.get("exists") else "✗"
            size = _size_fmt(f.get("size_mb", 0)) if f.get("exists") else "N/A"
            rows = f.get("row_estimate", "?")
            cols = f.get("schema_columns") or f.get("columns", [])
            cols_str = ", ".join(cols[:12])
            if len(cols) > 12:
                cols_str += f" …(+{len(cols)-12})"
            lines.append(
                f"- **{f['name']}** [{exists}] `{f['path']}` "
                f"| {size} | {rows}行 | {f.get('industry','')}"
            )
            if cols_str:
                lines.append(f"  字段: {cols_str}")
        lines.append("")

    # --- discovered ---
    discovered = data.get("discovered", [])
    if discovered:
        lines.append("### 动态发现\n")
        for d in discovered:
            lines.append(f"**{d['search_path']}/** ({len(d['files'])} 文件):")
            for f in d["files"]:
                lines.append(f"  - `{f['name']}` ({_size_fmt(f['size_mb'])})")
            if d.get("overflow"):
                lines.append(f"  - …还有 {d['overflow']} 个文件未列出")
        lines.append("")

    # --- databases ---
    databases = data.get("databases", [])
    if databases:
        lines.append("### 数据库\n")
        for db in databases:
            lines.append(
                f"- **{db['name']}** ({db['type']}) — {db['description']} "
                f"| {db['table_count']} 表"
            )
            for t in db.get("tables", []):
                rows = f"~{t['row_estimate']}行" if t.get("row_estimate") else "?行"
                cols_preview = ", ".join(t.get("columns", [])[:8])
                lines.append(f"  - `{t['name']}` ({rows}): {cols_preview}")
        lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="dAnalyzer 数据源发现")
    parser.add_argument("--config", default=str(DATASOURCES_PATH),
                        help="datasources.yaml 路径")
    parser.add_argument("--format", choices=["json", "context-card"],
                        default="context-card", help="输出格式")
    args = parser.parse_args()

    data = discover(args.config)

    if "error" in data:
        print(data["error"], file=sys.stderr)
        sys.exit(1)

    if args.format == "json":
        print(json.dumps(data, ensure_ascii=False, indent=2, default=str))
    else:
        print(format_context_card(data))


if __name__ == "__main__":
    main()
