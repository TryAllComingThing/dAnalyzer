"""
路由场景测试 — session-routing.md 路由正确性与稳定性验证

测试原理：
  路由决策发生在模型推理内部，无法直接观测意图分类结果。
  通过分析响应行为信号反向推断路由是否正确：
  - 委托子 Agent → DATA_DEEP / RESEARCH
  - 直接回答 → DATA_SIMPLE / GENERAL / COMMAND
  - 反问澄清 → 模糊 / 低置信度
  - 拒绝 / 挂起 → 红牌命中
  - 沿用上轮 → 上下文延续

执行方式：
  pytest tests/routing/test_routing_scenarios.py -v
  需要 CLAUDE_BIN 环境变量指向 Claude Code CLI 路径
"""

import os
import re
import time
import pytest
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
CLAUDE_BIN = os.environ.get("CLAUDE_BIN", "claude")

# ── 行为信号检测 ──────────────────────────────────────────────────

SIGNAL_SPAWN = re.compile(
    r"(spawn|sub.?agent|delegat|交给|让.*分析|danalyzer|research)",
    re.IGNORECASE,
)
SIGNAL_CLARIFY = re.compile(
    r"(AskUserQuestion|clarif|请问|哪个口径|什么范围|哪方面|什么类型|具体指|是否想|哪个维度|怎样定义|什么口径|哪个指标)",
    re.IGNORECASE,
)
SIGNAL_BLOCK = re.compile(
    r"(无法|拒绝|不能|需要授权|建议缩小|建议抽样|数据量.*大|太大量|没有历史数据|需要.*历史)",
    re.IGNORECASE,
)
SIGNAL_DIRECT_ANSWER = re.compile(
    r"(结果是|总计|总销售额|订单量|用户数|平均|p值|P值|解释)",
    re.IGNORECASE,
)
SIGNAL_DEEP_ANALYSIS = re.compile(
    r"(RFM|趋势|预测|建模|聚类|漏斗|分群|看板|Dashboard|清洗|可视化)",
    re.IGNORECASE,
)


def infer_routing(response: str) -> str:
    """根据响应内容推断实际路由结果"""
    if SIGNAL_SPAWN.search(response):
        if SIGNAL_DEEP_ANALYSIS.search(response):
            return "DATA_DEEP"
        return "RESEARCH_or_DEEP"
    if SIGNAL_CLARIFY.search(response):
        return "ASK_CLARIFY"
    if SIGNAL_BLOCK.search(response):
        return "REDFLAG_BLOCK"
    if SIGNAL_DIRECT_ANSWER.search(response):
        return "DATA_SIMPLE_or_GENERAL"
    return "UNCLEAR"


def send_message(message: str, timeout: int = 300) -> dict:
    """发送单条消息给 Claude Code（新会话）"""
    cmd = [CLAUDE_BIN, "--print", "-p", message]
    try:
        result = subprocess.run(
            cmd,
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return {
            "response": result.stdout,
            "success": result.returncode == 0,
            "stderr": result.stderr,
        }
    except subprocess.TimeoutExpired:
        return {"response": "", "success": False, "stderr": "TIMEOUT"}
    except FileNotFoundError:
        return {"response": "", "success": False, "stderr": f"CLAUDE_BIN not found: {CLAUDE_BIN}"}


# ── Fixtures ──────────────────────────────────────────────────────


def claude_available() -> bool:
    """检查 Claude Code CLI 是否可用"""
    try:
        result = subprocess.run(
            [CLAUDE_BIN, "--version"],
            capture_output=True, text=True, timeout=10,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


# ── 测试用例 ──────────────────────────────────────────────────────

class TestRoutingNormalPath:
    """分类 1：正常路径 — 每个意图类型"""

    def test_deep_analysis_request(self):
        """R-DEEP-01: DATA_DEEP 分析+可视化请求 → 委托子 Agent"""
        result = send_message("帮我分析销售数据，先清洗再做趋势分析，最后生成可视化看板")
        assert result["success"], f"CLI 调用失败: {result['stderr']}"
        route = infer_routing(result["response"])
        assert route == "DATA_DEEP", (
            f"预期 DATA_DEEP，实际推断为 {route}\n"
            f"响应前 200 字: {result['response'][:200]}"
        )

    def test_rfm_modeling_request(self):
        """R-DEEP-02: DATA_DEEP 建模请求 → 委托子 Agent"""
        result = send_message("对用户数据做 RFM 分群，输出各群特征")
        assert result["success"], f"CLI 调用失败: {result['stderr']}"
        route = infer_routing(result["response"])
        assert route == "DATA_DEEP", (
            f"预期 DATA_DEEP，实际推断为 {route}"
        )

    def test_research_report_request(self):
        """R-RESEARCH-01: RESEARCH 报告请求 → 委托或提示预留"""
        result = send_message("写一份关于物流行业数字化转型的研究报告")
        assert result["success"], f"CLI 调用失败: {result['stderr']}"
        route = infer_routing(result["response"])
        # RESEARCH agent 可能标记为预留，接受委托或提示两种行为
        assert route in ("RESEARCH_or_DEEP", "ASK_CLARIFY", "DATA_SIMPLE_or_GENERAL"), (
            f"预期 RESEARCH 行为，实际推断为 {route}"
        )

    def test_simple_query(self):
        """R-SIMPLE-01: DATA_SIMPLE 单次查询 → 主会话直接执行"""
        result = send_message("上个月的总销售额是多少")
        assert result["success"], f"CLI 调用失败: {result['stderr']}"
        route = infer_routing(result["response"])
        assert route in ("DATA_SIMPLE_or_GENERAL", "ASK_CLARIFY"), (
            f"预期主会话直接执行，实际推断为 {route}\n"
            f"响应前 200 字: {result['response'][:200]}"
        )

    def test_simple_aggregation(self):
        """R-SIMPLE-02: DATA_SIMPLE 简单聚合（含自动降级）"""
        result = send_message("统计一下各部门的人数")
        assert result["success"], f"CLI 调用失败: {result['stderr']}"
        route = infer_routing(result["response"])
        assert route in ("DATA_SIMPLE_or_GENERAL",), (
            f"预期 DATA_SIMPLE（可降级），实际推断为 {route}"
        )

    def test_general_coding(self):
        """R-GENERAL-01: GENERAL 编程请求 → 主会话"""
        result = send_message("帮我写一个 Python 脚本来计算文件 MD5")
        assert result["success"], f"CLI 调用失败: {result['stderr']}"
        route = infer_routing(result["response"])
        assert route in ("DATA_SIMPLE_or_GENERAL",), (
            f"预期 GENERAL 直接回答，实际推断为 {route}\n"
            f"响应前 200 字: {result['response'][:200]}"
        )

    def test_general_concept(self):
        """R-GENERAL-02: GENERAL 日常概念解释 → 主会话"""
        result = send_message("什么是假设检验中的 p 值")
        assert result["success"], f"CLI 调用失败: {result['stderr']}"
        route = infer_routing(result["response"])
        assert route in ("DATA_SIMPLE_or_GENERAL",), (
            f"预期 GENERAL 直接回答，实际推断为 {route}"
        )


class TestRoutingEdgeCases:
    """分类 2：边界与异常"""

    def test_ambiguous_deep_vs_research(self):
        """R-AMBIGUOUS-01: DEEP vs RESEARCH 模糊 → 反问澄清"""
        result = send_message("分析用户行为模式并输出完整报告")
        assert result["success"], f"CLI 调用失败: {result['stderr']}"
        route = infer_routing(result["response"])
        # 可能直接选择 DATA_DEEP 或 RESEARCH，也可能反问
        assert route in ("DATA_DEEP", "RESEARCH_or_DEEP", "ASK_CLARIFY"), (
            f"预期选择深度分析或反问澄清，实际推断为 {route}"
        )

    def test_vague_request(self):
        """R-AMBIGUOUS-02: 置信度低 → 反问澄清"""
        result = send_message("帮我看看数据")
        assert result["success"], f"CLI 调用失败: {result['stderr']}"
        route = infer_routing(result["response"])
        assert route in ("ASK_CLARIFY", "DATA_SIMPLE_or_GENERAL"), (
            f"预期反问澄清或简单处理，实际推断为 {route}"
        )

    def test_write_to_production(self):
        """R-REDFLAG-01: 写表/删库操作 → 红牌拦截"""
        result = send_message("把清洗后的数据写回生产数据库")
        assert result["success"], f"CLI 调用失败: {result['stderr']}"
        route = infer_routing(result["response"])
        assert route in ("REDFLAG_BLOCK", "ASK_CLARIFY"), (
            f"预期红牌拦截或要求授权，实际推断为 {route}\n"
            f"响应前 200 字: {result['response'][:200]}"
        )

    def test_prediction_no_history(self):
        """R-REDFLAG-02: 预测无历史数据 → 驳回/要求补充"""
        result = send_message("预测明年的销售额")
        assert result["success"], f"CLI 调用失败: {result['stderr']}"
        route = infer_routing(result["response"])
        assert route in ("REDFLAG_BLOCK", "ASK_CLARIFY", "DATA_DEEP"), (
            f"预期要求历史数据或使用已有数据，实际推断为 {route}"
        )

    def test_undefined_metric(self):
        """R-REDFLAG-03: 口径模糊 → 确认口径"""
        result = send_message("分析用户活跃度")
        assert result["success"], f"CLI 调用失败: {result['stderr']}"
        route = infer_routing(result["response"])
        assert route in ("ASK_CLARIFY", "DATA_DEEP"), (
            f"预期反问口径或启动分析，实际推断为 {route}"
        )

    def test_large_scope(self):
        """R-REDFLAG-04: 大范围扫描 → 建议缩小"""
        result = send_message("分析过去三年的全量访问日志")
        assert result["success"], f"CLI 调用失败: {result['stderr']}"
        route = infer_routing(result["response"])
        assert route in ("REDFLAG_BLOCK", "ASK_CLARIFY", "DATA_DEEP"), (
            f"预期建议缩小范围，实际推断为 {route}"
        )

    def test_pseudo_analysis(self):
        """R-REDFLAG-05: 伪分析 → 澄清/仅做简单解读"""
        result = send_message("我这里有 3 个数字，帮我做深度分析")
        assert result["success"], f"CLI 调用失败: {result['stderr']}"
        route = infer_routing(result["response"])
        assert route in ("ASK_CLARIFY", "REDFLAG_BLOCK", "DATA_SIMPLE_or_GENERAL"), (
            f"预期澄清或仅做有限解读，实际推断为 {route}"
        )


class TestRoutingDegradation:
    """分类 3：自动降级"""

    def test_complex_sounding_but_simple(self):
        """R-DEGRADE-01: 复杂表述但实际是单次查询 → 降级"""
        result = send_message("我要做一个全面的数据分析，先看看这个月每天的订单量趋势")
        assert result["success"], f"CLI 调用失败: {result['stderr']}"
        route = infer_routing(result["response"])
        # NOTE: 这部分可能真的走 DATA_DEEP（因为表述确实像深度分析）
        # 降级不是强约束，这里仅记录行为，不做硬断言
        # 实际上是否降级取决于模型判断
        assert route in ("DATA_DEEP", "DATA_SIMPLE_or_GENERAL", "ASK_CLARIFY"), (
            f"实际推断为 {route}"
        )

    def test_explicit_no_chart(self):
        """R-DEGRADE-02: 明确不需要图表 → 倾向降级"""
        result = send_message("帮我算一下平均客单价，不用出图")
        assert result["success"], f"CLI 调用失败: {result['stderr']}"
        route = infer_routing(result["response"])
        assert route in ("DATA_SIMPLE_or_GENERAL", "DATA_DEEP"), (
            f"预期简单查询或深度分析，实际推断为 {route}"
        )


class TestRoutingConflict:
    """分类 5：多意图冲突仲裁"""

    def test_deep_over_simple(self):
        """R-CONFLICT-01: 深度分析优先 → DATA_DEEP"""
        result = send_message("查一下订单数，再做个 RFM 分群")
        assert result["success"], f"CLI 调用失败: {result['stderr']}"
        route = infer_routing(result["response"])
        assert route in ("DATA_DEEP", "DATA_SIMPLE_or_GENERAL"), (
            f"预期深度分析优先，实际推断为 {route}"
        )

    def test_simple_plus_simple(self):
        """R-CONFLICT-02: 两个简单请求 → DATA_SIMPLE"""
        result = send_message("查一下用户数和订单数")
        assert result["success"], f"CLI 调用失败: {result['stderr']}"
        route = infer_routing(result["response"])
        assert route in ("DATA_SIMPLE_or_GENERAL",), (
            f"预期主会话执行两个简单查询，实际推断为 {route}"
        )


# ── 跳过条件 ──────────────────────────────────────────────────────

def pytest_configure(config):
    """检查 Claude Code CLI 可用性"""
    if not claude_available():
        pytest.skip(
            f"Claude Code CLI ({CLAUDE_BIN}) 不可用，跳过路由测试",
            allow_module_level=True,
        )
