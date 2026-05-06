---
name: context-retriever
description: Use when industry context is needed — retrieves indicators, scenarios, and models via three-tier fallback (L1 exact → L2 fuzzy → L3 LLM). Do NOT use for simple queries with clearly defined metrics, or when industry context is already cached and unchanged.
---

# 动态上下文检索器 (Context Retriever) — Phase 2

## 概述

行业知识动态检索技能。通过三级兜底路径（L1 精确 code 查询 → L2 FTS5+向量+RRF 模糊搜索 → L3 LLM 推理）检索行业指标定义、分析场景、推荐模型和技能链。由 danalyzer-core 知识注入步骤自动调用，也可手动触发。新增行业/指标零配置自动可用。

## 何时使用

- **触发:** danalyzer-core 知识注入步骤输出结构化 plan — 自动调用
- **触发:** 用户输入含行业特征词（如"配送时效"、"销售额"、"产能利用率"）
- **触发:** 需要指标公式、SQL 模板或分析场景定义
- **不要用于:** 指标定义已明确的简单查询（如"查询订单数量"）
- **不要用于:** 行业上下文已缓存且未变更时的重复检索

---

## 核心步骤

1. **获取动态注册表** — `python3 dAnalyzer/scripts/registry_scanner.py --format context-card`，获取当前所有可用行业/指标 code/场景/模型 → 详见「执行指令 > Step 1」
2. **结构化检索**（主路径）— `python3 dAnalyzer/scripts/retrieve_context.py --query "<原文>" --plan '<JSON>'`，走 L1→L2→L3 三级兜底 → 详见「执行指令 > Step 2」
3. **降级检索**（无 plan 时）— `python3 dAnalyzer/scripts/retrieve_context.py --query "关键词" --industry <行业>`，直接走 L2 模糊搜索 → 详见「降级路径」
4. **解析返回结果** — 提取 indicators/scenarios/models/analysis_type/skill_chain/source → 详见「返回格式」
5. **注入上下文** — 将检索结果注入 danalyzer-core 的执行上下文

---

## 执行指令

> 对应 核心步骤 第 1-3 步

### Step 1: 获取动态注册表

```bash
python3 dAnalyzer/scripts/registry_scanner.py --format context-card
```

获取当前 knowledge/ 下所有可用行业、指标 code、场景 code、模型列表。
**新增行业/指标零配置自动出现**。

### Step 2: 精确检索（主路径，带结构化 plan）

```bash
python3 dAnalyzer/scripts/retrieve_context.py \
  --query "<用户原始查询>" \
  --plan '<danalyzer-core Step 2.5b 输出的 JSON>'
```

内部走 L1 精确 → L2 模糊 → L3 推理三级兜底。`--industry` 可选（不传则自动检测）。

### 降级路径（无 plan，直接模糊搜索）

```bash
python3 dAnalyzer/scripts/retrieve_context.py --query "关键词" --industry fmcg
```

## 返回格式

> 对应 核心步骤 第 4 步

```json
{
  "indicators": [{"code": "sales_amount", "name": "销售额", "formula": "SUM(...)", ...}],
  "scenarios": [{"code": "sales_trend", "name": "销售趋势分析", ...}],
  "models": ["attribution-model"],
  "analysis_type": "diagnostic",
  "skill_chain": ["data-query", "data-clean", "data-analysis", "model", "visual", "report", "security"],
  "industry": "fmcg",
  "source": "l1_exact"
}
```

`source` 字段标识走的哪级兜底：
- `l1_exact` — 结构化解析精确命中
- `l1_l2_mixed` — 部分命中 + FTS 补齐
- `l2_fts_fallback` — L1 失败，FTS 模糊搜索接住
- `l3_llm_fallback` — 全部失败，返回 routing_context 供 Agent 推理

## 依赖

- `scripts/intent_parser.py` — 意图解析器（L1→L2→L3）
- `scripts/industry/store.py` — IndustryStore 存储引擎
- `scripts/industry/retriever.py` — IndustryRetriever（L2 FTS5+向量+RRF）
- `knowledge/intent-routing.yaml` — 意图路由映射
- `knowledge/industry/{industry}/` — 行业 YAML 配置

---

## 常见借口与纠正

| 借口 | 现实 |
|--------|---------|
| "这个行业我熟悉，不需要检索" | 指标定义和公式可能因行业而异；凭记忆导致口径错误 |
| "先用着，错了再查" | 检索只需秒级；用错误指标执行完整分析链的代价远大于检索成本 |
| "L1 精确命中了，不需要看 L2/L3 补充" | L1 命中不保证覆盖所有相关场景；`source` 字段显示 `l1_l2_mixed` 时说明有补充 |

## 红线

- **context-card 为空:** registry_scanner.py 返回空 — knowledge/ 目录可能损坏或行业配置缺失
- **所有 code 均为编造:** plan JSON 中每个 code 都不在 context-card 中 — L1 校验层将全部过滤；需重新生成 plan
- **三级全部失败:** L1→L2→L3 全部失败 (source: l3_llm_fallback) — 所有结果标记为不确定推理
- **行业不匹配:** 检索结果明显不匹配用户行业 — 检查 `--industry` 自动检测并重试

## 验证

1. 验证注册表已扫描：确认 `registry_scanner.py --format context-card` 已运行且返回非空
2. 验证检索已执行：确认 `retrieve_context.py` 已运行且返回有效 JSON（含 indicators/scenarios/models）
3. 验证上下文已注入：确认检索到的指标、场景和模型已出现在分析上下文中
4. 验证来源层级：检查 `source` 字段确认走了哪级兜底
5. 验证不确定性已标注：确认 l3_llm_fallback 结果在分析中显式标注为不确定
