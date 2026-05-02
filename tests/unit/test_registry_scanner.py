"""
registry_scanner 单元测试 — 动态注册表扫描

测试目标:
  - build_registry() 扫描真实 knowledge/ 目录
  - build_context_card() 输出格式
  - 缓存行为
  - 新增行业自动发现
  - 排除 _base / 隐藏目录

用法:
  pytest tests/unit/test_registry_scanner.py -m p0 -v
  pytest tests/unit/test_registry_scanner.py -m "p0 or p1" -v
"""

import json
import sys
import time
from pathlib import Path
from textwrap import dedent

import pytest
import yaml

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.registry_scanner import (
    scan_industries,
    scan_models,
    build_registry,
    build_context_card,
)
from scripts.industry.store import IndustryStore


# ═══════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════

def _make_indicator_yaml(path: Path, code: str, name: str,
                         keywords: list[str] = None):
    """创建符合 IndustryStore sync.py 期望的 indicator YAML"""
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "code": code,
        "name": name,
        "industry": path.parent.parent.name,
        "keywords": keywords or [name],
        "definition": {"formula": f"SUM({code})"},
        "stats": {"importance": 5},
    }
    path.write_text(yaml.dump(data, allow_unicode=True), encoding="utf-8")


def _make_scenario_yaml(path: Path, code: str, name: str,
                        keywords: list[str] = None,
                        required_indicators: list[str] = None):
    """创建符合 sync.py 期望的 scenario YAML（required 在 content 下）"""
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "code": code,
        "name": name,
        "industry": path.parent.parent.name,
        "keywords": keywords or [name],
        "content": {
            "required": required_indicators or [],
            "optional": [],
            "dimensions": {},
        },
    }
    path.write_text(yaml.dump(data, allow_unicode=True), encoding="utf-8")


def _make_model_md(path: Path, name: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"# {name}\n\nTest model.\n", encoding="utf-8")


@pytest.fixture
def populated_knowledge(tmp_path):
    """创建含 2 个行业的临时 knowledge 目录 + 独立的 models 目录"""
    data_root = tmp_path / "knowledge_data"
    data_root.mkdir()
    (data_root / "_base" / "indicators").mkdir(parents=True)

    # 行业 A
    ia = data_root / "industry_a"
    _make_indicator_yaml(ia / "indicators" / "revenue.yaml",
                         "revenue", "营收", ["营收", "收入", "GMV"])
    _make_indicator_yaml(ia / "indicators" / "order_cnt.yaml",
                         "order_cnt", "订单量", ["订单", "订单量"])
    _make_scenario_yaml(ia / "scenarios" / "trend.yaml",
                        "trend", "趋势分析", ["趋势"],
                        required_indicators=["revenue", "order_cnt"])

    # 行业 B
    ib = data_root / "industry_b"
    _make_indicator_yaml(ib / "indicators" / "throughput.yaml",
                         "throughput", "吞吐量", ["吞吐", "产能"])
    _make_scenario_yaml(ib / "scenarios" / "efficiency.yaml",
                        "efficiency", "效率分析", ["效率"],
                        required_indicators=["throughput"])

    # 模型独立目录（不在 data_root 下，避免被 scan_industries 误识别为行业）
    models_dir = tmp_path / "models"
    _make_model_md(models_dir / "test-model.md", "测试模型")

    return data_root, models_dir


# ═══════════════════════════════════════════════════════════════
# P0 — 真实 knowledge/ 目录扫描
# ═══════════════════════════════════════════════════════════════

@pytest.mark.p0
class TestRealKnowledgeP0:
    """对项目真实 knowledge/ 目录的断言 (P0)"""

    def test_registry_has_fmcg_industry(self):
        reg = build_registry()
        industries = reg["industries"]
        assert "fmcg" in industries

    def test_each_industry_has_indicators(self):
        reg = build_registry()
        for code, data in reg["industries"].items():
            assert data["indicator_count"] >= 1, \
                f"{code} should have at least 1 indicator"
            assert len(data["indicators"]) == data["indicator_count"]

    def test_each_industry_has_scenarios(self):
        reg = build_registry()
        for code, data in reg["industries"].items():
            assert data["scenario_count"] >= 1, \
                f"{code} should have at least 1 scenario"

    def test_each_industry_has_trigger_keywords(self):
        reg = build_registry()
        for code, data in reg["industries"].items():
            kws = data["trigger_keywords"]
            assert len(kws) >= 3, f"{code}: trigger_keywords too few ({len(kws)})"

    def test_trigger_keywords_exclude_generic_words(self):
        reg = build_registry()
        for data in reg["industries"].values():
            generic = {"元", "%", "单", "小时", "金额", "数量"}
            found = set(data["trigger_keywords"]) & generic
            assert not found, f"generic words in keywords: {found}"

    def test_models_scanned(self):
        reg = build_registry()
        models = reg["models"]
        assert len(models) >= 1
        assert "cohort-model" in models or "prediction-model" in models

    def test_registry_structure(self):
        reg = build_registry()
        assert "generated_at" in reg
        assert "data_root" in reg
        assert "industries" in reg
        assert "models" in reg

    def test_context_card_format(self):
        reg = build_registry()
        card = build_context_card(reg)
        assert "## 可用知识库资源" in card
        assert "| indicator_code |" in card
        assert "| scenario_code |" in card
        assert "### 可用分析模型" in card
        assert "### 分析类型 → 技能链" in card

    def test_context_card_mentions_fmcg(self):
        reg = build_registry()
        card = build_context_card(reg)
        assert "快消" in card, "context-card should mention 快消"


# ═══════════════════════════════════════════════════════════════
# P1 — 动态扫描 (临时目录)
# ═══════════════════════════════════════════════════════════════

@pytest.mark.p1
class TestDynamicScanP1:
    """临时目录动态扫描 (P1)"""

    def test_scan_discovers_all_industries(self, populated_knowledge):
        data_root, models_dir = populated_knowledge
        industries = scan_industries(str(data_root))
        assert set(industries.keys()) == {"industry_a", "industry_b"}

    def test_scan_excludes_base(self, populated_knowledge):
        data_root, models_dir = populated_knowledge
        industries = scan_industries(str(data_root))
        assert "_base" not in industries

    def test_scan_excludes_hidden(self, populated_knowledge):
        data_root, models_dir = populated_knowledge
        (data_root / ".hidden_industry" / "indicators").mkdir(parents=True)
        (data_root / ".hidden_industry" / "indicators" / "x.yaml").write_text(
            '{"code":"x","name":"X"}')
        industries = scan_industries(str(data_root))
        assert ".hidden_industry" not in industries

    def test_indicator_details(self, populated_knowledge):
        data_root, models_dir = populated_knowledge
        industries = scan_industries(str(data_root))
        inds = industries["industry_a"]["indicators"]
        assert "revenue" in inds
        assert inds["revenue"]["name"] == "营收"
        assert "GMV" in inds["revenue"]["keywords"]

    def test_scenario_details(self, populated_knowledge):
        data_root, models_dir = populated_knowledge
        industries = scan_industries(str(data_root))
        scns = industries["industry_a"]["scenarios"]
        assert "trend" in scns
        assert "revenue" in scns["trend"]["required_indicators"]

    def test_scan_models(self, populated_knowledge):
        data_root, models_dir = populated_knowledge
        models = scan_models(str(models_dir))
        assert "test-model" in models
        assert models["test-model"]["name"] == "测试模型"

    def test_new_industry_auto_discovered(self, populated_knowledge):
        data_root, models_dir = populated_knowledge
        """新增行业目录后，下次扫描自动出现"""
        new = data_root / "industry_c"
        _make_indicator_yaml(new / "indicators" / "metric.yaml",
                             "metric", "指标", ["指标"])
        _make_scenario_yaml(new / "scenarios" / "analysis.yaml",
                            "analysis", "分析", required_indicators=["metric"])

        industries = scan_industries(str(data_root))
        assert "industry_c" in industries
        assert industries["industry_c"]["indicator_count"] == 1
        assert industries["industry_c"]["scenario_count"] == 1

    def test_build_registry_with_temp_data(self, populated_knowledge):
        data_root, models_dir = populated_knowledge
        reg = build_registry(
            data_root=str(data_root),
            model_root=str(models_dir),
        )
        assert len(reg["industries"]) == 2
        assert len(reg["models"]) == 1

    def test_context_card_includes_dynamic_industries(self, populated_knowledge):
        data_root, models_dir = populated_knowledge
        reg = build_registry(
            data_root=str(data_root),
            model_root=str(models_dir),
        )
        card = build_context_card(reg)
        assert "industry_a" in card
        assert "revenue" in card
        assert "trend" in card


# ═══════════════════════════════════════════════════════════════
# P2 — 边界
# ═══════════════════════════════════════════════════════════════

@pytest.mark.p2
class TestScannerEdgeCasesP2:
    """边界情况 (P2)"""

    def test_empty_directory(self, tmp_path):
        industries = scan_industries(str(tmp_path))
        assert industries == {}

    def test_nonexistent_directory(self):
        industries = scan_industries("/nonexistent/path/xyz")
        assert industries == {}

    def test_industry_with_no_yaml_files(self, tmp_path):
        (tmp_path / "empty_ind" / "indicators").mkdir(parents=True)
        (tmp_path / "empty_ind" / "scenarios").mkdir(parents=True)
        (tmp_path / "_base" / "indicators").mkdir(parents=True)

        industries = scan_industries(str(tmp_path))
        # IndustryStore 初始化可能失败（无 yaml），应被跳过
        assert isinstance(industries, dict)

    def test_context_card_empty_registry(self):
        reg = {"industries": {}, "models": {}}
        card = build_context_card(reg)
        assert "## 可用知识库资源" in card
        # 无行业时不应崩溃
        assert isinstance(card, str)
