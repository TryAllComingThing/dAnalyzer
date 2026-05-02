"""
data-analysis Skill 单元测试 — 验证 LLM 正确执行描述性统计/趋势/相关性分析
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from llm_skill_harness import SkillTestHarness, SkillTestCase

ANALYSIS_RULES = """
# 数据分析规则

## 描述性统计
均值=SUM/N, 中位数=排序取中, 标准差=SQRT(SUM((x-μ)²)/N)
IQR=Q3-Q1, 异常值: < Q1-1.5*IQR 或 > Q3+1.5*IQR

## 趋势分析
环比=(本期-上期)/上期*100%, 同比=(本期-去年同期)/去年同期*100%
连续3期同向变化→趋势信号, 环比变化>10%→显著

## 相关性
Pearson r: |r|>0.7强, >0.4中, <0.2弱
相关性≠因果性

## 洞察规则
输出必须含: 数据特征+变化方向+显著差异+业务含义+建议行动
"""

CASES = [
    SkillTestCase("A01", "描述性统计", [
        {"product": "A", "sales": 100}, {"product": "B", "sales": 120},
        {"product": "C", "sales": 110}, {"product": "D", "sales": 90},
        {"product": "E", "sales": 130},
    ], "计算 sales 的均值、中位数、标准差、Q1、Q3、IQR",
     must_contain=["均值", "中位数", "标准差", "iqr", "110"]),

    SkillTestCase("A02", "趋势判断", [
        {"month": "1月", "gmv": 1000}, {"month": "2月", "gmv": 1100},
        {"month": "3月", "gmv": 1050}, {"month": "4月", "gmv": 1200},
        {"month": "5月", "gmv": 1150}, {"month": "6月", "gmv": 1300},
    ], "分析 GMV 趋势: 计算各月环比, 判断是否存在上升趋势",
     must_contain=["环比", "上升", "趋势"]),

    SkillTestCase("A03", "相关性分析", [
        {"x": 1, "y": 2}, {"x": 2, "y": 4},
        {"x": 3, "y": 6}, {"x": 4, "y": 8},
        {"x": 5, "y": 10},
    ], "计算 x 和 y 的 Pearson 相关系数, 判断相关强度和方向",
     must_contain=["相关", "1.0", "强", "正"]),

    SkillTestCase("A04", "异常值检测", [
        {"id": 1, "value": 10}, {"id": 2, "value": 12},
        {"id": 3, "value": 11}, {"id": 4, "value": 9},
        {"id": 5, "value": 100}, {"id": 6, "value": 8},
    ], "用 IQR 法检测 value 字段的异常值",
     must_contain=["异常", "100", "IQR"]),
]

harness = SkillTestHarness(
    "data-analysis", ANALYSIS_RULES, CASES, "分析任务",
    '{"id":"A01","statistics":{},"insights":["..."],"summary":"..."}',
    timeout=180,
)

if __name__ == "__main__":
    sys.exit(harness.run())
