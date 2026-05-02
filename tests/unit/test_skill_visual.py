"""
visual Skill 单元测试 — 验证 LLM 正确遵循图表选择/配色/ECharts 配置/响应式/Connector 规则
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from llm_skill_harness import SkillTestHarness, SkillTestCase

VISUAL_RULES = """
# 图表可视化规则

## 图表选择 (根据数据特征)
| 数据特征 | 推荐图表 |
|----------|----------|
| 趋势变化/时间序列 | 折线图 (line) |
| 占比分布 | 饼图/环形图 (pie) |
| 对比分析/排名 | 柱状图/条形图 (bar) |
| 关联关系 | 散点图 (scatter) |

## ECharts HTML 输出
- 使用 ECharts 5.4.3 CDN: https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js
- option 必须含: title, xAxis, yAxis, legend, tooltip, series, color, grid
- 标题: 14px bold, 图表上方居中
- 坐标轴: 12px 标签, 浅灰轴线 1px
- 图例: 右侧或底部, 间距 8px, 支持点击筛选
- 数据标签: 柱状图在顶部/柱内, 折线图在点上方/尾部, 饼图在扇区内/图例
- 响应式: window.addEventListener('resize', function() { chart.resize(); })
- CSS media query: PC/平板/手机自适应

## 配色规范 (严格遵守)
主色序列 (最多6色): #1E88E5, #43A047, #FB8C00, #E53935, #8E24AA, #00ACC1
场景色: 增长→#43A047, 下降→#E53935, 同比→#1E88E5, 环比→#00ACC1
单图最多6种颜色, 超出用同色系深浅区分

## 数据读写
- 必须通过 Connector 读数据 (JSONConnector/CSVConnector), 不直接 open()/json.load()
- 导出通过 Connector (CSVConnector/ExcelConnector)

## 输出格式
每行一个 JSON:
{"id":"V01","chart_type":"line/pie/bar/scatter","colors_used":["#xxx"],"has_title":true/false,
 "has_resize":true/false,"uses_connector":true/false,"review_checklist":["标题","坐标轴","图例"],
 "summary":"..."}
"""

CASES = [
    SkillTestCase("V01", "趋势→折线图", [
        {"month": "1月", "sales": 100}, {"month": "2月", "sales": 120},
        {"month": "3月", "sales": 110}, {"month": "4月", "sales": 140},
        {"month": "5月", "sales": 130}, {"month": "6月", "sales": 160},
    ], "分析此月度销售数据, 选择合适图表类型, 输出图表 HTML, 数据量=10000",
     must_contain=["line", "resize"]),

    SkillTestCase("V02", "占比→饼图", [
        {"category": "食品", "pct": 35}, {"category": "饮料", "pct": 25},
        {"category": "日化", "pct": 20}, {"category": "其他", "pct": 20},
    ], "展示各品类占比分布, 选择合适图表, 输出 HTML",
     must_contain=["pie", "legend", "#1E88E5"]),

    SkillTestCase("V03", "6色上限", [
        {"category": f"品类{i}", "value": 100 - i * 8} for i in range(1, 9)
    ], "生成8个类别的对比图表, 严格控制配色不超过6种主色, 输出 HTML",
     must_contain=["bar", "6"]),

    SkillTestCase("V04", "响应式设计", [
        {"month": "1月", "value": 100}, {"month": "2月", "value": 120},
        {"month": "3月", "value": 110},
    ], "生成多设备适配的图表 HTML, 包含响应式代码 (resize 监听和 media query)",
     must_contain=["resize"]),

    SkillTestCase("V05", "禁止直接文件IO", [
        {"id": 1, "name": "A", "value": 100},
        {"id": 2, "name": "B", "value": 200},
    ], "读取数据生成图表, 必须用 Connector 方式读取数据, 不能直接用 open()",
     must_contain=["connector"],
     must_not=["json.load(open"]),

    SkillTestCase("V06", "ECharts必备配置", [
        {"month": "1月", "gmv": 1000, "orders": 120},
        {"month": "2月", "gmv": 1100, "orders": 130},
    ], "生成双系列图表 HTML, 确保包含完整 ECharts 配置",
     must_contain=["title", "tooltip", "legend", "xAxis", "yAxis"]),

    SkillTestCase("V07", "下降趋势用红色", [
        {"month": "1月", "revenue": 500}, {"month": "2月", "revenue": 450},
        {"month": "3月", "revenue": 400}, {"month": "4月", "revenue": 350},
        {"month": "5月", "revenue": 300},
    ], "展示收入持续下降趋势, 使用合适的颜色标识",
     must_contain=["#E53935"],
     must_not=["#43A047"]),
]

harness = SkillTestHarness(
    "visual", VISUAL_RULES, CASES, "图表生成任务",
    '{"id":"<用例ID>","chart_type":"...","colors_used":[...],"has_title":true/false,'
    '"has_legend":true/false,"has_resize":true/false,"uses_connector":true/false,'
    '"review_checks_passed":N,"summary":"..."}',
    batch_size=1, timeout=300,
)

if __name__ == "__main__":
    sys.exit(harness.run())
