"""
dashboard Skill 单元测试 — 验证多图表看板 HTML 生成
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from llm_skill_harness import SkillTestHarness, SkillTestCase

DASHBOARD_RULES = """
# 数据看板规则

## 看板组成
- KPI 摘要卡片区: 汇总指标数值（销售额/订单量/转化率等），卡片式布局
- 图表区: 多个 ECharts 图表，网格布局排列
- 看板标题 + 时间范围展示

## 布局规范
- PC: 2-3 列网格，KPI 卡片横向排列
- 平板: 2 列，图表等宽
- 手机: 1 列堆叠

## ECharts 集成
- 使用 ECharts 5.4.3 CDN: https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js
- 每个图表独立 echarts.init()，不同 DOM 容器
- 所有图表共用 window.addEventListener('resize', ...) 批量 resize

## 配色规范
主色序列: #1E88E5, #43A047, #FB8C00, #E53935, #8E24AA, #00ACC1
增长→#43A047, 下降→#E53935

## 数据读写
- 必须通过 Connector 读数据，不直接 open()/json.load()

## 输出格式
每行一个 JSON:
{"id":"D01","chart_count":N,"has_kpi_cards":true/false,
 "has_responsive":true/false,"uses_connector":true/false,
 "review_checks_passed":N,"summary":"..."}
"""

CASES = [
    SkillTestCase("D01", "多图表看板", [
        {"month": "1月", "sales": 1000, "orders": 120, "users": 80},
        {"month": "2月", "sales": 1200, "orders": 140, "users": 95},
        {"month": "3月", "sales": 1100, "orders": 130, "users": 90},
        {"month": "4月", "sales": 1400, "orders": 160, "users": 110},
    ], "生成一个包含销售趋势折线图、订单柱状图、用户趋势折线图的完整看板 HTML, 含 KPI 摘要卡片",
     must_contain=["echarts", "grid", "resize"]),

    SkillTestCase("D02", "KPI摘要卡片", [
        {"month": "1月", "sales": 1000, "orders": 120},
        {"month": "2月", "sales": 1200, "orders": 140},
        {"month": "3月", "sales": 1100, "orders": 130},
    ], "生成看板 HTML, 顶部展示总销售额、总订单量、月均销售额等 KPI 摘要卡片",
     must_contain=["card", "kpi"]),

    SkillTestCase("D03", "响应式多端适配", [
        {"month": "1月", "sales": 100}, {"month": "2月", "sales": 120},
        {"month": "3月", "sales": 110},
    ], "生成支持 PC/平板/手机三端自适应的看板 HTML",
     must_contain=["resize"]),

    SkillTestCase("D04", "多图表独立实例", [
        {"category": "食品", "sales": 500, "pct": 35},
        {"category": "饮料", "sales": 350, "pct": 25},
        {"category": "日化", "sales": 280, "pct": 20},
        {"category": "其他", "sales": 270, "pct": 20},
    ], "生成包含饼图(占比)和柱状图(对比)两个独立图表的看板 HTML, 每个图表使用独立的 DOM 容器",
     must_contain=["pie", "bar"]),

    SkillTestCase("D05", "Connector读取数据", [
        {"id": 1, "name": "A", "sales": 100, "orders": 20},
        {"id": 2, "name": "B", "sales": 200, "orders": 30},
    ], "通过 Connector 读取数据生成看板, 不使用 open() 直接读文件",
     must_contain=["connector"],
     must_not=["json.load(open"]),
]

harness = SkillTestHarness(
    "dashboard", DASHBOARD_RULES, CASES, "看板生成任务",
    '{"id":"<用例ID>","chart_count":N,"has_kpi_cards":true/false,'
    '"has_responsive":true/false,"uses_connector":true/false,'
    '"review_checks_passed":N,"summary":"..."}',
    batch_size=1, timeout=600,
)

if __name__ == "__main__":
    sys.exit(harness.run())
