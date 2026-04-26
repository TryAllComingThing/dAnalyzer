#!/usr/bin/env python3
# learn/scripts/instinct-engine.py
# Instinct 引擎 - 匹配并应用 Instinct

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Trigger:
    """触发条件"""
    type: str
    pattern: str = ""
    threshold: int = 0


@dataclass
class Instinct:
    """Instinct 实体"""
    name: str
    description: str
    confidence: float
    trigger: dict[str, Any]
    content: str
    score: float = 0.0


class InstinctEngine:
    """Instinct 引擎 - 匹配并应用 Instinct"""

    def __init__(self, instinct_dir: str | Path) -> None:
        self.instinct_dir = Path(instinct_dir)
        self.instincts: list[Instinct] = []
        self.load_instincts()

    def load_instincts(self) -> None:
        """加载所有 Instinct"""
        if not self.instinct_dir.exists():
            logger.warning(f"Instinct directory not found: {self.instinct_dir}")
            return

        for yaml_file in self.instinct_dir.rglob("*.yaml"):
            try:
                self._load_instinct_file(yaml_file)
            except Exception as e:
                logger.warning(f"Failed to load {yaml_file}: {e}")

        logger.info(f"Loaded {len(self.instincts)} instincts")

    def _load_instinct_file(self, yaml_file: Path) -> None:
        """加载单个 Instinct 文件"""
        with open(yaml_file, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        if not data:
            return

        instinct = Instinct(
            name=data.get("name", yaml_file.stem),
            description=data.get("description", ""),
            confidence=data.get("confidence", 0.5),
            trigger=data.get("trigger", {}),
            content=yaml_file.read_text(encoding="utf-8"),
        )
        self.instincts.append(instinct)

    def match(self, context: dict[str, Any]) -> list[Instinct]:
        """匹配当前上下文"""
        matched = []

        for instinct in self.instincts:
            if self._match_trigger(context, instinct.trigger):
                instinct.score = self._calculate_confidence(context, instinct)
                matched.append(instinct)

        return sorted(matched, key=lambda x: x.score, reverse=True)

    def _match_trigger(self, context: dict[str, Any], trigger: dict[str, Any]) -> bool:
        """匹配触发条件"""
        trigger_type = trigger.get("type", "")

        if trigger_type == "context_match":
            pattern = trigger.get("pattern", "").lower()
            query = context.get("query", "").lower()
            return pattern in query

        if trigger_type == "frequency":
            threshold = trigger.get("threshold", 0)
            return context.get("frequency", 0) >= threshold

        if trigger_type == "error_context":
            pattern = trigger.get("pattern", "")
            return context.get("error_type", "") == pattern

        if trigger_type == "skill_match":
            pattern = trigger.get("pattern", "")
            return pattern in context.get("skill", "")

        return False

    def _calculate_confidence(
        self, context: dict[str, Any], instinct: Instinct
    ) -> float:
        """计算置信度分数"""
        base = instinct.confidence

        # 根据上下文调整
        if context.get("exact_match"):
            base = min(1.0, base * 1.2)

        # 根据匹配程度调整
        match_strength = context.get("match_strength", 1.0)
        base *= match_strength

        return min(1.0, base)

    def apply(self, instinct: Instinct, context: dict[str, Any]) -> str:
        """应用 Instinct，返回建议内容"""
        # 简单实现：返回 content
        # 可扩展：根据 context 动态生成内容
        return instinct.description

    def get_suggestions(
        self, context: dict[str, Any], min_confidence: float = 0.3
    ) -> list[dict[str, Any]]:
        """获取所有匹配的建议"""
        matched = self.match(context)

        suggestions = []
        for instinct in matched:
            if instinct.score >= min_confidence:
                suggestions.append({
                    "name": instinct.name,
                    "description": instinct.description,
                    "confidence": instinct.score,
                    "trigger_type": instinct.trigger.get("type", ""),
                    "content": self.apply(instinct, context),
                })

        return suggestions

    def list_instincts(self) -> list[dict[str, Any]]:
        """列出所有 Instinct"""
        return [
            {
                "name": i.name,
                "description": i.description,
                "confidence": i.confidence,
                "trigger_type": i.trigger.get("type", ""),
            }
            for i in self.instincts
        ]


def get_engine() -> InstinctEngine:
    """获取 InstinctEngine 实例"""
    script_dir = Path(__file__).parent
    instinct_dir = script_dir.parent / "data" / "instincts"
    return InstinctEngine(instinct_dir)


def main() -> None:
    """命令行入口"""
    import argparse

    parser = argparse.ArgumentParser(description="Instinct Engine")
    parser.add_argument("--context", type=str, help="JSON context")
    parser.add_argument("--list", action="store_true", help="List all instincts")
    parser.add_argument(
        "--min-confidence", type=float, default=0.3, help="Minimum confidence threshold"
    )

    args = parser.parse_args()

    engine = get_engine()

    if args.list:
        instincts = engine.list_instincts()
        print(f"Loaded {len(instincts)} instincts:")
        for i, inst in enumerate(instincts, 1):
            print(f"  {i}. {inst['name']} (confidence: {inst['confidence']}, trigger: {inst['trigger_type']})")
        return

    if args.context:
        context = json.loads(args.context)
        suggestions = engine.get_suggestions(context, args.min_confidence)
        print(json.dumps(suggestions, indent=2, ensure_ascii=False))
    else:
        print("No context provided. Use --list to see instincts.")
        print("\nExample usage:")
        print('  python instinct-engine.py --context \'{"query": "查销售额"}\'')
        print('  python instinct-engine.py --list')


if __name__ == "__main__":
    main()
