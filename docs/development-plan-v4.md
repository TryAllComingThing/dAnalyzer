# dAnalyzer 自进化 V4 开发计划

> 基线文档: docs/self-evolution-v4.md
> 基线配置: learn/data/config.yaml (v4 配置段已就绪)
> 基线 Schema: knowledge/_schemas/* (3 个 schema 文件已就绪)
> 基线映射: knowledge/_base/cross_industry_mappings.yaml (已就绪)
> 日期: 2026-05-02

---

## 开发原则

1. **每个 Phase 产出可独立验证的东西。** 不写"为将来准备"的代码。
2. **TDD 先行。** 每个模块先用属性测试定义契约，再写实现。
3. **纯函数优先。** 信号检测、聚类、置信度计算全部是纯函数，I/O 隔离在边界。
4. **Schema 防线。** 所有持久化数据在写入/加载时通过 Pydantic schema 校验。

---

## Phase 1: 数据模型与基础桩（V4-P0 前半）

**目标：** 定义所有数据类、创建测试夹具、让信号检测器能 import 并跑空测试。

### 1.1 核心数据模型

**创建 `learn/ingest/models.py`**
- `Observation` frozen dataclass（v2 格式，含 candidates + context + user_anon_id）
- `DetectedSignal` frozen dataclass（SignalType 枚举 + 全字段）
- `Candidate` dataclass（id + score + rank）
- `ObservationContext` dataclass（time_period + query_raw + trigger_source）
- `CounterRecord` dataclass（session 级 + by_scenario）
- Pydantic schema 校验：`ObservationV2`、`SignalV2`

**验证：** `pytest tests/unit/test_evolution_models.py -v` 全部 pass

### 1.2 测试夹具

**创建 `tests/fixtures/evolution_fixtures.py`**
- 3 组预定义 observation pairs（correction / supplement / refinement 各一组）
- 1 个完整 session 的 5-turn observation 序列
- 1 组 reinforcement 场景
- 1 组 counterfactual 场景
- 1 组 preference 场景

**验证：** 夹具可 import，observation 通过 Pydantic 校验

### 1.3 纯函数桩

**创建以下纯函数签名（仅签名 + 类型标注 + docstring，不实现）：**
- `learn/ingest/signal_detector.py::classify_query_pair`
- `learn/ingest/reinforcement_detector.py::detect_reinforcement`
- `learn/ingest/counterfactual_check.py::check_counterfactual`
- `learn/ingest/preference_detector.py::detect_preference`
- `learn/analyze/signal_analyzer.py::cluster_signals`
- `learn/analyze/signal_analyzer.py::generate_hypothesis`
- `learn/analyze/propagation.py::propagate_correction`
- `learn/validate/validator.py::validate_hypothesis`
- `learn/apply/applier.py::apply_hypothesis`
- `learn/apply/weight_climber.py::evaluate_climb`

**验证：** mypy strict mode 无错误，所有 import 可解析

**文件量：** ~6 个文件，~250 行

---

## Phase 2: 信号检测引擎（V4-P0 后半 + V4-P1）

**目标：** 实现 4 类信号检测，从 observation 到 JSONL 的完整链路可运行。

### 2.1 纠正/补充/调整/扩展检测

**实现 `learn/ingest/signal_detector.py`**
- `classify_query_pair(prev, curr) → DetectedSignal | None`
- 逻辑 = v3 的集合运算 + 部分重叠纠正（replacement_ratio + 否定词正则）
- 纯函数，无 I/O

**单元测试：**
- 完全不相交 → correction
- 纯扩充 → supplement
- 纯缩减 → narrowing（不产生信号）
- 完全一致 → no_change（不产生信号）
- 部分重叠 + 否定词 + 替换比 >= 0.5 → correction（部分重叠纠正）
- 部分重叠 + 无否定词 → refinement
- scenario 变化 → unrelated
- 空 indicators → insufficient_data
- 属性测试：`classify_query_pair` 总是返回合法 SignalType 或 None

**文件量：** ~150 行

### 2.2 强化信号检测

**实现 `learn/ingest/reinforcement_detector.py`**
- `detect_reinforcement(session_observations) → list[DetectedSignal]`
- 规则：用户在收到结果后产生新查询（unrelated scenario）或 session 结束→前一轮标记为 accepted

**单元测试：**
- 2 轮 session：T1 查询 → T2 新 unrelated 查询 → T1 产生 reinforcement
- 2 轮 session：T1 查询 → T2 correction → T1 不产生 reinforcement
- 单轮 session → 不产生 reinforcement
- 属性测试：每 session 最多产生 (turns - 1) 个 reinforcement

**文件量：** ~60 行

### 2.3 反事实信号检测

**实现 `learn/ingest/counterfactual_check.py`**
- `check_counterfactual(observation, user_selected_indicators) → CounterfactualResult | None`
- 规则：user_selected 的指标出现在 candidates 中但不在 retrieved 中 → counterfactual

**单元测试：**
- 用户选中的指标在 candidates rank > K → counterfactual hit
- 用户选中的指标不在 candidates → 返回 None（这是纯 correction）
- 用户选中的指标在 retrieved → 返回 None（系统已正确推荐）
- 属性测试：hit 时 ranks 必须都 > len(retrieved)

**文件量：** ~50 行

### 2.4 偏好信号检测

**实现 `learn/ingest/preference_detector.py`**
- `detect_preference(observation, user_chart_choice, user_report_choice) → list[DetectedSignal]`
- 规则：系统推荐的 chart_type/report_format 与用户实际选择不同 → preference 信号

**单元测试：**
- 推荐 heatmap，用户选 line_chart → chart preference
- 推荐 pdf，用户选 excel → report preference
- 用户直接接受 → 无信号

**文件量：** ~60 行

### 2.5 信号写入

**实现 `learn/ingest/counter_writer.py`**
- `append_signal(path, signal)` — 原子追加一行 JSONL
- `write_counters(path, counters)` — 原子写入 counter JSON
- 使用 `os.fsync` 确保落盘

**验证：** 集成测试 — 写入 → 读取 → 校验数据完整

**文件量：** ~40 行

### 2.6 重写 Session Hook

**修改 `learn/hooks/session-summary`**
从 bash 脚本改为调用 Python 入口：

```bash
#!/usr/bin/env bash
set -euo pipefail
python3 -m learn.ingest.session_processor \
    --session-id "$CLAUDE_SESSION_ID" \
    --obs-dir "learn/data/observations/sessions" \
    --signals-dir "learn/data/signals" \
    --counters-dir "learn/data/counters"
```

**创建 `learn/ingest/session_processor.py`**（Python 入口）
- 加载 session 的所有 observation
- 遍历相邻 turns → 调用 `classify_query_pair`
- 检测 reinforcement
- 检测 counterfactual
- 检测 preference
- 写入所有信号 JSONL
- 聚合计数器写入

**文件量：** ~80 行

**Phase 2 验证标准：**
1. 用测试夹具的 5-turn session 跑完整链路
2. 验证 corrections.jsonl / supplements.jsonl / refinements.jsonl / reinforcements.jsonl / counterfactuals.jsonl / preferences.jsonl 输出正确
3. 验证 counters/{date}.jsonl 输出正确
4. `pytest tests/unit/test_evolution_signals.py tests/integration/test_evolution_pipeline.py -v` 全绿

**Phase 2 总文件量：** ~520 行

---

## Phase 3: 聚类与假设生成（V4-P3 前半）

**目标：** 从信号 JSONL 到 hypothesis YAML 的完整链路。

### 3.1 共现矩阵构建

**实现 `learn/analyze/proximity_builder.py`**
- `build_cooccurrence_matrix(template_dir, industry) → dict`
- 扫描模板 + scenario 配置，构建指标共现矩阵
- 归一到 [0, 1]

**单元测试：**
- 同模板内共现 → 高邻近度
- 不同模板无共现 → 邻近度 = 0
- 矩阵对称性

**文件量：** ~80 行

### 3.2 置信度计算

**实现 `learn/analyze/confidence.py`**
- `calculate_confidence(signals, industry) → float`
- 四维公式：频次×0.35 + 一致性×0.30 + 多样性×0.20 + 邻近加分×0.15
- 信号衰减加权（基于 user_anon_id）
- 反事实邻近加分

**单元测试：**
- 5 条同方向 correction → confidence ≈ 0.83
- 4 条分散方向 correction → confidence 明显低于集中方向
- 单用户贡献所有信号 → diversity 部分的 score 不变（频次和一致性照算，仅 diversity 不受影响... 实际上 diversity 看的是 session 数，同一用户可以在不同 session 中）
  - 重新想：diversity_score 看 unique_sessions，不受 user_anon_id 影响
  - 单用户信号衰减只影响 consistency 加权

**文件量：** ~80 行

### 3.3 信号聚类

**实现 `learn/analyze/signal_analyzer.py`**
- `cluster_corrections(signals) → list[Cluster]` — 按 industry+scenario+方向分组
- `cluster_supplements(signals) → list[Cluster]` — 按 industry+scenario+indicator 分组
- `cluster_refinements(signals) → list[Cluster]`
- `cluster_extensions(signals) → list[Cluster]` — LCS 路径相似度
- `cluster_l3_fallbacks(signals) → list[Cluster]` — N-gram 关键词提取
- `cluster_preferences(signals) → list[Cluster]`
- `generate_hypotheses(clusters) → list[Hypothesis]` — 产出 hypothesis YAML

**文件量：** ~200 行

### 3.4 语义邻近传播

**实现 `learn/analyze/propagation.py`**
- `propagate_correction(hypothesis, proximity_matrix) → list[PropagationEntry]`
- 行业内传播（3.3 节逻辑）
- 跨行业传播（3.5 节逻辑）
  - 加载 `cross_industry_mappings.yaml`
  - 迁移幅度 = 源幅度 × 0.25 × mapping_confidence
  - 跨行业传播标记为 `progressive_apply` 永不走 `full_apply`

**单元测试：**
- 直接纠正 → 1 个 direct_correction entry + N 个 propagation entries
- 邻近度 < 阈值 → 不传播
- 跨行业：FMCG 的纠正 → Finance 获得小幅度 propagation
- 跨行业：弱映射 confidence=0.50 → 迁移幅度更小

**文件量：** ~120 行

**Phase 3 验证标准：**
1. 用 20 条手工构造的 signal 跑聚类 → 产出 ≥ 3 个 hypothesis
2. 覆盖 5 种假设类型（keyword_adjustment / indicator_weight / indicator_combination / template_routing / preference_chart）
3. hypothesis YAML 通过 Pydantic schema 校验
4. `pytest tests/unit/test_evolution_analyze.py -v` 全绿

**Phase 3 总文件量：** ~480 行

---

## Phase 4: 验证与应用（V4-P4 + V4-P5）

**目标：** 假设 → hold-out 验证 → 补丁文件 → 知识库更新的完整闭环。

### 4.1 回测验证

**实现 `learn/validate/validator.py`**
- `validate_hypothesis(hypothesis, all_queries) → ValidationResult`
- 75/25 hold-out 分离
- 按假设类型选择通过标准（5.1 节 Step 2）
- 退化检查（任意 query 退化 → 降级）
- 产出 pass_rate + validated_confidence

**实现 `learn/validate/combo_validator.py`**
- `validate_batch(hypotheses, all_queries) → BatchValidationResult`
- 批量假设组合回测
- 退化 → 二分排查

**单元测试：**
- 假设在 hold-out 集 100% 通过 → pass_rate = 1.0
- 1 条退化 → 强制降级
- 批量 2 条无冲突 → 组合通过
- 批量 2 条交互退化 → 二分定位到冲突对

**文件量：** ~180 行 + ~80 行

### 4.2 补丁写入与知识库重建

**实现 `learn/apply/applier.py`**
- `apply_hypothesis(hypothesis) → PatchResult`
- 生成 `.patch` 文件（YAML 格式）
- 写入 `knowledge/_patches/`
- Schema 校验：patch 只修改 target 声明的字段，不允许越权

**实现 `learn/apply/patch_builder.py`**
- `rebuild_active(canonical_dir, patches_dir, active_dir) → None`
- 从 `_canonical/` + 所有 active patches → 重建 `_active/`
- 冲突处理：patch_B 修改的指标在 patch_A 的 4 周内被修改过 → 合并 delta（取平均）
- 废弃 patch 自动排除

**单元测试：**
- 单 patch → _active/ 包含 canonical + patch 变更
- 双 patch 修改同一指标 → delta 合并
- 废弃 patch → 不参与重建
- Schema 校验失败 → patch 被拒绝

**文件量：** ~100 行 + ~100 行

### 4.3 权重爬坡

**实现 `learn/apply/weight_climber.py`**
- `evaluate_climb(hypothesis, counters, weeks) → ClimbResult`
- 无退化 + 有接受 → 权重 +0.15
- 无数据 → 保持
- 退化 → 冻结
- 连续 3 周冻结 → 衰减
- 连续 8 周冻结 → 废弃
- 达到 validated_confidence → 标记 mature

**单元测试：**
- 3 周无退化 → 权重从 0.30 爬到 0.75
- 第 2 周退化 → 冻结
- 连续 3 周冻结 → 衰减
- 连续 8 周冻结 → 废弃

**文件量：** ~100 行

**Phase 4 验证标准：**
1. 构造 3 条 hypothesis → 全链路：验证 → 应用 → 检查 _active/ 输出 → 爬坡模拟
2. batch 应用 + 组合验证通过
3. `pytest tests/unit/test_evolution_validate.py tests/unit/test_evolution_apply.py tests/integration/test_evolution_closed_loop.py -v` 全绿

**Phase 4 总文件量：** ~560 行

---

## Phase 5: 模板自主进化（V4-P6 + V4-P7）

**目标：** 模板内容自动调整 + 新模板草稿自动生成。

### 5.1 模板偏离监控

**实现 `learn/analyze/template_deviation.py`**
- `compute_deviation(template, signals, weeks) → DeviationReport`
- 指标层面：被接受次数、被替换次数、被跳过次数、被补充次数
- 步骤层面：执行率、跳过率、被追加次数
- 触发条件检测

**单元测试：**
- 指标被跳过 55% → 触发降级建议
- 新指标被补充 35% → 触发加入建议
- 步骤跳过 60% → 触发 optional: true

**文件量：** ~120 行

### 5.2 模板内容原子调整

**实现 `learn/apply/template_updater.py`**
- `compute_adjustment(deviation_report) → TemplateAdjustment | None`
- 每次仅产出一条调整（优先级排序）
- 调整类型：add_indicator / demote_indicator / promote_indicator / toggle_optional / add_optional_step
- 调整后 4 周冷却期

**单元测试：**
- 优先级：补充 > 降级 > 步骤降级 > 新增步骤 > 升级 > 废弃
- 冷却期内不产出新调整

**文件量：** ~80 行

### 5.3 模板草稿生成

**实现 `learn/analyze/template_discovery.py`**
- `discover_templates(extension_signals, existing_templates) → list[DraftTemplate]`
- 四重门检查（频次 + 跨 session + 无现有匹配 + 复杂度）
- 自动提取 indicators / steps / applicability

**单元测试：**
- 路径满足四重门 → 产出草稿
- 路径匹配现有模板 applicability → 不产出
- 路径复杂度 < 3 → 不产出

**文件量：** ~100 行

### 5.4 草稿生命周期

**实现 `learn/apply/draft_manager.py`**
- `evaluate_draft(draft, usage_stats) → DraftStatus`
- 被接受 → 权重 +0.10
- 被忽略 → 权重不变
- 被纠正 → 权重 -0.05
- 权重 >= 0.60 → 晋升
- 8 周 < 0.30 → 废弃
- 12 周 → 自动清理

**文件量：** ~80 行

**Phase 5 验证标准：**
1. 模拟模板偏离 → 产出原子调整 → 应用 → 模板版本号 +1
2. 模拟 extension 信号 → 产出草稿模板 → 模拟 5 次接受 → 晋升为正式
3. `pytest tests/unit/test_evolution_template.py tests/integration/test_evolution_template_lifecycle.py -v` 全绿

**Phase 5 总文件量：** ~380 行

---

## Phase 6: 监控与异常检测（V4-P8）

**目标：** 48h 快速窗口 + 周级健康趋势 + 异常信号检测。

### 6.1 健康度量

**实现 `learn/monitor/health_metrics.py`**
- `compute_48h_metrics(scenario, counters) → WindowMetrics`
- `compute_weekly_report(counters) → WeeklyReport`
- 信号有效率、强化率、反事实命中率、L3 率、草稿晋升率、权重冻结率

**文件量：** ~100 行

### 6.2 异常检测

**实现 `learn/monitor/anomaly_detector.py`**
- `check_single_user_dominance(signals) → bool`
- `check_burst(signals, window_hours=24) → bool`
- `check_degradation(baseline, current, thresholds) → DegradationResult`

**单元测试：**
- 同用户占比 60% → 告警
- 24h 内 15 条同方向信号 → 突发告警
- 48h 内样本量 < 10 → 不触发退化判定
- 无数据 case → stable_insufficient_data

**文件量：** ~80 行

**Phase 6 验证标准：**
1. 模拟 48h 窗口数据 → 各种退化场景判定正确
2. 模拟单用户主导 → 正确告警
3. `pytest tests/unit/test_evolution_monitor.py -v` 全绿

**Phase 6 总文件量：** ~180 行

---

## Phase 7: 主动学习（V4-P9，可选）

**目标：** feature flag 控制的主动反问，默认关闭。

### 7.1 intent_parser 分支

**修改 `scripts/intent_parser.py`**
- 增加 `parse_intent` 的主动学习分支（见 V4 文档 九节伪代码）
- 受 `config.evolution.active_learning.enabled` 控制
- `ClarificationRequest` 返回类型
- `session_clarifications` 计数器（MAX_CLARIFICATIONS_PER_SESSION）

**单元测试：**
- enabled=false → 行为不变
- enabled=true + gap < 阈值 → 返回 ClarificationRequest
- enabled=true + gap >= 阈值 → 返回正常结果
- session 内反问 >= 3 次 → 不再反问

**文件量：** ~60 行

---

## 总代码量估算

| Phase | 新增文件 | 修改文件 | 代码行数 | 测试行数 |
|-------|---------|---------|---------|---------|
| P1: 数据模型 | 2 | 0 | ~250 行 | ~100 行 |
| P2: 信号引擎 | 4 | 2 | ~520 行 | ~300 行 |
| P3: 聚类分析 | 4 | 0 | ~480 行 | ~250 行 |
| P4: 验证应用 | 2 | 0 | ~560 行 | ~300 行 |
| P5: 模板进化 | 4 | 0 | ~380 行 | ~200 行 |
| P6: 监控 | 2 | 0 | ~180 行 | ~150 行 |
| P7: 主动学习 | 0 | 1 | ~60 行 | ~50 行 |
| **总计** | **18** | **3** | **~2430 行** | **~1350 行** |

---

## 文件创建顺序与依赖

```
Phase 1 ──────────────────────────────────────────────
  learn/ingest/models.py
  tests/fixtures/evolution_fixtures.py
  │
Phase 2 ──────────────────────────────────────────────
  learn/ingest/signal_detector.py          (from models)
  learn/ingest/reinforcement_detector.py   (from models)
  learn/ingest/counterfactual_check.py     (from models)
  learn/ingest/preference_detector.py      (from models)
  learn/ingest/counter_writer.py           (from models)
  learn/ingest/session_processor.py        (from all detectors)
  修改 learn/hooks/session-summary
  修改 learn/hooks/analyze-observe
  │
Phase 3 ──────────────────────────────────────────────
  learn/analyze/proximity_builder.py       (独立)
  learn/analyze/confidence.py              (独立)
  learn/analyze/signal_analyzer.py         (from signals + confidence)
  learn/analyze/propagation.py             (from proximity + mappings)
  │
Phase 4 ──────────────────────────────────────────────
  learn/validate/validator.py              (from hypotheses)
  learn/validate/combo_validator.py        (from validator)
  learn/apply/applier.py                   (from validated hypotheses)
  learn/apply/patch_builder.py             (from patches)
  learn/apply/weight_climber.py            (from counters)
  │
Phase 5 ──────────────────────────────────────────────
  learn/analyze/template_deviation.py      (from signals)
  learn/apply/template_updater.py          (from deviation)
  learn/analyze/template_discovery.py      (from extension signals)
  learn/apply/draft_manager.py             (from drafts)
  │
Phase 6 ──────────────────────────────────────────────
  learn/monitor/health_metrics.py          (from counters)
  learn/monitor/anomaly_detector.py        (from signals + counters)
  │
Phase 7 ──────────────────────────────────────────────
  修改 scripts/intent_parser.py
```

---

## 每日里程碑

| 天 | Phase | 内容 | 验证 |
|----|-------|------|------|
| Day 1 | P1 | 数据模型 + 测试夹具 + 纯函数桩 | mypy strict pass |
| Day 2 | P2 | signal_detector + reinforcement_detector | 单元测试 6 条 case pass |
| Day 3 | P2 | counterfactual + preference + counter_writer | 单元测试 pass |
| Day 4 | P2 | session_processor + hook 重写 | 集成测试端到端 pass |
| Day 5 | P3 | proximity_builder + confidence | 单元测试 pass |
| Day 6 | P3 | signal_analyzer + propagation | 聚类产出 hypothesis |
| Day 7 | P4 | validator + combo_validator | hold-out 验证 pass |
| Day 8 | P4 | applier + patch_builder | _active/ 重建 pass |
| Day 9 | P4 | weight_climber | 爬坡全状态 pass |
| Day 10 | P5 | template_deviation + template_updater | 原子调整 pass |
| Day 11 | P5 | template_discovery + draft_manager | 草稿生命周期 pass |
| Day 12 | P6 | health_metrics + anomaly_detector | 监控全场景 pass |
| Day 13 | P7 | intent_parser 主动学习分支 | feature flag 测试 pass |
| Day 14 | — | 全链路回测 + 文档更新 | ✅ 189 tests 全绿 |

---

## 执行结果

**完成日期:** 2026-05-02
**总测试数:** 189 (全部通过)
**总代码量:** ~2,500 行（19 个源文件）+ ~1,750 行（9 个测试文件）

### 实际偏差

| 偏差 | 说明 |
|------|------|
| Phase 3 提前实现 | P3 作为 P2→P4 的自然桥接，在 Day 5-6 完成 |
| Phase 5 拆分 | 模板进化拆为 2 天（Day 10 + Day 11） |
| supplement 触发 bug | `template_deviation.py` 中 add 触发检查嵌套在 `if total > 0:` 内，导致纯补充指标无法触发 |
| weight_climber degradation | `_has_degradation` 在 `l3_fallbacks > 0` 时返回 True，需构造干净的 counter 测试 |
| 主动学习集成点 | 注入在 routing merge 之后、L2 search 之前，基于 intent 关键词评分计算 top-2 gap |

### 新增文件清单

```
learn/ingest/
├── models.py                    # 所有 frozen dataclass
├── signal_detector.py           # classify_query_pair + detect_extension
├── reinforcement_detector.py    # detect_reinforcement
├── counterfactual_check.py      # check_counterfactual
├── preference_detector.py       # detect_preference
├── counter_writer.py            # 原子 JSONL append + counter JSON
└── session_processor.py         # process_session 全管线

learn/analyze/
├── confidence.py                # 四维置信度公式
├── proximity_builder.py         # 共现矩阵构建
├── signal_analyzer.py           # 聚类 + 假设生成
├── propagation.py               # 语义 + 跨行业传播
├── template_deviation.py        # 模板偏离监控
└── template_discovery.py        # 四重门草稿发现

learn/validate/
├── validator.py                 # 75/25 hold-out 验证
└── combo_validator.py           # 批量冲突检测

learn/apply/
├── applier.py                   # 假设 → 补丁
├── patch_builder.py             # canonical/patches 双栈
├── weight_climber.py            # 权重爬坡状态机
├── template_updater.py          # 原子调整 + 冷却期
└── draft_manager.py             # 草稿生命周期管理

learn/monitor/
├── health_metrics.py            # 48h + 周报
└── anomaly_detector.py          # 用户主导/突发/退化

tests/
├── unit/test_evolution_signals.py         # 30 tests
├── unit/test_evolution_analyze.py         # 41 tests
├── unit/test_evolution_validate.py        # 10 tests
├── unit/test_evolution_apply.py           # 16 tests
├── unit/test_evolution_template.py        # 19 tests
├── unit/test_evolution_monitor.py         # 27 tests
├── unit/test_evolution_active_learning.py # 10 tests
├── integration/test_evolution_pipeline.py          # 10 tests
├── integration/test_evolution_closed_loop.py       # 4 tests
├── integration/test_evolution_template_lifecycle.py # 12 tests
└── integration/test_evolution_full_loop.py          # 10 tests

修改:
├── scripts/intent_parser.py     # +55 行主动学习分支
├── hooks/analyze-observe        # → v2 Observation 格式
├── hooks/session-summary        # → Python entry
└── learn/data/config.yaml       # (已就绪，未修改)
```

---

*本文档于 2026-05-02 创建，同日完成全部实施。*
