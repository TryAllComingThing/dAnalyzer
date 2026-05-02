# dAnalyzer 自进化系统 v4

> 版本: 4.0 — 2026-05-02
> 前身: v3.1 (纠正检测 + 模板三层进化 + 人工确认 + 回滚)
> v4 核心变革: 三信号学习 + 渐进式置信 + 语义邻近泛化 + 全自主闭环（无人工审核、无回滚）

---

## 零、v3 → v4 范式转换

| 维度 | v3 | v4 |
|------|-----|-----|
| 学习信号 | 仅纠正（惩罚驱动） | 四类信号：纠正 + 强化 + 反事实 + 偏好 |
| 知识表示 | 点估计（A 替换为 B） | 权重分布（A 权重降 20%，B 升 20%） |
| 泛化能力 | 无（同纠正需出现 >= 3 次） | 行业内语义邻近 + 跨行业种子映射传播 |
| 安全模型 | 回滚（恢复性安全） | 渐进权重（预防性安全） |
| 人工角色 | 审核假设 + 编写模板内容 | 零介入（仅监控退化趋势） |
| 模板创建 | 人工编写 | 系统自动生成草稿 → 使用中自证 |
| 知识存储 | 直接覆写文件 | 双层 + 补丁栈（可追溯、可合并） |
| 变更粒度 | 一次性替换 | 渐进式爬坡（0.3 → validated_confidence） |
| 跨行业 | 不支持 | 符号级种子映射 + 小幅度迁移传播 |
| 偏好学习 | 不支持 | 图表/报告多模态偏好信号 |
| 主动学习 | 不支持 | v4.5 feature flag（默认关闭） |

**核心哲学：不做大变更，不做回滚。每个变更足够小，小到不需要回滚。用时间换安全。**

---

## 一、设计原则

1. **三信号驱动。** 纠正告诉你哪里错了，强化告诉你哪里对了，反事实告诉你差一点就对了。三者缺一不可。

2. **渐进式生效。** 所有自动变更从低权重起步，随时间积累证明自己。权重爬坡替代回滚——错的变更永远到不了高权重。

3. **语义泛化。** 一次纠正不应只影响一对映射。利用指标共现结构传播学习信号，实现"举一反三"。

4. **全自主闭环。** 从信号检测到假设生成到验证到应用到权重爬坡，全链路无人介入。系统对自身知识库的修改负全责。

5. **预防性安全。** 安全不靠事后回滚，靠事前的小步慢走 + 交叉验证 + 权重冻结。

6. **行业通用内核。** 学习逻辑跨行业不变。行业知识是学习的结果，不是学习的规则。

---

## 二、三信号体系

### 2.1 信号总览

```
用户行为 ──→ 系统响应 ──→ 信号分类
  │                          │
  │  用户接受（无修改）       ├──→ reinforcement   强化信号（系统对了）
  │  用户纠正（替换指标）     ├──→ correction      纠正信号（系统错了）
  │  用户补充（追加指标）     ├──→ supplement      补充信号（系统不完整）
  │  用户调整（修改粒度）     ├──→ refinement      调整信号（系统粒度不当）
  │  用户扩展（追加步骤）     ├──→ extension       扩展信号（分析路径不完整）
  │  系统兜底（L3 未匹配）    ├──→ l3_fallback     盲区信号（知识缺失）
  │  系统校验失败（L1 不存在）├──→ l1_miss         幻觉信号（LLM 转写错误）
  │  候选命中但未推荐          └──→ counterfactual  反事实信号（排序错误）
```

### 2.2 强化信号（v4 新增）

成功的查询包含关键信息——它告诉系统"你做对了什么"。v3 丢弃了这些信息，v4 捕获它们。

```json
// reinforcements.jsonl
{
  "ts": "2026-05-02T10:30:00Z",
  "session": "abc123",
  "industry": "fmcg",
  "scenario": "category_analysis",
  "indicators_accepted": ["gross_margin_rate", "sell_through_rate", "inventory_turnover"],
  "template_accepted": "category_health_diagnostic",
  "skill_chain_accepted": ["data-query", "data-analysis", "visual"],
  "source": "l1_exact",
  "user_anon_id": "u_7a3f"
}
```

**作用：**
- 巩固正确的指标-场景映射（被接受的组合降低被错误调整的风险）
- 为模板路由提供正向证据（用户选择了推荐模板 → 路由正确）
- 建立 baseline 行为画像（什么才是"正常"的成功查询）

**不捕获的情况：**
- 用户未做任何交互（无法区分"满意"和"离开"）
- 单一 turn 的查询（没有后续交互无法判断接受与否）

判定逻辑：同一 session 内，用户在收到结果后未产生 correction/supplement/refinement 信号，而是发起新的 unrelated 查询或结束 session → 前一轮结果标记为 accepted。

### 2.3 反事实信号（v4 新增）

检索过程返回 top-K 个指标给用户，但系统内部可能计算了 20 个候选项。当用户纠正后的指标恰好出现在候选项中（但不在前 K 个返回结果中），这是一个**强信号**——系统不是不知道正确答案，而是没把它排到前面。

```json
// counterfactuals.jsonl
{
  "ts": "2026-05-02T10:23:00Z",
  "session": "abc123",
  "scenario": "category_analysis",
  "indicators_retrieved": ["sales_amount", "order_count", "sku_count"],
  "indicators_candidates": [
    {"id": "gross_margin_rate", "score": 0.62, "rank": 4},
    {"id": "sell_through_rate", "score": 0.58, "rank": 5},
    {"id": "sales_amount", "score": 0.95, "rank": 1},
    {"id": "order_count", "score": 0.88, "rank": 2},
    {"id": "sku_count", "score": 0.81, "rank": 3}
  ],
  "user_selected": ["gross_margin_rate", "sell_through_rate"],
  "candidate_hit": true,
  "hit_ranks": [4, 5],
  "detection_method": "candidate_intersection"
}
```

**关键区分：**

| 场景 | 信号类型 | 进化含义 |
|------|---------|---------|
| 用户纠正的指标在 candidates 中（rank > K） | counterfactual | 排序权重错误，需调权 |
| 用户纠正的指标不在 candidates 中 | correction | 术语映射缺失，需补充关键词/别名 |
| candidates 为空（L3 兜底） | l3_fallback | 知识盲区，需新增 intent/indicator |

这个区分解决了 v3 的核心模糊性——同一个纠正行为，现在可以精准定位到"排序问题"还是"知识缺失问题"。

### 2.4 纠正信号（v3 延续，增强）

继承 v3 的 correction / supplement / refinement / extension 分类逻辑（含部分重叠纠正 + 否定词检测），增强点：

- 每条信号附加 `user_anon_id`（匿名化），用于单用户信号占比检测
- 关联 counterfactual 检测结果（`candidate_hit: true/false`）

### 2.5 信号衰减（v4 新增）

同一用户对同一 scenario 的重复纠正，信号权重递减：

```
signal_weight = 1.0 / (1 + log2(同一用户对该 scenario 的纠正次数))

例:
  第 1 次纠正: weight = 1.00
  第 2 次纠正: weight = 0.50
  第 3 次纠正: weight = 0.39
  第 5 次纠正: weight = 0.30
```

衰减后的信号在聚类时贡献降低——高频次仍然计入 frequency，但 consistency_score 计算中使用衰减权重。这防止单一激进用户主导学习方向，不引入用户/团队分层。

### 2.6 多模态偏好信号（v4 新增）

系统推荐图表类型和报告格式。当用户主动更换推荐的多模态选择时，系统学习这种偏好。

```json
// preferences.jsonl
{
  "ts": "2026-05-02T10:35:00Z",
  "session": "abc123",
  "industry": "fmcg",
  "scenario": "category_analysis",
  "preference_type": "chart",
  "recommended": "heatmap",
  "user_selected": "line_chart",
  "template": "category_health_diagnostic",
  "detection_method": "ui_selection_diff"
}
```

**两大多模态偏好维度：**

| 偏好维度 | 检测方式 | 进化对象 |
|---------|---------|---------|
| 图表类型 | 推荐 chart_type vs 用户实际选择 | 模板 steps 中 visual 的 types 权重调整 |
| 报告格式 | 推荐 report_format vs 用户实际导出格式 | 模板 steps 中 report 的 format 权重调整 |

**判定逻辑：**
- 系统推荐了图表/报告类型 → 用户手动更换 → preference 信号
- 用户直接接受推荐 → reinforcement 信号中附加 `preference_accepted: true`
- 用户未选择（在推荐界面跳过） → 不捕获

**聚类与假设：**
- 同一 scenario 下同一 preference 方向出现 >= 3 次 → 产出 `preference_chart` 或 `preference_report` 假设
- 假设类型走 `progressive_apply`（>= 0.70 即可自动应用，初始权重 0.30）
- 进化对象：模板 visual / report 步骤的 types / format 权重

**示例：**
```
品类分析场景下:
  heatmap 被推荐 12 次，被接受 4 次，被替换为 line_chart 5 次
  → 假设: 品类分析场景用户偏好折线图 > 热力图
  → 动作: 模板 visual 步骤 types 中 line_chart 权重 +0.15, heatmap 权重 -0.10
```

代码量约 80 行（`ingest/preference_detector.py` + 聚类逻辑扩展），合并到 V4-P1。

---

## 三、语义邻近传播

### 3.1 动机

v3 的根本局限：在 scenario A 下学了 5 次 `sales_amount → gross_margin_rate`，在 scenario B 下需要重新学 5 次才能产生同样的纠正。人类不会这样学习——一次纠正会更新整个相关概念网络。

v4 的解决方案：当纠正发生时，不仅调整被纠正的指标对，还对**语义邻近指标**施加小幅权重调整。

### 3.2 邻近度计算

**Phase 1：基于共现矩阵（无需 ML 基础设施）**

```
1. 扫描所有模板 + 所有 scenario 的指标配置
2. 构建指标共现矩阵 C[i][j] = 指标 i 和 j 在同一模板/scenario 中出现的次数
3. 归一化为邻近度: proximity(i, j) = C[i][j] / max(C[i][:])
```

```
共现矩阵示例（FMCG 模板）:

                    gross_margin  sell_through  inventory_turn  sales_amount  order_count
gross_margin           -             4              3              5            3
sell_through           4             -              4              3            2
inventory_turn         3             4              -              2            2
sales_amount           5             3              2              -            5
order_count            3             2              2              5            -
```

### 3.3 传播规则

```python
def propagate_correction(source_indicator, target_indicator, scenario, proximity_matrix):
    """
    source_indicator: 被用户否定的指标 (e.g., sales_amount)
    target_indicator: 用户期望的指标 (e.g., gross_margin_rate)
    """
    adjustments = []

    # 直接映射：被否定指标 → 期望指标 (全量调整)
    adjustments.append({
        "from": source_indicator,
        "to": target_indicator,
        "scenario": scenario,
        "weight_delta": -0.20,           # 降权
        "target_weight_delta": +0.20,    # 升权
        "source": "direct_correction"
    })

    # 邻近传播：与被否定指标高度共现的指标也获得微调
    neighbors = proximity_matrix.get_neighbors(source_indicator, threshold=0.6)

    for neighbor in neighbors:
        proximity = proximity_matrix[source_indicator][neighbor]
        # 邻近指标也向 target_indicator 方向微调
        adjustments.append({
            "from": neighbor,
            "to": target_indicator,
            "scenario": scenario,
            "weight_delta": -0.05 * proximity,       # 小幅降权
            "target_weight_delta": +0.05 * proximity, # 小幅升权
            "source": "semantic_propagation"
        })

    return adjustments
```

**效果示例：**

```
纠正: sales_amount → gross_margin_rate (品类分析场景)

直接影响:
  sales_amount 在品类分析下权重 -0.20
  gross_margin_rate 在品类分析下权重 +0.20

语义传播（邻近度 >= 0.6）:
  order_count (邻近度 0.83) → 权重 -0.04, gross_margin_rate +0.04
  sku_count (邻近度 0.67) → 权重 -0.03, gross_margin_rate +0.03

结果: 一次纠正同时影响了 3 个相关指标的权重，下次类似查询时，
     利润类指标整体排名上升，规模类指标整体排名下降。
```

### 3.4 安全边界

- 传播范围限制：邻近度阈值 >= 0.6，最多传播到 5 个邻近指标
- 传播幅度限制：邻近调整幅度 = 直接调整幅度 × 邻近度 × 0.25（系数可配置）
- 仅传播降权（降低错误指标相关项的权重），不传播升权（避免过度推荐）
- 传播仅作用于同一 industry 内（跨行业传播见 3.5）

### 3.5 跨行业迁移传播（v4 新增）

行业内邻近传播解决"举一反三"。跨行业迁移解决"A 行业学到的，B 行业也能受益"。

**思路：行业间指标映射表（种子映射）+ 小幅度传播 + 目标行业数据主导。**

#### 3.5.1 种子映射

人工定义跨行业指标语义映射（一次性投入，30-50 对），存储在 `knowledge/_base/cross_industry_mappings.yaml`：

```yaml
mappings:
  fmcg_to_finance:
    - {from: gross_margin_rate,       to: net_interest_margin,       confidence: 0.75}
    - {from: net_margin_rate,          to: return_on_assets,           confidence: 0.70}
    - {from: sell_through_rate,        to: loan_utilization_rate,      confidence: 0.60}
    - {from: inventory_turnover,       to: deposit_turnover_rate,      confidence: 0.55}
    - {from: sales_amount,             to: loan_balance,               confidence: 0.65}
    # ... 30-50 对

  fmcg_to_logistics:
    - {from: sales_amount,             to: parcel_volume,              confidence: 0.70}
    - {from: order_count,              to: delivery_order_count,       confidence: 0.85}
    # ...
```

`confidence` 表示映射可靠度：>= 0.80 强映射（同名指标、财务指标间），0.50-0.79 中等映射（需目标行业数据验证）。

#### 3.5.2 迁移传播规则

```
1. FMCG 行业学到: 品类分析 + gross_margin_rate 权重 +0.20（5 次纠正确认）

2. 查映射表: gross_margin_rate → net_interest_margin (confidence=0.75)

3. Finance 行业: 产品分析 + net_interest_margin 权重微调
   迁移幅度 = 源调整幅度 × cross_industry_factor × mapping_confidence
            = 0.20 × 0.25 × 0.75 = 0.0375
   → 四舍五入: +0.04

4. 跨行业迁移永远走 progressive_apply（初始权重 = 迁移幅度，max = 源调整幅度 × 0.5）
   即使源假设是 full_apply(>= 0.90)

5. 目标行业验证:
   - Finance 行业自己的强化信号支持 → 权重爬坡加速（+0.20/周，高于常规的 0.15）
   - Finance 行业出现反向纠正 → 权重快速衰减 + 映射 confidence 降低 0.20
   - Finance 行业无数据 → 权重保持，不爬坡（等待目标行业数据）
```

**关键约束：**

| 约束 | 值 | 理由 |
|------|-----|------|
| 跨行业传播系数 | 0.25 | 目标行业数据永远占主导 |
| 跨行业额外折扣 | × mapping_confidence | 弱映射自动获得更小幅度 |
| 权重上限 | 源幅度的 50% | 跨行业迁移不能超过行业内学习的效果 |
| 反向纠正衰减 | -0.20/次 | 快速纠正错误的跨行业迁移 |
| 仅 progressive | 永不走 full_apply | 跨行业变更必须在目标行业证明自己 |

代码量约 100 行（`analyze/propagation.py` 增加跨行业分支），合并到 V4-P2。

---

## 四、渐进式置信框架

### 4.1 核心理念

v3 的问题是变更是一次性的——apply 之后系统状态突变，错了需要回滚。v4 的答案是：**所有变更从低权重起步，随时间证明自己。**

```
变更生命周期:

  hypothesis 生成 → 验证 → 应用(权重=0.30) → 周级评估 → 权重爬坡/冻结
                                              │
                                              ├─ 无退化 + 被接受 → 权重 += 0.15
                                              ├─ 无数据 → 权重保持
                                              └─ 退化 → 权重冻结，不再爬坡
```

一个错误的变更永远卡在 0.30 权重，被正确的高权重推荐压制。不需要回滚。

### 4.2 置信度计算

继承 v3 的三维公式，调整为四维（新增邻近距离维度）：

```
confidence = α × frequency_score + β × consistency_score + γ × diversity_score + δ × proximity_bonus

权重:  α = 0.35  频次得分
       β = 0.30  一致性得分
       γ = 0.20  跨 session 多样性得分
       δ = 0.15  反事实邻近加分（v4 新增）
```

**反事实邻近加分**（δ = 0.15）：

```
对 counterfactual 信号（用户纠正的指标在 candidates 中）:
  proximity_bonus = min(hit_count / 3, 1.0) × 0.30
  理由: 候选命中说明系统掌握正确答案，只需排序调整 → 置信度应略高

对 correction 信号（用户纠正的指标不在 candidates 中）:
  proximity_bonus = 0
  理由: 完全的知识缺失 → 需要更多证据
```

其他维度计算同 v3（见 v3 文档 4.5 节），仅权重调整。

### 4.3 自主应用门槛

```
validated_confidence >= 0.90  →  full_apply      (初始权重 = validated_confidence，单步直接生效)
validated_confidence >= 0.70  →  progressive_apply (初始权重 = 0.30，周级爬坡至 validated_confidence)
validated_confidence <  0.70  →  discarded        (记录原因，不应用)
```

无人工审核队列。0.70-0.90 的假设自动进入渐进式应用，不需要人看。

**validated_confidence 计算公式不变：** `validated_confidence = confidence × pass_rate`（含 hold-out 分离和退化降级，见 v3 文档 5.1-5.2 节）。

### 4.4 权重爬坡算法

```
每周一 9am（与假设生成同步）:

对每个处于 progressive_apply 状态的 hypothesis:
  1. 检查本周该 hypothesis 涉及的 scenario 的健康计数器:
     - L3 率无恶化（相对基线 +0pp 以内）
     - 纠正率无恶化（相对基线 +3pp 以内）
     - 涉及的指标被接受次数 > 0（有正向强化信号）
  2. 条件满足:
     - current_weight += 0.15
     - 若 current_weight >= validated_confidence → 标记成熟，固定权重
  3. 条件不满足:
     - current_weight 冻结（本周不增加）
     - 若连续 3 周冻结 → current_weight 衰减 0.05（缓慢遗忘）
     - 若连续 8 周冻结 → 废弃（weight 降为 0，hypothesis 标记为 defunct）
  4. 爬坡期间 hypothesis 状态 = progressive
```

**关键：爬坡依据的是系统真实运行数据（健康计数器），不是重新验证。变更在生产中证明自己。**

### 4.5 权重表示

v3 中的假设应用是替换值（`default_indicators: [A, B, C]` → `default_indicators: [D, B, C]`）。v4 改为权重表示：

```yaml
# intent-routing.yaml 中的指标（v4 格式）
intents:
  category_overview:
    default_indicators:
      - id: gross_margin_rate
        weight: 0.92          # 高权重（被强化信号巩固）
        source: evolution
        hypothesis: hyp-20260502-001
      - id: sell_through_rate
        weight: 0.88
        source: evolution
        hypothesis: hyp-20260502-001
      - id: sales_amount
        weight: 0.65          # 降权（被纠正信号削弱）
        source: canonical     # 人工设定基线
      - id: order_count
        weight: 0.60
        source: canonical
      - id: sku_count
        weight: 0.55
        source: canonical
```

运行时按权重降序排列推荐。高权重的进化指标自然排在前面，被削弱的人工基线指标自然靠后。**不删除任何指标，不绝对替换——保留多模态，让数据说话。**

权重爬坡期间，系统对该指标的推荐置信度也反映在 UI 中：

```
检索结果:
  1. gross_margin_rate  (推荐度: ★★★★★)
  2. sell_through_rate  (推荐度: ★★★★★)
  3. sales_amount       (推荐度: ★★★☆☆)
  4. order_count        (推荐度: ★★★☆☆)
```

---

## 五、自主模板进化

### 5.1 模板三线全自主化

v3 的三条进化线（路由对齐 / 内容进化 / 模板沉淀）全部保留，但移除人工确认环节。

| 进化线 | v3 方式 | v4 方式 |
|--------|---------|---------|
| 路由对齐 | 自动权重 ±1 | 自动权重调整（同 v3），增加强化信号巩固 |
| 内容进化 | 人工确认后更新 | 自动渐进式调整（每次只改一个指标/步骤） |
| 模板沉淀 | 人工确认 + 人工编写 | 自动生成草稿 → 使用中自证 → 自动晋升/淘汰 |

### 5.2 第一线：模板路由对齐（全自动，同 v3）

逻辑与 v3 相同——correction 携带 template_before / template_after → 调整路由权重。增强点：

- 强化信号参与：用户接受模板推荐 → 该模板的 trigger_query 权重 +0.05
- 权重爬坡：路由权重调整也走渐进式（初始 +0.10，后续每次巩固 +0.05，上限 0.95）

### 5.3 第二线：模板内容自主进化

v3 中这项需要人工确认。v4 改为**原子化自动调整**——每次只改一个东西，且改动足够小。

**触发条件（同 v3）：**
- 指标偏离（替换/跳过/补充）>= 40% 使用次数
- 步骤跳过 >= 50% 使用次数
- 新指标补充 >= 30% 使用次数

**自主调整规则（每次仅执行一条）：**

```
优先级排序（取偏离度最高的 1 项执行）:

1. 补充指标: 不在模板中、被补充 >= 30% 使用次数
   动作: 加入 secondary 列表，weight = 0.30（渐进起步）
   示例: net_margin_rate 不在模板中，8次补充 → 加入 secondary，weight = 0.30

2. 降级指标: 在 primary 中、被跳过 >= 50% 使用次数
   动作: 从 primary 移至 secondary，保留 weight
   示例: inventory_turnover 跳过 55% → 降为 secondary

3. 降级步骤: 在核心步骤中、跳过率 >= 60%
   动作: 标记为 optional: true
   示例: model(归因) 跳过 60% → optional: true

4. 新增可选步骤: 不在模板中、被追加 >= 30% 使用次数
   动作: 加入 steps 列表，标记 optional: true，weight = 0.25
   示例: 渠道拆解被追加 35% → 新增可选步骤

5. 升级指标: 在 secondary 中、被补充进用户选择 >= 4 周且未被纠正
   动作: 移至 primary，weight += 0.10

6. 废弃指标: 在模板中、连续 8 周未被任何用户接受
   动作: weight 衰减，连续 12 周 → 移除
```

**安全机制：**
- 每次仅执行 1 条调整（不是批量修改）
- 调整后进入 4 周冷却期（同一模板不连续调整）
- 调整记录在模板 meta 中（完整审计）
- 所有调整走权重爬坡（初始低权重，时间证明）

### 5.4 第三线：模板自主沉淀

v3 中需要人工确认 + 人工编写模板内容。v4 改为**草稿-自证-晋升**机制。

**沉淀条件（四重门，同 v3）：**
1. 相同路径出现 >= 5 次
2. 跨越 >= 3 个不同 session
3. 无法匹配任何现有模板
4. 路径复杂度 >= 3 个步骤

**自主沉淀流程：**

```
1. 条件满足 → signal_analyzer 自动生成草稿模板:

   草稿模板特征:
   - id: auto_{date}_{seq}           # 系统自动编号
   - status: draft                   # 草稿状态
   - version: 0                      # 草稿版本号从 0 开始
   - routing_weight: 0.25            # 低初始权重——排在人工模板之后
   - indicators:                     # 从信号中提取的观测指标集
       primary: [观测到的高频指标]
       secondary: [观测到的低频指标]
   - steps:                          # 从信号中提取的观测步骤链
       - skill: data-query
       - ...
   - applicability:                  # 自动推断的适用条件
       intents: [观测到的 intent]
       scenarios: [观测到的 scenario]
   - meta:
       created_by: system
       hypothesis: hyp-xxx
       evidence_signals: [sig-001, ...]

2. 草稿注入路由系统:
   - 参与模板匹配，但权重 0.25（远低于人工模板的 0.85+）
   - 匹配时标注为草稿
   - 用户可见提示: "💡 发现新的分析路径「...」，系统正在验证中"

3. 草稿自证（权重爬坡）:
   - 用户接受草稿推荐 → 权重 +0.10
   - 用户忽略（选了其他模板） → 权重不变
   - 用户纠正（选了另外的模板） → 权重 -0.05
   - 4 周内权重 >= 0.60 → 晋升为正式模板（status: active, version: 1）
   - 8 周内权重 < 0.30 → 自动废弃（status: defunct, 不再参与匹配）
   - 12 周后自动清理废弃模板（归档到 evolution-log）

4. 晋升后的模板:
   - 进入第二线（内容进化）的监控范围
   - 可被后续的偏离监控自动调整
```

**关键：系统自主完成模板的全生命周期——发现 → 草稿 → 验证 → 晋升/废弃 → 内容进化。人零介入。**

### 5.5 intent 自主创建

L3 fallback 聚类产出的 `intent_new` 假设，同样走草稿机制：

```
1. L3 fallback 高频关键词组合 → 生成草稿 intent
2. 草稿 intent 包含:
   - keywords: 从 L3 query 中提取的 N-gram
   - default_indicators: 空（待渐进学习）
   - status: draft
   - routing_weight: 0.20
3. 草稿 intent 参与路由，但优先级最低（L2.5，介于 L2 和 L3 之间）
4. 被命中 + 用户接受 → weight 爬坡
5. weight >= 0.50 → 晋升为正式 intent（L2 级别）
6. 4 周未被命中 → 废弃
```

---

## 六、知识架构

### 6.1 双层知识库

解决 v3 中知识文件"既是真相源又是进化目标"的冲突。

```
knowledge/
├── _canonical/                       # 人工维护的规范版本（只读）
│   ├── intent-routing.yaml           # 基线路由配置
│   ├── industry/                     # 基线行业配置
│   └── template/                     # 人工创建的模板
│
├── _active/                          # 运行时读取（= canonical + patches）
│   ├── intent-routing.yaml           # 自动生成，禁止手动编辑
│   ├── industry/
│   └── template/
│
├── _patches/                         # 进化补丁（每个 hypothesis 一个 patch）
│   ├── hyp-20260502-001.patch
│   ├── hyp-20260509-003.patch
│   └── _index.jsonl                  # patch 索引 + 状态
│
└── _schemas/                         # Schema 定义
    ├── observation_v2.json
    ├── hypothesis_v2.yaml
    ├── template_v2.yaml
    └── intent_routing_v2.yaml
```

**运行时逻辑：**
- 系统启动 → 加载 `_canonical/` + 所有 active patches → 生成 `_active/` → 加载到内存
- 新 patch 应用 → 重建受影响的 `_active/` 文件
- patch 废弃 → 从重建列表中移除 → 重建 `_active/`
- 人工修改 `_canonical/` → 触发全量重建（保留 patches）

**关键：applier 从不修改 `_canonical/` 和 `_active/` 中的文件。它只创建/更新 patch 文件，然后触发重建。这消除了 v3 中"覆盖文件"的事务性风险。**

### 6.2 补丁格式

```yaml
# _patches/hyp-20260502-001.patch
id: hyp-20260502-001
status: progressive              # progressive | mature | frozen | defunct
type: indicator_weight
created: 2026-05-02T09:00:00Z
last_updated: 2026-05-16T09:00:00Z

target:
  layer: industry
  file: fmcg/scenarios/category_analysis.yaml
  path: indicators

operations:
  - op: adjust_weight
    indicator: gross_margin_rate
    delta: +0.20
    current_weight: 0.50          # 爬坡中
    max_weight: 0.85               # validated_confidence
  - op: adjust_weight
    indicator: sales_amount
    delta: -0.20
    current_weight: 0.70
    max_weight: null               # 降权无上限（可降至 0）

propagation:
  - indicator: order_count
    delta: -0.04
    reason: semantic_propagation
  - indicator: sku_count
    delta: -0.03
    reason: semantic_propagation

evidence:
  hypothesis: hyp-20260502-001
  signals: [corr-0042, corr-0058, corr-0091, corr-0103, corr-0112]
  validated_confidence: 0.85

schema_version: 2
```

### 6.3 补丁合并

重建 `_active/` 时，同一文件上的多个 patches 按时间顺序合并：

```
1. 从 _canonical/ 加载基线文件
2. 按 created 时间排序该文件的所有 active patches
3. 依次 apply 每个 patch 的 operations
4. 冲突检测: 如果 patch_B 修改的指标被 patch_A 在 4 周内修改过 → 合并两者 delta（取平均）
5. 输出到 _active/
```

**补丁栈的优势：**
- 不修改 v3 的回滚逻辑，而是让回滚不需要存在——废弃的 patch 直接从重建中移除
- 并发安全：多个 hypothesis 修改同一文件时自动合并
- 可追溯：任何时刻的 `_active/` 状态都可以通过 patches + canonical 精确复现

---

## 七、安全机制

### 7.1 设计哲学：预防性安全

v3 的安全模型是**恢复性**的——错了回滚。v4 的安全模型是**预防性**的——让错误无法产生实质性影响。

| 防护层 | 机制 | 作用 |
|--------|------|------|
| 信号质量 | 用户级衰减 + 最小样本量 | 防止噪声/恶意信号进入假设生成 |
| 假设验证 | hold-out 分离 + 退化检查 | 阻止有害假设进入应用阶段 |
| 渐进生效 | 权重从 0.30 起步，周级爬坡 | 错误变更永远低权重，被正确推荐压制 |
| 原子调整 | 模板每次只改 1 项 + 冷却期 | 防止模板突变 |
| 草稿隔离 | 新模板/新 intent 权重 0.20-0.25 | 未经验证的知识不污染检索结果 |
| 权重冻结 | 连续 3 周退化 → 冻结，8 周 → 废弃 | 错误变更自动消亡 |
| 48h 快监 | auto_apply 后 48h 密集监控 | 捕获即时退化 |
| 组合验证 | 批量应用前交叉回测 | 防止变更交互退化 |
| Schema 校验 | applier 写入前结构校验 | 防止越权修改 |

### 7.2 48h 快速监控（增强）

继承 v3 的 48h 监控机制，增强：

```
1. 最小样本量门槛: 48h 内该 scenario 查询数 < 10 → 仅监控不冻结
   （小样本波动不触发动作，标记 stable_low_confidence）
2. 受影响的"其他用户"监控: 变更涉及的 scenario 中，
   非训练/验证来源的新 session 出现退化 → 权重冻结
3. 单指标粒度: 监控细化到具体受影响的指标，
   而非整个 scenario
```

### 7.3 组合验证

批量 progressive_apply 或 full_apply 前：

```
1. 收集本批次所有待应用假设
2. 在合并 hold-out 集上回测全部假设组合后的系统状态
3. 组合回测通过 → 逐条应用
4. 组合回测退化 → 二分法排查（一次排除一半假设，定位交互退化源）
5. 定位到的冲突假设 → 两者都降为 progressive_apply（即使 validated_confidence >= 0.90）
```

### 7.4 异常信号检测

防止知识投毒和异常用户行为：

```
单用户信号占比检测:
  - 同一 scenario 下，来自同一 user_anon_id 的信号占比 >= 50%
  - → 该假设的 diversity_score 强制设 0（来自单一用户，置信度降低）

信号突发检测:
  - 24h 内同一 scenario + 同一纠正方向的信号 >= 10 条
  - → 标记为异常突发，暂停该方向的假设生成，告警

权重异常检测:
  - 任一进化指标的权重超过 0.95
  - → 锁定权重，不允许继续爬坡（保留最低限度的多样性）
```

### 7.5 知识库健康度量

每周围绕以下指标评估系统状态：

| 指标 | 计算 | 健康范围 | 告警阈值 |
|------|------|---------|---------|
| 信号有效率 | (correction+supplement) / total_queries | < 15% | > 25% |
| 强化率 | reinforcements / total_queries | > 40% | < 25% |
| 反事实命中率 | counterfactuals / corrections | > 30% | < 10% |
| L3 率 | l3 / total | < 5% | > 10% |
| 草稿晋升率 | promoted_drafts / total_drafts | > 30% | < 10% |
| 权重冻结率 | frozen_patches / total_active_patches | < 10% | > 20% |

---

## 八、信号 → 假设 → 应用 全链路

### 8.1 链路总览

```
Session 结束
  │
  ├─→ signal_detector: 结构化对比 → 写 signals/*.jsonl
  ├─→ counterfactual_check: 候选回溯 → 写 counterfactuals.jsonl
  └─→ reinforcement_check: 接受检测 → 写 reinforcements.jsonl
        │
        ▼ (每周一 9am 或 周新增信号 >= 50)
signal_analyzer: 聚类 → 生成假设
        │
        ├─ 按 industry+scenario 分组
        ├─ 频次/一致性/多样性 三维评分
        ├─ 区分: correction / counterfactual → 不同 proximity_bonus
        └─ 产出 hypothesis YAML
              │
              ▼
validator: hold-out 验证
        │
        ├─ 75/25 分层分离
        ├─ 按假设类型分别验证
        ├─ 组合回测（批量子集）
        └─ 产出 validated_confidence
              │
              ▼
          决策:
          >= 0.90 → full_apply（初始权重 = validated_confidence）
          >= 0.70 → progressive_apply（初始权重 = 0.30）
          < 0.70  → discarded
              │
              ▼
applier: 写入 patch → 重建 _active/ → 重载缓存
        │
        ├─ 生成 .patch 文件
        ├─ 验证 patch schema
        ├─ 重建受影响 _active/ 文件
        └─ 标记 hypothesis status = applied | progressive
              │
              ▼ (每周一)
爬坡评估: 健康计数器检查
        │
        ├─ 无退化 + 有接受 → 权重 +0.15
        ├─ 无数据 → 权重保持
        ├─ 退化 → 权重冻结
        └─ 连续冻结 → 衰减 → 废弃
```

### 8.2 链路中的关键数据流

```
learn/data/
├── signals/                          # 原始信号
│   ├── corrections.jsonl
│   ├── supplements.jsonl
│   ├── refinements.jsonl
│   ├── extensions.jsonl
│   ├── l3_fallbacks.jsonl
│   ├── l1_misses.jsonl
│   ├── reinforcements.jsonl          # v4 新增
│   └── counterfactuals.jsonl         # v4 新增
│
├── counters/{date}.jsonl             # 健康计数器（同 v3，含 by_scenario）
│
├── hypotheses/                       # 假设
│   └── hyp-{date}-{seq}.yaml
│
├── proximity/                        # v4 新增：邻近度矩阵
│   └── {industry}_cooccurrence.json  # 每周重建
│
└── evolution-log/                    # 审计追踪
    ├── _index.jsonl
    └── {year}-{month}/
        ├── hyp-001_before.yaml
        ├── hyp-001_after.yaml
        └── hyp-001.diff
```

---

## 九、主动学习（v4.5，feature flag 默认关闭）

### 9.1 动机

当 intent_parser 的 top-2 匹配得分非常接近时，系统面临歧义。v3/v4 的做法是直接选得分最高的——但得分最高的不一定是用户想要的。

主动学习让系统在不确定时反问用户，用最小的交互成本消除歧义。

### 9.2 触发条件

```python
# scripts/intent_parser.py — 主动学习分支

ACTIVE_LEARNING_ENABLED = config.get("evolution.active_learning.enabled", False)
CONFIDENCE_GAP_THRESHOLD = config.get("evolution.active_learning.confidence_gap_threshold", 0.10)
MAX_CLARIFICATIONS = config.get("evolution.active_learning.max_clarifications_per_session", 3)

def parse_intent(query, top_k=3, session_clarifications=0):
    results = retriever.search(query, top_k=top_k)

    # 主动学习分支（feature flag 控制）
    if (ACTIVE_LEARNING_ENABLED
        and len(results) >= 2
        and session_clarifications < MAX_CLARIFICATIONS):

        gap = results[0].score - results[1].score
        if gap < CONFIDENCE_GAP_THRESHOLD:
            # 不确定 → 反问
            return ClarificationRequest(
                options=[results[0], results[1]],
                question=f"你要看的是「{results[0].name}」（{results[0].sample_indicators}）
                          还是「{results[1].name}」（{results[1].sample_indicators}）？"
            )

    return results[0]
```

### 9.3 用户体验

```
用户: "看品类表现"

系统: 💡 你要看的是:
      A. 品类概况（销售额、订单量、SKU 数）
      B. 品类健康度（毛利率、动销率、库存周转）
      [回复 A 或 B，或直接描述你想要的]

用户: "B"

系统: 好的，按「品类健康度综合诊断」模板执行。
      核心指标: 毛利率 + 净利率 + 动销率
      ...
```

### 9.4 学习价值

每次反问和用户选择产生一个**高精度信号**——用户明确选择了 A 或 B，消除了所有歧义：

```json
{
  "ts": "2026-05-02T10:40:00Z",
  "session": "abc123",
  "type": "active_clarification",
  "query": "品类表现",
  "options": [
    {"template": "category_overview", "score": 0.72},
    {"template": "category_health_diagnostic", "score": 0.68}
  ],
  "user_selected": "category_health_diagnostic",
  "gap": 0.04
}
```

这个信号的进化价值高于普通的强化信号——它不是"用户没纠正"的弱信号，而是"用户明确选择"的强信号。在聚类时可以给 active_clarification 信号 1.5x 权重。

### 9.5 安全边界

- **默认关闭**：feature flag 控制，不影响现有行为
- **频率限制**：每 session 最多 3 次反问（避免干扰）
- **用户可关闭**：会话中说"不要问我"即可永久关闭（per session）
- **不改变 return 结构**：ClarificationRequest 是 parse_intent 的一个合法返回类型，调用方需要处理
- **渐进上线**：先对 10% session 开启，观察用户接受率 > 80% 再全量

### 9.6 与 v4 核心的关系

主动学习是**可选增强**，不是 v4 核心闭环的一部分。关闭 feature flag 时，系统行为与 v4 完全一致。

代码量约 60 行（intent_parser 分支 + ClarificationRequest 数据类），作为 v4.5 的可选特性独立交付。

---

## 十、实施路线

| 阶段 | 内容 | 核心产出 | 依赖 |
|------|------|---------|------|
| **V4-P0** | 继承 v3 P0-P2（observation + 信号埋点 + 计数器） | 信号开始积累 | v3 已有 |
| **V4-P1** | 四类信号体系上线（correction + reinforcement + counterfactual + preference） | 四类信号 JSONL 写入 | V4-P0 |
| **V4-P2** | 共现矩阵 + 语义邻近传播 + 跨行业迁移（种子映射） | 行业内一次纠正辐射邻近指标；跨行业小幅度迁移 | V4-P1 |
| **V4-P3** | 权重化知识表示（点估计 → 权重分布） | intent-routing / template 改用 weights | V4-P2 |
| **V4-P4** | 渐进式置信框架（full_apply + progressive_apply + 爬坡评估） | 全自主应用，无回滚 | V4-P3 |
| **V4-P5** | 双层知识库 + 补丁栈 | _canonical / _active / _patches 架构 | V4-P4 |
| **V4-P6** | 自主模板内容进化（原子化自动调整） | 模板自动更新，无人介入 | V4-P5 |
| **V4-P7** | 自主模板沉淀 + intent 草稿机制 | 模板全生命周期自主管理 | V4-P5 |
| **V4-P8** | 健康监控 + 异常检测 | 全链路可观测 | V4-P6+P7 |
| **V4-P9** | 主动学习（可选，feature flag 默认关闭） | 系统在低置信度时反问用户 | V4-P1 |

V4-P1 至 V4-P3 可部分并行。V4-P4 起串行依赖。V4-P9 可在 V4-P1 后任意时间上线。

V4-P1 至 V4-P3 可部分并行。V4-P4 起串行依赖。

**与 v3 的关系：**
- V4-P0 = v3 P0-P2（继承现有信号体系）
- V4-P1 = 在 v3 信号体系上增加 reinforcement + counterfactual + preference
- V4-P2 = 语义邻近传播 + 跨行业迁移（种子映射）
- V4-P4 替代了 v3 的 P4-P5（回滚 + 人工确认 → 渐进权重 + 全自主）
- V4-P6+P7 替代了 v3 P6（人工模板进化 → 自主模板进化）
- V4-P9 = v4.5 可选特性，feature flag 控制

---

## 十一、需要改动的文件

### 新增

| 文件 | 说明 | 所在目录 |
|------|------|---------|
| `learn/ingest/signal_detector.py` | 结构化对比：correction/supplement/refinement/extension | ingest/ |
| `learn/ingest/reinforcement_detector.py` | 强化信号检测（用户接受判定） | ingest/ |
| `learn/ingest/counterfactual_check.py` | 反事实信号检测（候选回溯） | ingest/ |
| `learn/ingest/preference_detector.py` | 图表/报告偏好检测 | ingest/ |
| `learn/ingest/counter_writer.py` | 计数器写入 | ingest/ |
| `learn/analyze/signal_analyzer.py` | 信号聚类 → 假设生成 | analyze/ |
| `learn/analyze/proximity_builder.py` | 共现矩阵构建 | analyze/ |
| `learn/analyze/propagation.py` | 语义邻近传播 + 跨行业迁移 | analyze/ |
| `learn/validate/validator.py` | hold-out 回测验证 | validate/ |
| `learn/validate/combo_validator.py` | 组合回测（多假设交互检测） | validate/ |
| `learn/apply/applier.py` | 写入 patch 文件 + 触发 _active/ 重建 | apply/ |
| `learn/apply/weight_climber.py` | 每周权重爬坡评估 | apply/ |
| `learn/apply/patch_builder.py` | 从 _canonical + patches 重建 _active/ | apply/ |
| `learn/monitor/anomaly_detector.py` | 异常信号检测（单用户占比、突发检测） | monitor/ |
| `learn/monitor/health_metrics.py` | 健康度量计算 + 趋势报告 | monitor/ |
| `knowledge/_schemas/observation_v2.json` | Observation schema | _schemas/ |
| `knowledge/_schemas/hypothesis_v2.yaml` | Hypothesis schema | _schemas/ |
| `knowledge/_schemas/template_v2.yaml` | Template schema | _schemas/ |
| `knowledge/_base/cross_industry_mappings.yaml` | 跨行业指标映射（种子映射） | _base/ |

### 修改

| 文件 | 改动 |
|------|------|
| `learn/hooks/analyze-observe` | 重写：记录结构化 observation（含 candidates + context + user_anon_id） |
| `learn/hooks/session-summary` | 调用 ingest/ 全套信号检测；写 counters；修复触发阈值 |
| `learn/data/config.yaml` | 新增 evolution 配置段（v4 全部阈值） |
| `learn/agents/pattern-detector.md` | 扩展：消费 v4 四类信号作为额外输入 |
| `scripts/intent_parser.py` | 返回 candidates 列表；主动学习分支（feature flag 控制） |

### 不变

- `learn/hooks/load-instincts`、`learn/hooks/instinct-apply`（SessionStart hook 不变）
- `learn/scripts/instinct-engine.py`（保留在 scripts/，现有功能不变）
- `learn/data/observations/`、`learn/data/patterns/`、`learn/data/instincts/`（现有数据保留）
- 所有 skills（12 个）、agents（danalyzer、error-handler、pattern-detector）、rules（4 级）、connectors
- `knowledge/industry/fmcg/**/*.yaml` 格式（仅内容通过 applier 写入权重）
- `hooks/session-start`、`hooks/session-routing.md`、`hooks/post-tool-use`

### 移除（v3 组件）

| 文件 | 原因 |
|------|------|
| `learn/scripts/rollback.py` | 渐进权重替代回滚——错误变更自行消亡，不回滚 |
| `learn/scripts/health_check.py` | 功能合并到 monitor/health_metrics.py |

---

## 十二、明确不在 v4 范围内

以下作为 v5+ 方向预留：

- **Embedding 级语义邻近**：当前用共现矩阵（符号级），v5 可升级为预训练 embedding
- **跨行业 Embedding 迁移**：从种子映射升级为学习到的 embedding 空间对齐
- **协作进化**：多用户之间的知识共享与冲突消解（当前仅全局学习 + 单用户信号衰减）
- **因果推理**：理解用户为什么纠正，而不只是记录纠正了什么（需 LLM 参与 + 行为序列建模）
- **模型参数自动调优**：RFM 分位数、预测窗口等

---

*本文档于 2026-05-02 创建 (v4.0)，2026-05-02 修订 (v4.1 — 前移跨行业迁移/多模态偏好/主动学习)。v3.1 文档保留作为架构演进参考。*

