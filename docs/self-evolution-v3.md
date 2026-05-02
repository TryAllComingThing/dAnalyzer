# dAnalyzer 自进化系统 v3

> 版本: 3.1 — 2026-05-02
> 前身: v1 (全量遥测, 过度设计) → v2 (异常信号 + 多轮纠正 + 六层模型)
> v3.1 聚焦: 术语纠正 → 关键词/指标调整的最短闭环，模板体系（已有纠正 + 新模板沉淀）

---

## 一、设计原则

1. **只记录意外。** 成功的查询不包含改进信息。仅偏差（纠正、补充、重查、L3 兜底、L1 校验失败）值得存储。
2. **计数 + 信号分离。** 计数器回答"有没有退化"（聚合数字），信号回答"哪里要改"（详细事件）。
3. **确定性优先。** 信号检测用结构化对比 + 规则，不依赖 LLM。LLM 仅预留给未来的假设质量评估。
4. **行业相关 vs 行业通用严格分界。** 检测逻辑通用，产生什么改进行业相关。
5. **不对现有执行链路增加开销。** 埋点是追加行为，不改变现有 return 结构。

---

## 二、信号体系

### 2.1 用户反馈信号（从多轮对话中提取）

| 信号 | 含义 | 检测方式 | 进化价值 |
|------|------|---------|---------|
| **correction** | 用户否定了上一轮的结果，要求不同内容 | 同一 session 相邻 query 的 indicators 完全替换 + scenario 不变 | 术语映射错误 |
| **supplement** | 用户接受了上一轮结果，追加新指标 | 同一 session 相邻 query 的 indicators 纯扩充 | 指标组合不完整 |
| **refinement** | 用户接受了结果但调整了精度/范围 | 同一 session 相邻 query 的 indicators 部分重叠 | 默认粒度不当 |
| **extension** | 用户在同一分析上下文中追加新步骤 | 同一 session 内多轮 query 的 scenario 不变但 skill chain 不同 | 分析路径不完整 |

### 2.2 系统信号（内部可观测的事实）

| 信号 | 含义 | 触发点 | 进化价值 |
|------|------|-------|---------|
| **l3_fallback** | 知识库完全无法匹配 | `intent_parser.py` L3 分支 | 知识盲区 |
| **l1_validation_failure** | LLM 转写的 code 不存在 | `intent_parser.py` L1 校验层 | LLM 幻觉模式 |

### 2.3 不捕获的信号

- **unrelated**: scenario 变化 → 话题切换，不包含系统错误
- **narrowing**: indicators 纯缩减 → 用户自己缩小范围
- **no_change**: indicators 完全不变 → 用户重复查看或放弃，没有显式反馈机制无法区分

---

## 三、纠正检测引擎（核心）

### 3.1 输入

Session 结束时，该 session 的所有 observation 记录（按 turn 排序）。每条记录包含：

```json
{
  "turn": 2,
  "query": "我要的是毛利率和动销",
  "skill": "danalyzer-core",
  "source": "l1_exact",
  "industry": "fmcg",
  "indicators_retrieved": ["gross_margin_rate", "sell_through_rate"],
  "scenarios_retrieved": ["category_analysis"],
  "models_retrieved": [],
  "analysis_type": "diagnostic",
  "skill_chain_planned": ["data-query", "data-clean", "data-analysis", "model", "visual", "report"],
  "skill_chain_actual": ["data-query", "data-analysis", "model", "visual"],
  "template_matched": "category_health_diagnostic",
  "context": {
    "time_period": "month_end",
    "query_raw": "我要的是毛利率和动销",
    "trigger_source": "correction"
  },
  "error": null
}
```

**context 字段说明：**

| 字段 | 类型 | 说明 | 来源 |
|------|------|------|------|
| `time_period` | enum | `month_end` / `promo_period` / `quarter_end` / `normal` | 系统日期 + 行业日历 |
| `query_raw` | string | 用户原始输入（保留未解析文本） | 直接记录 |
| `trigger_source` | enum | `new_query` / `correction` / `follow_up` | session-summary hook 判定 |

`query_raw` 的作用：当系统解析失败（L3 兜底、indicators_retrieved 为空）时，原始文本是唯一的信号来源。信号分析阶段可回溯 query_raw 做关键词提取，缓解解析失败导致的信号丢失问题。

### 3.2 判定逻辑（纯规则，零 LLM）

```python
# 否定/纠正常见模式（中文 + 英文）
CORRECTION_PATTERNS = [
    r"(?:不是|不对|错了|我要的是|应该是|改成|换成|纠正|修正|重新)",
    r"(?:not|could be wrong|should be|actually|I meant|change to|replace)",
]

# 信号强度：新增指标数占总数的比例超过此阈值视为纠正（即使有部分重叠）
CORRECTION_REPLACEMENT_RATIO = 0.5


def classify_query_pair(prev, curr):
    """对同一 session 内相邻的两条 observation 分类"""

    # 场景变了 → 换话题
    if set(prev["scenarios_retrieved"]) != set(curr["scenarios_retrieved"]):
        return "unrelated"

    prev_inds = set(prev["indicators_retrieved"])
    curr_inds = set(curr["indicators_retrieved"])

    # 都不为空才做对比
    if not prev_inds or not curr_inds:
        return "insufficient_data"

    # 完全不相交 → 纠正
    if prev_inds.isdisjoint(curr_inds):
        return "correction"

    # 纯扩充 → 补充
    if curr_inds > prev_inds:
        return "supplement"

    # 纯缩减 → 用户自己缩小范围，不记录
    if curr_inds < prev_inds:
        return "narrowing"

    # 完全一致 → 静默重查（信号弱，不记录）
    if prev_inds == curr_inds:
        return "no_change"

    # 部分重叠 → 检查是否为部分纠正
    replaced = prev_inds - curr_inds          # 被拿掉的指标
    added = curr_inds - prev_inds             # 新增的指标
    kept = prev_inds & curr_inds              # 保留的指标
    replacement_ratio = len(added) / len(curr_inds)

    # 替换比例高 + query 含否定词 → 纠正（部分重叠纠正）
    if replacement_ratio >= CORRECTION_REPLACEMENT_RATIO and _has_correction_signal(curr):
        return "correction"

    # 否则 → 调整
    return "refinement"


def _has_correction_signal(record):
    """检测 query 文本是否包含纠正意图"""
    import re
    query = record.get("query", "")
    for pattern in CORRECTION_PATTERNS:
        if re.search(pattern, query):
            return True
    return False
```

LLM 不参与分类。分类逻辑是确定性规则——指标集合运算 + 否定词正则匹配。正则仅辅助区分"部分重叠纠正"与"纯调整"，不引入概率判断。

### 3.3 输出

```
learn/data/signals/corrections.jsonl
learn/data/signals/supplements.jsonl
learn/data/signals/refinements.jsonl
learn/data/signals/extensions.jsonl
learn/data/signals/l3_fallbacks.jsonl
learn/data/signals/l1_misses.jsonl
```

每条信号都带有 `industry` 和 `template_matched`（如果命中）标签。

### 3.4 信号示例

```json
// corrections.jsonl — 纠正信号（携带模板信息）
{
  "ts": "2026-05-02T10:23:00Z",
  "session": "abc123",
  "turn_pair": [1, 2],
  "industry": "fmcg",
  "scenario": "category_analysis",
  "indicators_before": ["sales_amount", "order_count"],
  "indicators_after": ["gross_margin_rate", "sell_through_rate"],
  "template_before": "category_overview",
  "template_after": "category_health_diagnostic",
  "query_before": "品类表现",
  "query_after": "我要的是毛利率和动销情况",
  "detection_method": "structured_comparison"
}

// corrections.jsonl — 部分重叠纠正（替换比例 >= 50% + 否定词）
{
  "ts": "2026-05-02T10:27:00Z",
  "session": "abc123",
  "turn_pair": [1, 2],
  "industry": "fmcg",
  "scenario": "category_analysis",
  "indicators_before": ["sales_amount", "order_count", "sku_count"],
  "indicators_after": ["gross_margin_rate", "sell_through_rate", "order_count"],
  "replaced_indicators": ["sales_amount", "sku_count"],
  "added_indicators": ["gross_margin_rate", "sell_through_rate"],
  "kept_indicators": ["order_count"],
  "replacement_ratio": 0.67,
  "query_before": "看品类表现",
  "query_after": "不对，我要的是毛利率和动销",
  "detection_method": "partial_replacement_with_negation"
}

// supplements.jsonl — 补充信号
{
  "ts": "2026-05-02T10:25:00Z",
  "session": "abc123",
  "turn_pair": [2, 3],
  "industry": "fmcg",
  "scenario": "category_analysis",
  "existing_indicators": ["gross_margin_rate", "sell_through_rate"],
  "added_indicators": ["inventory_turnover"],
  "template": "category_health_diagnostic",
  "detection_method": "structured_comparison"
}
```

---

## 四、分析管道：信号 → 假设

### 4.1 触发时机

两个条件满足其一：
- 本周新增信号 >= 50 条（可配置）
- 每周定时（周一 9am）

### 4.2 聚类逻辑（`learn/scripts/signal_analyzer.py`）

```
correction 聚类:
  1. 按 industry + scenario 分组
  2. 组内统计 (indicators_before → indicators_after) 的频次
  3. 同一映射出现 >= 3 次 → 产出假设
  例: 在 fmcg + category_analysis 下,
      [sales_amount] → [gross_margin_rate] 出现 5 次
      → 假设: 品类语境下应该优先推荐毛利率而非销售额

  若纠正伴随 template_before → template_after 切换:
      → 假设: 模板路由对齐（什么查询该推荐哪个模板）

supplement 聚类:
  1. 按 industry + scenario 分组
  2. 组内统计被追加的指标频次
  3. 同一指标被追加 >= 3 次 → 产出假设

refinement 聚类:
  1. 按 industry + scenario 分组
  2. 统计指标调整方向
  3. 同一方向 >= 3 次 → 产出假设

l3_fallback 聚类:
  1. 按 industry 分组
  2. 对 query 做 N-gram 关键词提取
  3. 高频关键词组合（>= 3 次）→ 产出假设

extension 聚类:
  1. 提取相同（或高度相似）的多步骤路径
  2. 频次 >= 5 且跨 >= 3 个 session → 产出假设
  3. 例: [品类查询→品类诊断→渠道拆解→导出] 出现 6 次 → 模板沉淀候选
```

### 4.3 假设类型

| 假设类型 | 信号源 | 进化对象 | 自动化 |
|---------|-------|---------|--------|
| `keyword_adjustment` | correction | intent-routing 的 keywords / default_indicators | 可自动 |
| `indicator_priority` | correction | intent-routing 中 default_indicators 的排序 | 可自动 |
| `indicator_combination` | supplement | scenario 的 required_indicators | 可自动 |
| `template_routing` | correction | query + context → template 的映射权重 | 可自动 |
| `template_content` | supplement + refinement | 已有模板内部的指标/步骤调整 | 人工确认 |
| `template_discovery` | extension | 发现新高频分析路径 → 建议创建模板 | 人工确认 |
| `intent_new` | l3_fallback | 新建 intent | 人工确认 |

### 4.4 假设格式

```yaml
# learn/data/hypotheses/hyp-20260502-001.yaml
id: hyp-20260502-001
type: keyword_adjustment
industry: fmcg
dimension: terminology_mapping

target:
  file: knowledge/intent-routing.yaml
  path: intents[category_overview]
  field: default_indicators
current:
  default_indicators: [sales_amount, order_count, sku_count]
suggested:
  default_indicators: [gross_margin_rate, sell_through_rate, sales_amount, sku_count]

evidence:
  signal_type: correction
  signal_ids: [corr-0042, corr-0058, corr-0091, corr-0103, corr-0112]
  frequency: 5
  period_days: 14

confidence: 0.72
status: pending_validation
created_at: "2026-05-02T09:00:00Z"
```

### 4.5 置信度计算

置信度由三个维度合成，满分 1.0：

```
confidence = α × frequency_score + β × consistency_score + γ × diversity_score

权重:  α = 0.40  频次得分
       β = 0.35  一致性得分
       γ = 0.25  跨 session 多样性得分
```

**频次得分**（α = 0.40，饱和型）：

```
frequency_score = min(frequency / F_sat, 1.0)

其中 F_sat 按信号类型不同:
  correction:     F_sat = 5   (5 次出现即满分)
  supplement:     F_sat = 5
  refinement:     F_sat = 5
  extension:      F_sat = 8   (扩展路径需要更多验证)
  l3_fallback:    F_sat = 3   (知识盲区 3 次即可确认)
```

**一致性得分**（β = 0.35）：

```
对 correction: consistency = 1 - (direction_count / total_signals)
                方向越集中 → 得分越高
  例: A→B 出现 5 次 → 方向数=1, consistency = 1 - 1/5 = 0.80
  例: A→B 3次, A→C 2次 → 方向数=2, consistency = 1 - 2/5 = 0.60

对 supplement: consistency = same_indicator_count / total_signals
                同一指标被追加剧中
  例: inventory_turnover 被补充 4次, order_count 被补充 1次 → 4/5 = 0.80

对 l3_fallback: consistency = N-gram 命中次数 / total_signals
                 同一关键词组合重复出现比例
```

**多样性得分**（γ = 0.25）：

```
diversity_score = min(unique_sessions / D_sat, 1.0)

其中 D_sat = 3（跨 3 个不同 session 即满分）

理由: 来自多个 session 的信号比单一 session 重复更有说服力
```

**综合示例**：

```
假设 A: correction, frequency=5, 同一方向 A→B 全部 5 次, 来自 3 个 session

  frequency_score = min(5/5, 1.0) = 1.00
  consistency_score = 1 - 1/5 = 0.80
  diversity_score = min(3/3, 1.0) = 1.00

  confidence = 0.40×1.00 + 0.35×0.80 + 0.25×1.00 = 0.40 + 0.28 + 0.25 = 0.93
  → auto_apply (≥ 0.80)


假设 B: supplement, frequency=4, 同一指标被补充 2次, 来自 2 个 session

  frequency_score = min(4/5, 1.0) = 0.80
  consistency_score = 2/4 = 0.50
  diversity_score = min(2/3, 1.0) = 0.67

  confidence = 0.40×0.80 + 0.35×0.50 + 0.25×0.67 = 0.32 + 0.18 + 0.17 = 0.66
  → review_queue (≥ 0.50)
```

**validated_confidence** 回测后重新计算：在原始公式基础上乘以回测通过率 `pass_rate`，其中 `pass_rate = 通过验证的 hold-out queries 数 / hold-out queries 总数`（见 5.1 节）。

---

## 五、验证与应用

### 5.1 验证（`learn/scripts/validator.py`）

对每条 `pending_validation` 的假设，验证分为两步。

**Step 1: 数据分离**

```
1. 加载假设的全部 source_queries（原始 query 对）
2. 按 75/25 比例分层随机分成训练集和 hold-out 集
   - 分层维度: industry + scenario（保持每层的分布）
   - 训练集: 用于第 4 章生成假设（实际已用，此处记录）
   - hold-out 集: 专用于验证，不参与假设生成
3. 仅当 source_queries 总数 >= 4 时才做分割（否则全部用于验证，confidence 降低）
```

**Step 2: 回测验证**

```
1. 模拟应用假设后的系统状态:
   - keyword_adjustment:      修改 intent-routing 的 default_indicators，重新跑 parse_intent
   - indicator_priority:      调整指标 importance 权重，重新跑 retriever.search
   - indicator_combination:   扩展 scenario 的 required_indicators，检查是否覆盖用户补充后的指标
   - template_routing:        调整模板匹配权重，检查推荐结果是否与用户选择一致
   - template_discovery:      检查路径是否匹配 applicability 条件
2. 在 hold-out 集上逐一回测，按假设类型使用不同的通过标准:

   keyword_adjustment:
     通过标准: query_after 的指标 ⊆ 检索结果 AND L3 不退化

   indicator_priority:
     通过标准: query_after 的指标在检索结果中排名上升（或不下降）AND L3 不退化

   indicator_combination:
     通过标准: 补充后的指标 ⊆ 扩展后的 required_indicators

   template_routing:
     通过标准: 调整权重后 target 模板在匹配排序中得分 >= 调整前
               具体: 对每条 signal，检查 template_after 的匹配排名是否上升或保持第1
                     且不劣化其他已知 query 的模板匹配结果

   template_discovery / intent_new:
     通过标准: N/A — 这两类假设一律走人工确认，验证仅记录对比报告供参考

3. 计算 pass_rate:
   - pass_rate = 通过的 hold-out queries 数 / hold-out queries 总数
   - template_discovery / intent_new 不计算 pass_rate，不产生 validated_confidence
4. 检查退化:
   - 在全部 source_queries（训练+hold-out）上检查是否有已知 query 退化
   - 任一 query 退化 → 假设降级为 review_queue，不限 pass_rate
5. 产出 validated_confidence = confidence × pass_rate
   - confidence 来自 4.5 节的三维公式
   - pass_rate ∈ [0, 1] 作为缩放因子
```

### 5.2 置信度门槛

```
validated_confidence >= 0.80  →  auto_apply   (自动应用)
validated_confidence >= 0.50  →  review_queue  (写入 hypotheses/，人工确认)
validated_confidence <  0.50  →  discarded     (记录原因，不应用)
```

其中 `validated_confidence = confidence × pass_rate`（confidence 来自 4.5 节，pass_rate 来自 5.1 节 hold-out 回测）。

**降级规则（独立于门槛，优先级最高）：**
- 在回测中发现任一已知 query 退化 → 强制降为 `review_queue`，即便 validated_confidence >= 0.80

可自动应用：`keyword_adjustment`、`indicator_priority`、`indicator_combination`、`template_routing`。

必须人工确认：`template_content`、`template_discovery`、`intent_new`。

### 5.3 应用（`learn/scripts/applier.py`）

```
1. 读 hypothesis
2. 根据 target 定位目标文件和位置
3. 生成 before snapshot → 写入 evolution-log/
4. 执行变更:
   - intent-routing.yaml:     修改 default_indicators / keywords / 模板路由权重
   - indicators/*.yaml:        补充 keywords 字段
   - scenarios/*.yaml:         扩展 required_indicators / optional_indicators
   - template/{industry}/*.yaml: 更新 routing 权重 / 指标步骤 / 版本号
   - template/{industry}/ (新):  创建新模板文件（template_discovery，人工编写内容后）
5. 生成 after snapshot → 写入 evolution-log/
6. 重载相关缓存（领域词典、模板匹配表）
7. 标记 hypothesis status = applied
```

### 5.4 审计追踪

```
learn/data/evolution-log/
├── 2026-05/
│   ├── hyp-001_before.yaml
│   ├── hyp-001_after.yaml
│   └── hyp-001.diff
├── _index.jsonl                # 时序索引
└── _rollback.sh                # 自动生成的回滚脚本
```

---

## 六、分析模板体系

### 6.1 模板的角色

模板代表**领域最佳实践**——品类诊断应该看什么指标、促销评估应该走什么步骤。模板由领域专家定义和维护。

系统学习的是三件事：
- **路由对齐**：什么情况下该推荐哪个已有模板（自动）
- **内容进化**：已有模板的指标/步骤是否还符合实际需要（偏离监控 → 人工确认后更新）
- **新模板发现**：高频且无模板匹配的分析路径 → 建议创建新模板（人工确认+人工编写）

### 6.2 三大进化线

```
查询 "品类表现" ──→ 匹配模板
                    │
                    ├── 命中模板A ──→ 推荐 ──→ 用户纠正为模板B
                    │   └────────────────────→ 第一线：路由对齐
                    │                           调整 query→模板 的映射权重
                    │                           （自动闭环，每次纠正生效）
                    │
                    ├── 命中模板A ──→ 推荐 ──→ 用户接受
                    │   │        └──→ 但调整了指标/跳过了步骤/追加了内容
                    │   │             ──→ 第二线：偏离监控
                    │   │                  4-8周累计 → 模板内容进化建议
                    │   │                  （人工确认后方可更新）
                    │   │
                    │   └──→ 用户完全接受，无调整
                    │        ──→ 强化路由映射
                    │
                    └── 无模板命中 ──→ 系统自行执行
                                       │
                                       └──→ 分析路径被记录
                                            │
                                            └──→ 高频 + 跨用户 + 有复杂度
                                                 ──→ 第三线：模板沉淀
                                                      建议创建新模板
                                                      （人工编写内容）
```

### 6.3 第一线：模板路由对齐（自动）

当用户纠正导致模板切换时：

```
轮次1: query="品类表现" → 系统推荐 品类概况模板 → 用户纠正为促销效果模板
轮次2: query="品类表现" → 系统推荐 促销效果模板 → 用户又纠正为品类健康度模板

信号: correction 携带 template_before, template_after

学习:
  "品类表现" + 大促期间 → 促销效果模板（权重 +1）
  "品类表现" + 月末 → 品类健康度模板（权重 +1）
  "品类表现" + 无其他信号 → 品类概况模板（基线不调整，除非连续纠正）
```

### 6.4 第二线：模板内容进化（人工确认）

系统持续监控每个模板的偏离度。当某项偏离超过阈值，产出模板更新建议。

**偏离度统计示例：**

```
模板「品类健康度诊断」最近 8 周 (22 次使用):

指标层面:
  gross_margin_rate       被接收 22次，未被纠正           → 稳定
  sell_through_rate       被接收 18次，被替换 4次           → 关注
  inventory_turnover      被接收 12次，被跳过 10次          → 偏离严重
  net_margin_rate         不在模板中，被补充 8次             → 应加入核心

步骤层面:
  data-query              执行率 100%                      → 稳定
  data-clean              执行率 90%                       → 稳定
  model (归因)            执行率 40%，被跳过 60%             → 考虑降为可选
  visual (热力图)         执行率 80%                       → 稳定
  渠道拆解                 不在模板中，被追加 5次             → 考虑加入可选步骤
```

**触发条件：**
- 指标偏离（替换/跳过/补充）>= 40% 使用次数
- 步骤跳过 >= 50% 使用次数
- 新指标补充 >= 30% 使用次数

**产出建议（人工确认后由 applier 执行）：**

```
建议: 品类健康度诊断模板 v1 → v2
  1. 核心指标加入 net_margin_rate（8次补充，补充后无进一步调整）
  2. inventory_turnover 降为可选指标（10次跳过）
  3. model(归因) 从核心步骤改为可选步骤（60%跳过率）
  4. 新增可选步骤: 渠道拆解（5次追加）
```

### 6.5 第三线：模板沉淀（人工确认）

当分析路径频繁出现且不匹配任何现有模板时，系统建议创建新模板。

**沉淀条件（四重门）：**

```
1. 相同路径（indicators + scenarios + skill_chain）出现 >= 5 次
2. 跨越 >= 3 个不同 session
3. 无法匹配任何现有模板（applicability 检查全部未命中）
4. 路径复杂度 >= 3 个步骤
```

**产出建议（人工确认 + 人工编写内容后由 applier 创建文件）：**

```
建议: 创建新模板
  名称: 渠道绩效对比分析（建议，人工确定）
  适用: scenario=channel_analysis + analysis_type=diagnostic
  推荐指标: [sales_amount, channel_revenue_share, terminal_coverage_rate]
  推荐步骤: 查询 → 清洗 → 分析 → 对比报告 → Excel导出

  参考路径（5次，3个不同 session）:
    - session-042: data-query → data-clean → data-analysis → visual → report
    - session-057: data-query → data-analysis → visual → report
    - session-081: data-query → data-clean → data-analysis → visual → report
    - session-093: data-query → data-analysis → visual → report
    - session-105: data-query → data-clean → data-analysis → visual → report

  置信度: 0.72
  状态: 待人工确认 + 人工编写模板内容
```

**关键：系统只负责发现"这里缺一个模板"，并给出参考路径。模板的具体内容（指标选择、步骤设计、注意事项）由人编写。**

### 6.6 模板存储

与现有 `knowledge/template/` 的 SQL/报告模板共存：

```
knowledge/template/
├── fmcg/                              # 行业分析模板（新增）
│   ├── category_health_diagnostic.yaml
│   └── ...
├── _base/                             # 模板格式规范（新增）
│   └── template_schema.yaml
├── common-sql-template.md             # 以下为现有模板（保持不变）
├── export-template.md
├── funnel-sql-template.md
├── report-template.md
├── time-analysis-template.md
└── user-analysis-template.md
```

### 6.7 模板格式

```yaml
# knowledge/template/fmcg/category_health_diagnostic.yaml
id: category_health_diagnostic
name: 品类健康度综合诊断
version: 2                              # 版本号，进化更新时递增
description: >
  从毛利率、动销率、库存周转三个维度诊断各品类健康度。
  适用于周度/月度品类复盘场景。

# 适用条件
applicability:
  intents: [diagnostic]
  scenarios: [category_analysis]
  min_indicators: 3

# 推荐指标
indicators:
  primary:
    - gross_margin_rate
    - sell_through_rate
    - net_margin_rate                  # v2 新增
  secondary:
    - sales_amount
    - sku_count
    - inventory_turnover               # v2: 从 primary 降为 secondary
    - out_of_stock_rate

# 推荐步骤
steps:
  - skill: data-query
    description: 按品类查询最近 4 周数据
    notes: 注意过滤上市 < 30天的新品

  - skill: data-clean
    rules: [null_check, outlier_filter]

  - skill: data-analysis
    methods: [descriptive, ranking, distribution]

  - skill: model                         # v2: 标记为可选
    model: attribution-model
    optional: true
    condition: 当需要深度归因时

  - skill: visual
    types: [heatmap, bubble_chart]

  - skill: channel_breakdown             # v2 新增可选步骤
    optional: true
    description: 按渠道拆解品类数据

# 路由权重（自进化调整）
routing:
  trigger_queries:
    - pattern: "品类.*(表现|健康|诊断)"
      weight: 0.85
    - pattern: ".*品类.*(毛利|动销|周转)"
      weight: 0.90

# 模板元信息
meta:
  created: 2026-03-15
  last_updated: 2026-07-01
  evolved_from:
    - type: content_update
      hypothesis: hyp-20260701-003
    - type: initial
      source: manual
```

### 6.8 模板触发方式

模板采用**主动推荐**模式。当用户查询命中 applicability 条件时：

```
系统内部:
  1. parse_intent(query) → intent=diagnostic, scenario=category_analysis
  2. 查找 knowledge/template/{industry}/ 下适用模板
  3. 触发词匹配 + routing 权重排序
  4. 命中 category_health_diagnostic

注入上下文:
  💡 推荐分析模板: 品类健康度综合诊断
  核心指标: 毛利率 + 净利率 + 动销率
  推荐步骤: 数据查询 → 清洗 → 分析 → 热力图 (归因模型可选)
  你可以自定义分析范围，或输入「按模板执行」开始。
```

---

## 七、健康监控

### 7.1 定位

两层监控：

- **48h 快速窗口**（P4 上线）：auto_apply 后立即监控变更相关的 scenario 计数器，异常自动回滚。不依赖基线。
- **周级趋势**（P5 上线）：跨周对比健康指标，回答"系统到底有没有在进步"。需积累 4-8 周基线数据。

Phase 1 期间周级趋势仅收集计数器，不告警。

### 7.2 计数器（`learn/data/counters/{date}.jsonl`）

Session 结束时写入一行聚合数据：

```json
{
  "session": "abc123",
  "date": "2026-05-02",
  "total_queries": 12,
  "l1_hits": 7,
  "l2_hits": 4,
  "l3_fallbacks": 1,
  "plan_validation_failures": 2,
  "corrections": 1,
  "supplements": 1,
  "refinements": 0,
  "errors": 0,
  "by_scenario": {
    "category_analysis": {
      "total": 5,
      "l1_hits": 3,
      "l2_hits": 2,
      "l3_fallbacks": 0,
      "corrections": 1
    },
    "channel_analysis": {
      "total": 4,
      "l1_hits": 2,
      "l2_hits": 2,
      "l3_fallbacks": 0,
      "corrections": 0
    }
  }
}
```

`by_scenario` 按 scenario 拆分计数，为 48h 快速监控提供 per-scenario 粒度数据。仅统计有查询的 scenario（至少 1 条）。

### 7.3 健康指标（P5 实现）

| 指标 | 计算 | 含义 |
|------|------|------|
| L3 率 | l3 / total | 检索质量（越低越好） |
| L1 率 | l1 / total | 精确匹配率（越高越好） |
| 纠正率 | corrections / total | 用户不满意度（越低越好） |

### 7.4 退化自动响应

**两层监控机制：**

**第一层：48h 快速窗口（auto_apply 后立即生效）**

```
每次 auto_apply 执行后:
  1. 将该变更标记为 monitored（记录 target 文件 + 涉及的 scenario）
  2. 启动 48h 窗口，监控该 scenario 的计数器:
     - L3 率（增量 + 绝对值）
     - 纠正率（增量 + 绝对值）
     - 该 scenario 的 L1 命中率
  3. 退化判定（任一条件满足）:
     - L3 率相对变更前上升 >= 5pp（百分点）
     - 纠正率相对变更前上升 >= 5pp
     - L1 率相对变更前下降 >= 10pp
  4. 退化触发时:
     - 立即自动回滚该变更（调用 rollback.py）
     - 标记 hypothesis 状态 = rolled_back
     - 写入 evolution-log 记录退化原因
     - 若 48h 内无退化 → 标记 hypothesis 状态 = stable
  5. 48h 窗口到期时，若该 scenario 零查询:
     - 标记 hypothesis 状态 = stable_insufficient_data（不自动回滚）
     - 原因: 低流量场景下无数据 ≠ 退化
     - P5 周级趋势可跨更长时间窗口覆盖此 case
  6. 48h 窗口关闭后，monitored 标记移除
```

**第二层：周级趋势（P5 实现）**

```
连续 2 周恶化时：暂停 auto_apply → 标记 suspect → 逐条回滚排查 → 无法定位则告警。
```

48h 快速窗口在 P4 即可实现（与 auto_apply 同步上线），不依赖 P5 的周级基线积累。

---

## 八、行业边界

### 8.1 行业相关域

换了行业就要换的东西。进化结果写入行业知识文件。

| 进化对象 | 存储位置 | 进化方式 |
|---------|---------|---------|
| intent 的 keywords | `knowledge/intent-routing.yaml` | correction 聚类 → 补充 keywords |
| intent 的 default_indicators | `knowledge/intent-routing.yaml` | correction 聚类 → 调整默认指标优先级 |
| scenario 的 required_indicators | `knowledge/industry/{ind}/scenarios/*.yaml` | supplement 聚类 → 扩展必选指标 |
| indicator 的 keywords | `knowledge/industry/{ind}/indicators/*.yaml` | L3 聚类 → 补充指标关键词 |
| 分析模板 | `knowledge/template/{ind}/` | 人工定义 → 偏离监控驱动内容更新 |
| 模板路由权重 | `knowledge/template/{ind}/*.yaml` routing 段 | correction 聚类 → 权重自动调整 |

### 8.2 行业通用域

换了行业也不变的东西。进化逻辑本身。

| 对象 | 存储位置 | 说明 |
|------|---------|------|
| 信号检测逻辑 | `learn/scripts/signal_detector.py` | 结构化对比规则，跨行业通用 |
| 信号聚类算法 | `learn/scripts/signal_analyzer.py` | 聚类逻辑通用，按 industry 分组 |
| 验证框架 | `learn/scripts/validator.py` | 回测框架通用 |
| 健康监控 | `learn/scripts/health_check.py` | 健康指标计算通用 |
| 模板格式规范 | `knowledge/template/_base/template_schema.yaml` | 模板的结构定义 |
| 进化配置 | `learn/data/config.yaml` | 阈值、周期、安全边界 |

---

## 九、存储架构

```
learn/
├── scripts/                          # 自进化脚本
│   ├── signal_detector.py            # 多轮纠正检测（Session 结束调用）
│   ├── signal_analyzer.py            # 信号聚类 → 假设生成
│   ├── validator.py                  # 回测验证
│   ├── applier.py                    # 写入知识文件
│   ├── rollback.py                   # 回滚
│   └── health_check.py               # 健康监控
│
├── agents/                           # Agent 定义
│   └── evolution-analyst.md          # 手动触发入口
│
├── data/                             # 数据存储
│   ├── signals/                      # 异常信号（JSONL）
│   │   ├── corrections.jsonl
│   │   ├── supplements.jsonl
│   │   ├── refinements.jsonl
│   │   ├── extensions.jsonl
│   │   ├── l3_fallbacks.jsonl
│   │   ├── l1_misses.jsonl
│   │   └── _index.json
│   │
│   ├── counters/                     # 健康计数器（按天）
│   │   └── {date}.jsonl
│   │
│   ├── hypotheses/                   # 假设存储（YAML）
│   │   └── hyp-{date}-{seq}.yaml
│   │
│   ├── evolution-log/                # 审计追踪
│   │   ├── _index.jsonl
│   │   └── {year}-{month}/
│   │
│   ├── observations/                 # 保留：现有观察记录
│   ├── patterns/                     # 保留：现有模式存储
│   └── instincts/                    # 保留：现有 instinct 存储
│
├── hooks/                            # 保留：现有 hook 脚本
│   ├── load-instincts
│   ├── instinct-apply
│   ├── analyze-observe               # 修改：替换硬编码提取
│   └── session-summary               # 修改：调用 signal_detector + 写 counters
│
└── data/config.yaml                  # 修改：新增 evolution 配置段
```

---

## 十、与现有 Learn 系统的关系

| 现有组件 | 状态 | 说明 |
|---------|------|------|
| `learn/hooks/load-instincts` | 保留 | SessionStart 轻量索引注入 |
| `learn/hooks/instinct-apply` | 保留 | 按需 instinct 匹配，独立能力 |
| `learn/hooks/analyze-observe` | **重写** | 替换硬编码正则 → 记录结构化 observation |
| `learn/hooks/session-summary` | **修改** | 修复触发阈值 + 调用 signal_detector + 写 counters |
| `learn/scripts/instinct-engine.py` | 保留 | 无改动 |
| `learn/agents/pattern-detector.md` | 保留 | 扩展算法，消费 signals 作为额外输入 |
| `learn/data/instincts/` | 保留 | pattern-detector 产出的 instinct 建议 |
| `learn/data/patterns/` | 保留 | pattern 存储 |
| `learn/data/observations/` | 保留 | observation 存储 |

---

## 十一、需要改动的文件

### 新增（7 个）

| 文件 | 说明 | 代码量 |
|------|------|--------|
| `learn/scripts/signal_detector.py` | 结构化对比 + 信号检测 | ~120 行 |
| `learn/scripts/signal_analyzer.py` | 信号聚类 → 假设生成 | ~200 行 |
| `learn/scripts/validator.py` | 回测验证 | ~180 行 |
| `learn/scripts/applier.py` | 写入知识文件 | ~120 行 |
| `learn/scripts/rollback.py` | 回滚机制 | ~80 行 |
| `learn/scripts/health_check.py` | 健康监控 | ~100 行 |
| `knowledge/template/_base/template_schema.yaml` | 模板格式规范 | ~40 行 |

### 修改（5 个）

| 文件 | 改动 | 代码量 |
|------|------|--------|
| `scripts/intent_parser.py` | L3 分支写 l3_fallbacks.jsonl；L1 校验层写 l1_misses.jsonl；返回结构中附加 industry/scenario/template_matched | ~25 行 |
| `learn/hooks/analyze-observe` | 重写：记录结构化 observation | ~60 行 |
| `learn/hooks/session-summary` | 修复触发阈值（全局累计）；调用 signal_detector；写 counters | ~40 行 |
| `learn/data/config.yaml` | 新增 evolution 配置段 | ~20 行 |
| `learn/agents/pattern-detector.md` | 新增信号分析相关算法描述 | ~20 行 |

### 不改

- 所有 skills（12 个）、agents（danalyzer、error-handler）、rules（4 级）、connectors
- `knowledge/industry/fmcg/**/*.yaml` 格式（仅内容通过 applier 修改）
- `knowledge/intent-routing.yaml` 格式（仅内容通过 applier 修改）
- `hooks/session-start`、`hooks/session-routing.md`、`hooks/post-tool-use`

---

## 十二、实施阶段

| 阶段 | 内容 | 核心产出 | 代码量 |
|------|------|---------|--------|
| **P0** | 修复 Learn 现有缺陷（触发阈值、硬编码关键词、行业引用） | Learn 系统可正常工作 | ~30 行 |
| **P1** | 结构化 observation + 多轮纠正检测 (`signal_detector.py`) | 5 类用户反馈信号开始积累 | ~180 行 |
| **P2** | 系统信号埋点 (intent_parser) + 健康计数器 | 系统信号 + counters 有数据 | ~55 行 |
| **P3** | 信号聚类分析 (`signal_analyzer.py`) | 信号 → 结构化假设 | ~200 行 |
| **P4** | 回测验证 + 自动应用 + 回滚 + 48h 快速退化监控 | 假设 → 知识文件更新（闭环完成） + 自动回滚保护 | ~430 行 |
| **P5** | 健康监控 (`health_check.py`) | 系统健康可量化（需 P3-P4 积累基线） | ~100 行 |
| **P6** | 模板体系（路由对齐 + 偏离监控 + 模板沉淀） | 模板三层进化线运作 | ~250 行 |

P0-P2 可并行。P3-P6 串行依赖。

**Phase 1 聚焦范围（P0-P4）：术语纠正 → 关键词/指标调整 + 模板路由对齐 的最短闭环。**

---

## 十三、明确不在 v3 范围内

以下不在 v3 范围内，作为未来扩展方向预留：

- **用户/团队分层**：全局学习，不区分个人或团队
- **LLM 参与信号分类**：分类用确定性规则完成。LLM 预留给未来的假设质量评估
- **可视化偏好学习**：图表类型推荐等
- **模型参数自动调优**：RFM 分位数、预测窗口等
- **数据质量规则自动生成**：已知错误模式积累
- **季节性感知**：618/双11 自动调权
- **指标活跃度衰减**：长期未用指标的自动降权
- **多行业支持**：当前仅 fmcg，架构设计预留了 industry 字段但 Phase 1 不做多行业切换
