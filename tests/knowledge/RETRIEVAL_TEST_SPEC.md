# 知识检索管道测试规格

> 版本: 1.0 (2026-05-01)
> 测试目标: intent-routing.yaml → registry_scanner → intent_parser → retrieve_context 全链路
> 测试方式: Python 单元测试（无 LLM 依赖），所有测试确定性可重复

---

## 测试分层

```
Layer 1: 静态配置校验      intent-routing.yaml 结构合法性
Layer 2: registry_scanner  动态注册表扫描 + context-card 生成
Layer 3: intent_parser     L1→L2→L3 三级兜底逻辑
Layer 4: retrieve_context  端到端集成
Layer 5: 触发机制          执行协议 Step 2.5 行为验证（需 Agent 环境）
```

Layer 1-4 为确定性单元测试，每次提交运行。Layer 5 为 Agent 行为测试，需 Claude CLI 环境。

---

## Layer 1: 静态配置校验 (P0)

| ID | 测试项 | 断言 |
|----|--------|------|
| CFG-001 | YAML 可解析 | `yaml.safe_load()` 无异常 |
| CFG-002 | `available_industries` 非空 | `len >= 1` |
| CFG-003 | `intents` 非空 | `len >= 1` |
| CFG-004 | 所有 `intent.id` 唯一 | 无重复 id |
| CFG-005 | 所有 `intent.analysis_type` 合法 | 值 ∈ {descriptive, diagnostic, predictive, prescriptive, exploratory} |
| CFG-006 | 所有 `intent.default_indicators` 至少 2 个 | `len >= 2` |
| CFG-007 | 所有 `intent.default_scenarios` 至少 1 个 | `len >= 1` |
| CFG-008 | `model_files` 路径存在或为 null | path 指向的 `.md` 文件存在，或值为 `null` |
| CFG-009 | `analysis_type_chains` 覆盖所有 analysis_type | 5 种类型均有链定义 |
| CFG-010 | `output_schema` 包含必需字段 | industry, intent_id, analysis_type, indicators, scenarios, skill_chain |

---

## Layer 2: registry_scanner (P0/P1)

| ID | 测试项 | 输入 | 预期 |
|----|--------|------|------|
| REG-001 | `build_registry()` 返回正确结构 | knowledge/industry/ | 含 `industries`, `models`, `generated_at` |
| REG-002 | 扫描到所有 4 个行业 | knowledge/industry/ | ecommerce, finance, logistics, manufacturing |
| REG-003 | 每个行业含 indicators + scenarios | — | `indicator_count > 0, scenario_count > 0` |
| REG-004 | 每个行业含 trigger_keywords | — | `len(keywords) >= 3` |
| REG-005 | trigger_keywords 过滤通用词 | — | 不含 "元", "%", "单", "金额" |
| REG-006 | scan_models() 扫描到文件 | knowledge/model/ | 含 cohort-model, prediction-model 等 |
| REG-007 | build_context_card() 输出 markdown | — | 含 "## 可用知识库资源", "\| indicator_code \|", "\| scenario_code \|" |
| REG-008 | context-card 含分析类型→技能链映射 | — | 含 "\| analysis_type \| skill_chain \|" |
| REG-009 | 新增行业自动发现 | 创建临时目录 + yaml → scan | 新行业出现在 industries 中 |
| REG-010 | 排除 _base 和隐藏目录 | — | `_base` 不在 industries 中 |
| REG-011 | 缓存 60 秒有效 | 连续两次调用 | 第二次命中缓存，结果相同 |

---

## Layer 3: intent_parser (P0/P1)

### 3.1 plan 校验 (P0)

| ID | 测试项 | 输入 | 预期 |
|----|--------|------|------|
| IP-001 | validate_plan 拒绝空 plan | `{}` | `valid=False`, errors 含 "empty" |
| IP-002 | validate_plan 拒绝未知行业 | `industry: "unknown_x"` | `errors` 含 "unknown industry" |
| IP-003 | validate_plan 警告未知 analysis_type | `analysis_type: "magic"` | `warnings` 含 "unknown analysis_type" |
| IP-004 | validate_plan 警告 confidence 越界 | `confidence: 1.5` | `warnings` 含 "out of range" |
| IP-005 | validate_plan 接受完整合法 plan | 合法 JSON | `valid=True`, 无 errors |
| IP-006 | validate_plan 接受 None industry | `industry: ""` | `warnings` 含 "not specified" |

### 3.2 code 校验 (P0)

| ID | 测试项 | 输入 | 预期 |
|----|--------|------|------|
| IP-010 | validate_codes_against_store 正确识别命中 | indicators: ["sales_amount", "order_count"] | hits=[sales_amount, order_count], misses=[] |
| IP-011 | validate_codes_against_store 正确识别未命中 | indicators: ["fake_code"] | hits=[], misses=[fake_code] |
| IP-012 | validate_codes_against_store 混合命中 | indicators: ["sales_amount", "fake"] | hits=[sales_amount], misses=[fake] |

### 3.3 L1/L2/L3 路径 (P1)

| ID | 测试项 | 输入 | 预期 source |
|----|--------|------|-------------|
| IP-020 | L1 精确命中 | 合法 plan + 有效 industry | `l1_exact` |
| IP-021 | L1 不足 → L1+L2 混合 | plan 含部分错误 code | `l1_l2_mixed` |
| IP-022 | L2 FTS 降级（无 plan） | 仅 query，无 plan | `l2_fts_fallback` |
| IP-023 | L2 空 → L3 兜底 | query 无可匹配关键词 | `l3_llm_fallback` |
| IP-024 | L3 返回 routing_context | — | routing_context 含 available_industries, available_intents |
| IP-025 | repair_from_scenario 补齐指标 | scenario 含 required_indicators | 缺失指标被自动添加 |
| IP-026 | supplement_from_routing 补齐 | plan 命中的 intent 有 default_indicators | 缺失指标被补充 |
| IP-027 | detect_industry 关键词匹配 | query: "GMV下降了" | `ecommerce` |
| IP-028 | detect_industry 无匹配时返回 None | query: "你好" | `None` → fallback ecommerce |

### 3.4 边界 (P2)

| ID | 测试项 | 输入 | 预期 |
|----|--------|------|------|
| IP-030 | 空 query | `""` | 不崩溃，返回 L3 |
| IP-031 | 超长 query | 5000 字符 | 不崩溃 |
| IP-032 | plan JSON 非法 | `"not valid json"` | 优雅降级到 L2 |
| IP-033 | 所有 indicator code 都错误 | plan 全为 fake codes | L1 insufficient → L2 |
| IP-034 | negative_keywords 排除 | query 含 "下降" | 跳过 sales_overview intent |

---

## Layer 4: retrieve_context (P1)

| ID | 测试项 | 输入 | 预期 |
|----|--------|------|------|
| RC-001 | 完整 L1 路径 | query + plan + industry | source=l1_exact, 含 indicators/scenarios |
| RC-002 | 无 plan 路径 | query 仅 | source=l2_fts_fallback |
| RC-003 | top_k 限制 | top_k=3 | indicators <= 3 |
| RC-004 | include_score 诊断 | include_score=True | 含 diagnostics 字段 |
| RC-005 | L3 兜底时注入 routing_context | 无匹配 | 含 routing_context + message |
| RC-006 | 自动行业检测 | query 含行业词，不传 industry | industry 被自动填充 |

---

## Layer 5: 触发机制 (P3 — 需 Agent 环境)

| ID | 测试项 | 验证方法 |
|----|--------|----------|
| TRG-001 | 中等复杂度查询强制触发 Step 2.5 | spawn danalyzer → 检查是否调用了 retrieve_context.py |
| TRG-002 | 简单查询允许跳过 Step 2.5 | spawn danalyzer → 检查未调用 retrieve_context.py |
| TRG-003 | l3_llm_fallback 后输出含覆盖不足声明 | spawn danalyzer + 刻意用未知行业 → 检查输出含 "知识库未覆盖" |
| TRG-004 | 行业特征词强制触发（即使简单查询） | query: "配送时效是多少" → 应触发检索 |

---

## 优先级汇总

| 优先级 | 测试数量 | 运行频率 |
|--------|----------|----------|
| P0 | 18 (CFG + IP-validate + IP-code-check) | 每次提交 |
| P1 | 15 (REG + IP-L1/L2/L3 + RC) | 每日 |
| P2 | 5 (IP 边界) | 发版前 |
| P3 | 4 (TRG 触发机制) | 专项测试 |

---

## 测试基础设施

- **框架**: pytest ≥ 7.0，标记 `p0`/`p1`/`p2`/`p3`
- **隔离**: 使用 `tmp_path` fixture 创建临时行业目录，不污染真实 `knowledge/`
- **依赖**: 无外部 API 调用，无 LLM 调用（Layer 1-4）；Layer 5 依赖 Claude CLI
- **执行**: `pytest tests/unit/test_intent_parser.py tests/unit/test_registry_scanner.py -m p0 -v`
