---
name: context-retriever
description: 行业上下文检索 — 通过意图解析器（L1→L2→L3 兜底）检索行业指标、场景、模型
---

# 动态上下文检索器 (Context Retriever) — Phase 2

## When to Activate

- 用户输入包含行业特征词时
- 需要生成 SQL 查询前
- danalyzer-core Step 2.5 输出结构化 plan 后

## 执行指令

### Step 1: 获取动态注册表

```bash
python scripts/registry_scanner.py --format context-card
```

获取当前 knowledge/ 下所有可用行业、指标 code、场景 code、模型列表。
**新增行业/指标零配置自动出现**。

### Step 2: 精确检索（主路径，带结构化 plan）

```bash
python scripts/retrieve_context.py \
  --query "<用户原始查询>" \
  --plan '<danalyzer-core Step 2.5b 输出的 JSON>'
```

内部走 L1 精确 → L2 模糊 → L3 推理三级兜底。`--industry` 可选（不传则自动检测）。

### 降级路径（无 plan，直接模糊搜索）

```bash
python scripts/retrieve_context.py --query "关键词" --industry fmcg
```

## 返回格式

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
