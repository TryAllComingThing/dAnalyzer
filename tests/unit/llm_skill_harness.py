"""
LLM Skill 单元测试共享 Harness — 避免 4 个测试文件重复 350 行样板代码.

用法 (每个 skill 测试文件只需 ~20 行):
    from .llm_skill_harness import SkillTestHarness, SkillTestCase

    RULES = '''...'''
    CASES = [SkillTestCase(id="C01", label="...", data=[...], task="...",
                           must_contain=["..."], must_not=["..."]), ...]

    harness = SkillTestHarness("skill-name", RULES, CASES, "任务描述",
                               '{{"id":"...","result":{{}},...}}')

    if __name__ == "__main__":
        sys.exit(harness.run())

    # pytest 集成:
    # def test_skill(): harness.run()
"""

import json
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent


@dataclass
class SkillTestCase:
    """单个 LLM Skill 测试用例"""
    id: str
    label: str
    data: list[dict]
    task: str
    must_contain: list[str] = field(default_factory=list)
    must_not: list[str] = field(default_factory=list)


class SkillTestHarness:
    """LLM 注入式 Skill 单元测试的共享运行器"""

    def __init__(
        self,
        skill_name: str,
        rules: str,
        cases: list[SkillTestCase],
        domain_desc: str,
        output_schema: str,
        batch_size: int = 2,
        timeout: int = 300,
    ):
        self.skill_name = skill_name
        self.rules = rules
        self.cases = cases
        self.domain_desc = domain_desc
        self.output_schema = output_schema
        self.batch_size = batch_size
        self.timeout = timeout

    # ── Prompt 构建 ──────────────────────────────────────────

    def build_prompt(self, batch: list[SkillTestCase]) -> str:
        parts = []
        for c in batch:
            data_str = json.dumps(c.data, ensure_ascii=False)
            parts.append(f"[{c.id}] {c.label}\n数据: {data_str}\n指令: {c.task}")
        joined = "\n\n".join(parts)

        return f"""{self.rules}

对以下{self.domain_desc}输出结果, 每行一个 JSON.

{joined}

输出 {len(batch)} 行 JSON, 格式: {self.output_schema}"""

    # ── 响应解析 ─────────────────────────────────────────────

    @staticmethod
    def parse_response(text: str) -> list[dict]:
        results = []
        for line in text.split("\n"):
            line = line.strip()
            if line.startswith("{") and '"id"' in line:
                try:
                    obj = json.loads(line)
                    if "id" in obj:
                        results.append(obj)
                except json.JSONDecodeError:
                    continue
        return results

    # ── 断言 ─────────────────────────────────────────────────

    @staticmethod
    def assert_case(case: SkillTestCase, actual: dict | None) -> tuple[bool, str]:
        """返回 (pass, 错误描述). 大小写不敏感.

        must_contain 非空 → 关键词子串匹配.
        must_contain 为空 → 结构校验 (id 匹配 + result/summary 非空).
        """
        if actual is None:
            return False, "无响应"

        # 结构校验模式: 无关键词要求, 只验证 JSON 结构完整
        if not case.must_contain:
            errs = []
            if actual.get("id") != case.id:
                errs.append(f"id 不匹配: {actual.get('id')} != {case.id}")
            # 检查是否有任何内容字段 (result / signals / dimensions / recommendations / sql ...)
            content_keys = {"result", "signals", "dimensions", "recommendations",
                           "metrics", "anomalies", "report_type", "sql", "overall_score"}
            has_content = any(k in actual and actual[k] for k in content_keys)
            if not has_content:
                errs.append("无有效内容字段")
            summary_val = actual.get("summary", "")
            if not isinstance(summary_val, str) or len(summary_val.strip()) < 1:
                errs.append(f"summary 缺失: '{summary_val}'")
            if errs:
                return False, "; ".join(errs)
            return True, ""

        # 关键词模式: 大小写不敏感子串匹配
        result_str = json.dumps(actual, ensure_ascii=False).lower()
        missing = [k for k in case.must_contain if k.lower() not in result_str]
        unexpected = [k for k in case.must_not if k.lower() in result_str]
        errs = []
        if missing:
            errs.append(f"缺: {missing}")
        if unexpected:
            errs.append(f"多余: {unexpected}")
        if errs:
            return False, "; ".join(errs)
        return True, ""

    # ── 单批次执行 ───────────────────────────────────────────

    def run_batch(self, batch: list[SkillTestCase]) -> tuple[list[dict], float, str | None]:
        """运行一批用例, 返回 (解析结果列表, 耗时秒, 错误信息或 None)"""
        prompt = self.build_prompt(batch)
        t0 = time.time()
        try:
            result = subprocess.run(
                ["claude", "--print", "-p", prompt],
                cwd=str(PROJECT_ROOT),
                capture_output=True, text=True, timeout=self.timeout,
            )
        except subprocess.TimeoutExpired:
            return [], time.time() - t0, f"超时 ({self.timeout}s)"
        elapsed = time.time() - t0

        if result.returncode != 0:
            return [], elapsed, f"claude 退出码 {result.returncode}: {result.stderr[:100]}"

        plans = self.parse_response(result.stdout)
        return plans, elapsed, None

    # ── 全量运行 ─────────────────────────────────────────────

    def run(self) -> int:
        """运行全部用例, 打印结果, 返回 exit code (0=全部通过)."""
        print(f"{self.skill_name} Skill 单元测试")
        passed = 0
        failed = 0

        for i in range(0, len(self.cases), self.batch_size):
            batch = self.cases[i:i + self.batch_size]
            batch_ids = [c.id for c in batch]

            plans, elapsed, error = self.run_batch(batch)

            if error:
                print(f"  ❌ claude 失败: {error}")
                failed += len(batch)
                continue

            print(f"  批次 {batch_ids}: {elapsed:.0f}s, {len(plans)}/{len(batch)}")

            for case in batch:
                actual = next((p for p in plans if p["id"] == case.id), None)
                ok, err = self.assert_case(case, actual)
                if ok:
                    summary = actual.get("summary", "")[:60] if actual else ""
                    print(f"  ✅ {case.id} {case.label}: {summary}")
                    passed += 1
                else:
                    print(f"  ❌ {case.id} {case.label}: {err}")
                    failed += 1

        total = passed + failed
        pct = passed / total * 100 if total else 0
        print(f"\n{'='*50}")
        print(f"  通过: {passed}/{total} ({pct:.0f}%)")
        return 0 if failed == 0 else 1
