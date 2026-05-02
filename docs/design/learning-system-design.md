# dAnalyzer 学习与进化系统设计方案

> 版本: 1.3 (修订)
> 设计理念: 借鉴ECC自学习系统，为dAnalyzer打造分析层面的学习进化能力
> 核心定位: 不基于项目/用户，而基于"分析行为"本身的学习系统

---

## 一、设计背景与目标

### 1.1 问题陈述

dAnalyzer 作为通用数据分析Agent，当前存在以下学习缺失：

| 现状 | 问题 | 影响 |
|------|------|------|
| 无行为追踪 | 相同问题被重复询问 | 效率低 |
| 无错误学习 | 分析错误重复发生 | 准确性低 |
| 无模式积累 | 常用分析无法复用 | 重复工作 |
| 无智能推荐 | 无法主动建议分析方向 | 价值有限 |
| 无行业自适应 | 行业指标需要手动配置 | 门槛高 |

### 1.2 设计目标

```
┌─────────────────────────────────────────────────────────────────┐
│                    dAnalyzer 学习系统                            │
│                                                                 │
│  ┌─────────┐   ┌─────────┐   ┌─────────┐                      │
│  │ 行为观察 │ → │ 模式识别 │ → │ 智能应用 │                      │
│  └─────────┘   └─────────┘   └─────────┘                      │
│                                                                 │
│  核心能力:                                                      │
│  • 分析行为追踪  • 错误模式学习  • 行业指标自动发现              │
│  • 智能分析推荐  • 置信度评分                              │
└─────────────────────────────────────────────────────────────────┘
```

**说明**: 模板是dAnalyzer的预设资产（报告模板、可视化模板、分析模型），不需要进化。

### 1.3 与ECC的差异点

| ECC | dAnalyzer |
|-----|-----------|
| 基于项目 (git repo) | 基于分析会话 |
| 项目级隔离 | 全局 + 行业双维度 |
| 用户行为学习 | 分析模式学习 |
| instinct → command | pattern → instinct → 应用 |

---

## 二、系统架构

### 2.1 整体架构

```
                           ┌──────────────────────────────────────┐
                           │         dAnalyzer Core               │
                           │         (分析核心 Agent)             │
                           └──────────────────┬───────────────────┘
                                              │
                      ┌───────────────────────┼───────────────────────┐
                      │                       │                       │
                      ▼                       ▼                       ▼
           ┌──────────────────┐   ┌──────────────────┐   ┌──────────────────┐
           │   行为观察层      │   │   模式识别层      │   │   智能应用层      │
           │   (Hooks)        │   │   (Background)  │   │   (Context)       │
           └────────┬─────────┘   └────────┬─────────┘   └────────┬─────────┘
                    │                       │                       │
         ┌──────────┴──────────┐   ┌────────┴─────────┐   ┌───────┴────────┐
         │                     │   │                  │   │                │
         ▼                     ▼   ▼                  ▼   ▼                ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│ observations/   │  │ patterns/       │  │ instincts/      │  │ 应用效果        │
│ 分析行为记录     │  │ 识别到的模式    │  │ 轻量级应用      │  │ 直接体现        │
└─────────────────┘  └─────────────────┘  └─────────────────┘  └─────────────────┘

         │                     │                  │
         └─────────────────────┴──────────────────┘
                                       │
                                       ▼
                         ┌─────────────────────────┐
                         │      knowledge/learn/     │
                         │      学习数据存储         │
                         └─────────────────────────┘
```

### 2.2 目录结构

```
learn/
├── hooks/                   # Hook 脚本
│   ├── load-instincts     # SessionStart: 加载 Instinct
│   ├── analyze-observe    # PostToolUse: 记录观察
│   └── session-summary    # Stop: 会话总结
│
├── agents/                 # Agent
│   └── pattern-detector.md  # 模式检测 Agent
│
├── scripts/                # 脚本
│   └── instinct-engine.py  # Instinct 引擎
│
├── data/                   # 数据存储
│   ├── observations/       # 观察记录
│   │   ├── sessions/      # 按会话ID组织
│   │   │   └── {session_id}.jsonl
│   │   └── _index.yaml
│   │
│   ├── patterns/          # 识别的模式
│   │   ├── industry/      # 行业模式
│   │   │   ├── ecommerce.yaml
│   │   │   └── ...
│   │   ├── analysis/      # 分析模式
│   │   │   ├── query-patterns.yaml
│   │   │   ├── error-patterns.yaml
│   │   │   └── analysis-patterns.yaml
│   │   └── _index.yaml
│   │
│   ├── instincts/         # Instinct 存储
│   │   ├── recommendation/
│   │   ├── error-learning/
│   │   ├── auto-discovery/
│   │   └── _index.yaml
│   │
│   └── config.yaml        # 学习系统配置
│
└── README.md              # 说明文档
```

---

## 三、核心模块设计

### 3.1 行为观察系统

#### 3.1.1 观察内容

```yaml
# 观察维度
observation_types:
  # 1. 查询行为
  query:
    - natural_language_request  # 自然语言查询
    - generated_sql            # 生成的SQL
    - execution_result         # 执行结果
    - result_summary           # 结果摘要

  # 2. 分析行为
  analysis:
    - analysis_type            # 分析类型
    - indicators_used          # 使用的指标
    - dimensions               # 分析维度
    - insights_generated       # 生成的洞察

  # 3. 输出行为
  output:
    - output_format            # 输出格式
    - visualization_type       # 可视化类型
    - export_action            # 导出行为

  # 4. 错误行为
  error:
    - error_type               # 错误类型
    - error_context            # 错误上下文
    - recovery_action          # 恢复动作
    - is_recovered             # 是否恢复成功

  # 5. 反馈行为
  feedback:
    - user_satisfaction        # 用户满意度
    - follow_up_action         # 跟进行为
    - refinement_request       # 优化请求
```

#### 3.1.2 观察Hook实现

```bash
# hooks/analyze-observe
#!/usr/bin/env bash
# 分析行为观察Hook - PostToolUse触发

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PLUGIN_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# 观察类型
OBSERVE_TYPE="$1"  # query|analysis|output|error|feedback

# 获取工具使用上下文
TOOL_NAME="$CLAUDE_TOOL_NAME"
TOOL_INPUT="$CLAUDE_TOOL_INPUT"
TOOL_RESULT="$CLAUDE_TOOL_RESULT"

# 记录观察
record_observation() {
    local obs_type="$1"
    local session_id="${CLAUDE_SESSION_ID:-default}"
    local timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

    local obs_file="${PLUGIN_ROOT}/knowledge/learn/observations/sessions/${session_id}.jsonl"
    mkdir -p "$(dirname "$obs_file")"

    # 构建观察记录
    cat >> "$obs_file" <<EOF
{"timestamp":"$timestamp","type":"$obs_type","tool":"$TOOL_NAME","session":"$session_id"}
EOF
}

# 根据工具类型判断观察类型
case "$TOOL_NAME" in
    Read|Skill)
        # 检查是否数据查询相关
        if echo "$TOOL_INPUT" | grep -q "data-query\|query\|SQL"; then
            record_observation "query"
        fi
        ;;
    *)
        ;;
esac

exit 0
```

### 3.2 模式识别系统 (Pattern Detector)

#### 3.2.1 ECC中的类似模块

ECC的自学习系统中，`observer.py` 就是 Pattern Detector 的原型：

```
ECC 架构:
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│  ┌─────────────┐    定期触发    ┌─────────────┐               │
│  │ observe.sh  │ ──────────▶   │ observer.py │               │
│  │   (Hook)    │  观察数据      │  (后台Agent)│               │
│  └─────────────┘                └──────┬──────┘               │
│                                        │                       │
│                                        ▼                       │
│                               ┌──────────────┐                 │
│                               │ instincts/   │                 │
│                               │ 目录         │                 │
│                               └──────────────┘                 │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

ECC observer.py 核心逻辑：

```python
# ECC observer.py 核心逻辑
class ObserverAgent:
    def analyze(self):
        # 1. 加载最近观察
        observations = load_recent_observations()

        # 2. 按项目分组
        by_project = group_by_project(observations)

        # 3. 检测重复模式
        patterns = detect_repeating_patterns(by_project)

        # 4. 检查已有instinct
        existing = match_existing_instincts(patterns)

        # 5. 生成新instinct建议
        return generate_instinct_suggestions(patterns, existing)
```

**结论**：ECC已有类似模块，dAnalyzer借鉴并适配到分析场景。

#### 3.2.2 Pattern Detector 设计

```markdown
# agents/pattern-detector.md
---
name: pattern-detector
description: 分析模式检测Agent - 后台运行，识别分析行为模式
type: background-agent
trigger: interval (每50次分析或每小时)
---

## 什么是 Pattern Detector？

```
┌─────────────────────────────────────────────────────────────────┐
│                   Pattern Detector Agent                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   输入: 观察记录 (observations)                                 │
│         ↓                                                       │
│   处理: 模式识别算法                                            │
│         ↓                                                       │
│   输出: 识别的模式 (patterns)                                   │
│         ↓                                                       │
│   交付: Instinct建议 / 行业配置建议                            │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## 职责

1. **加载观察数据** - 读取最近的观察记录
2. **模式检测** - 执行4类模式识别算法
3. **模式存储** - 更新 patterns/ 目录
4. **生成建议** - 输出 Instinct 创建建议

## 执行逻辑

### 1. 数据加载
- 读取最近N天的观察记录
- 按类型 (query/analysis/error) 分组
- 统计频次和共现关系

### 2. 模式检测算法

| 算法 | 输入 | 输出 |
|------|------|------|
| 查询模式检测 | 自然语言查询 | 重复查询意图 |
| 分析模式检测 | 指标组合 | 固定分析套路 |
| 错误模式检测 | 错误记录 | 重复错误类型 |
| 行业模式检测 | 行业上下文 | 新指标发现 |

### 3. 模式存储
- 更新 `patterns/` 目录
- 生成模式索引

### 4. 生成建议
- 筛选高价值模式 (frequency >= threshold)
- 生成 Instinct 创建建议
- 生成行业配置更新建议
```

#### 3.2.3 模式检测算法详解

##### 3.2.3.1 查询模式检测

```python
# 伪代码
def detect_query_patterns(observations):
    # 1. 向量化
    embeddings = embed([o.natural_language for o in observations])

    # 2. 相似度矩阵
    similarity_matrix = cosine_similarity(embeddings)

    # 3. 聚类 (相似查询为一组)
    clusters = cluster(similarity_matrix, threshold=0.8)

    # 4. 提取模式
    patterns = []
    for cluster in clusters:
        if len(cluster) >= 3:  # 出现3次以上
            pattern = {
                "type": "query_pattern",
                "pattern": extract_common_intent(cluster),
                "frequency": len(cluster),
                "confidence": calculate_confidence(cluster),
                "suggested_action": generate_suggestion(cluster)
            }
            patterns.append(pattern)

    return patterns
```

##### 3.2.3.2 分析模式检测

```python
def detect_analysis_patterns(observations):
    # 1. 构建指标共现矩阵
    cooccurrence = build_cooccurrence_matrix(observations)

    # 2. 发现固定组合 (高共现率)
    fixed_combinations = find_high_cooccurrence(cooccurrence, threshold=0.7)

    # 3. 识别分析套路
    patterns = []
    for combo in fixed_combinations:
        pattern = {
            "type": "analysis_pattern",
            "indicators": combo.indicators,
            "dimensions": combo.dimensions,
            "frequency": combo.count,
            "example": combo.example_queries,
            "confidence": combo.confidence
        }
        patterns.append(pattern)

    return patterns
```

##### 3.2.3.3 错误模式检测

```python
def detect_error_patterns(observations):
    errors = filter_by_type(observations, "error")

    # 1. 按错误类型分组
    error_groups = group_by(errors, "error_type")

    patterns = []
    for error_type, occurrences in error_groups.items():
        if len(occurrences) >= 2:  # 出现2次以上
            pattern = {
                "type": "error_pattern",
                "error_type": error_type,
                "occurrences": len(occurrences),
                "contexts": extract_contexts(occurrences),
                "solution": lookup_solution(error_type),
                "prevention_hint": generate_hint(error_type),
                "confidence": min(0.9, 0.5 + len(occurrences) * 0.1)
            }
            patterns.append(pattern)

    return patterns
```

##### 3.2.3.4 行业模式检测

```python
def detect_industry_patterns(observations):
    # 按行业分组
    by_industry = group_by(observations, "industry")

    patterns = []
    for industry, obs_list in by_industry.items():
        # 统计指标频率
        indicator_freq = count_indicators(obs_list)

        # 发现高频指标
        for indicator, freq in indicator_freq.items():
            if freq >= 3:  # 出现3次以上
                # 检查是否已在行业配置中
                if not is_in_config(industry, indicator):
                    patterns.append({
                        "type": "industry_pattern",
                        "industry": industry,
                        "indicator": indicator,
                        "frequency": freq,
                        "confidence": min(0.8, 0.4 + freq * 0.1),
                        "suggested_action": f"添加到{industry}行业指标"
                    })

    return patterns
```

#### 3.2.4 模式类型定义

```yaml
# 模式定义
pattern_types:
  # 1. 查询模式 (Query Pattern)
  query_pattern:
    description: "重复的查询意图"
    example:
      - "查销售额" (多次出现)
      - "上月 vs 本月" (固定对比)
    detection:
      threshold: 3  # 出现3次以上识别
      similarity: 0.8  # 相似度阈值

  # 2. 分析模式 (Analysis Pattern)
  analysis_pattern:
    description: "常用的分析套路"
    example:
      - "趋势 + 环比 + Top N"
      - "转化漏斗"
    detection:
      threshold: 5
      co_occurrence: 0.7  # 共现率

  # 3. 错误模式 (Error Pattern)
  error_pattern:
    description: "重复的错误类型"
    example:
      - "SQL语法错误: 字段名错误"
      - "数据口径不一致"
    detection:
      threshold: 2

  # 4. 行业指标模式 (Industry Pattern)
  industry_pattern:
    description: "行业特定指标发现"
    detection:
      frequency: 3  # 出现频率
      industry_context: true  # 需要行业上下文
```

#### 3.2.5 触发时机

| 触发方式 | 时机 | 说明 |
|----------|------|------|
| **定时触发** | 每小时或每50次分析 | 后台定期运行 |
| **事件触发** | Stop Hook | 会话结束时检查 |
| **手动触发** | Skill调用 | 用户主动请求 |

**推荐**: 定时 + 事件双触发

---

### 3.3 智能应用系统

#### 3.3.1 Instinct机制

借鉴ECC的instinct概念，但适配dAnalyzer的分析场景：

```yaml
# instincts/recommendation.yaml
---
name: smart-recommendation
description: 智能推荐 - 基于历史分析模式主动推荐
confidence: 0.7
trigger:
  type: context_match
  pattern: "query_pattern"
---

# 应用逻辑

当检测到用户查询模式匹配已知模式时:

1. **查询补全**
   ```
   用户: "查销售"
   → 建议: "您可能想查询: 销售额/销售量/销售趋势"
   ```

2. **延伸分析**
   ```
   用户: "查本月销售额"
   → 建议: "是否需要: 环比对比 | 区域分布 | Top产品"
   ```

3. **历史参考**
   ```
   用户: 重复查询
   → 上次分析结果: [链接]
   ```

#### 3.3.2 自动发现Instinct

```yaml
# instincts/auto-discovery.yaml
---
name: industry-indicator-discovery
description: 自动发现行业特定指标
confidence: 0.6
trigger:
  type: frequency
  threshold: 5
---

# 应用逻辑

当某指标在行业上下文中频繁出现:
1. 提取指标名称和上下文
2. 检查是否已在行业配置中
3. 若不存在，生成添加建议
4. 更新行业指标索引
```

#### 3.3.3 错误学习Instinct

```yaml
# instincts/error-learning.yaml
---
name: error-avoidance
description: 错误规避 - 从历史错误中学习
confidence: 0.8
trigger:
  type: error_context
  pattern: "error_pattern"
---

# 应用逻辑

当检测到可能的错误模式:
1. 匹配已知错误模式
2. 给出预防建议
3. 提供修复方案

示例:
用户查询涉及: "字段A / 字段B"
→ 提示: "注意: 之前发现除零错误，建议使用 NULLIF"
```

---

## 四、与现有架构的结合

### 4.1 完整数据流

```
┌─────────────────────────────────────────────────────────────────┐
│                      数据流                                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Step 1: 观察记录                                                │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ PostToolUse Hook                                         │   │
│  │   → 写入 observations/sessions/{id}.jsonl               │   │
│  └─────────────────────────────────────────────────────────┘   │
│                           │                                    │
│                           ▼                                    │
│  Step 2: 模式检测                                                │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ Pattern Detector (后台)                                  │   │
│  │   → 读取 observations/                                   │   │
│  │   → 检测模式                                             │   │
│  │   → 写入 patterns/                                       │   │
│  └─────────────────────────────────────────────────────────┘   │
│                           │                                    │
│                           ▼                                    │
│  Step 3: Instinct 生成                                           │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ Pattern Detector                                         │   │
│  │   → 读取 patterns/                                       │   │
│  │   → 生成 Instinct 建议                                   │   │
│  │   → 写入 instincts/                                      │   │
│  └─────────────────────────────────────────────────────────┘   │
│                           │                                    │
│                           ▼                                    │
│  Step 4: 智能应用                                                │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ PreToolUse Hook                                         │   │
│  │   → 读取 instincts/                                      │   │
│  │   → 匹配当前上下文                                      │   │
│  │   → 注入建议到上下文                                    │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 4.2 在dAnalyzer执行流程中的位置

```
用户输入
    │
    ▼
┌──────────────────────────────────────────────────────────────┐
│              danalyzer-core (执行入口)                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │ 需求理解    │→ │ 技能决策    │→ │ 执行技能   │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
└────────────────────────┬───────────────────────────────────────┘
                         │
            ┌────────────┼────────────┐
            │            │            │
            ▼            ▼            ▼
┌─────────────────┐ ┌──────────┐ ┌─────────────┐
│ PostToolUse     │ │ Skill    │ │ PreToolUse │
│ Hook            │ │ 调用     │ │ Hook       │
│ (观察记录)      │ │          │ │ (智能注入)  │
└────────┬────────┘ └────┬─────┘ └─────┬──────┘
         │               │             │
         ▼               │             │
┌─────────────────┐     │             │
│ Pattern         │     │             │
│ Detector        │ ◀───┘             │
│ (后台运行)       │                   │
└────────┬────────┘                   │
         │                           │
         ▼                           │
┌─────────────────┐                 │
│ patterns/       │                 │
│ instincts/     │ ◀───────────────┘
└─────────────────┘
```

### 4.3 Instinct应用方式 (不使用PreToolUse Hook)

> ⚠️ 重要说明：不使用 PreToolUse Hook 注入 Instinct，因为这会干扰 Skill 的正常执行。

#### 分层设计方案

```
Layer 1: SessionStart (加载全局指导)
  │
  └→ 加载高置信度(≥0.8)的 Instinct
     作为系统级指导原则
     (不影响 Skill 执行，只作为背景知识)

Layer 2: danalyzer-core (执行后附加建议)
  │
  └→ Skill 执行后，检查是否有匹配的 Instinct
     以"智能建议"形式附加在结果中
     (不干扰 Skill 本身，只提供延伸信息)

Layer 3: 定时检测 (后台模式识别)
  │
  └→ Pattern Detector 后台运行
     定期扫描观察数据，生成新模式
```

#### 与Hook的集成

| 集成点 | 作用 | 说明 |
|--------|------|------|
| **SessionStart** | 加载高置信度 Instinct | 作为系统级指导，不干扰 Skill |
| **PostToolUse** | 记录分析行为 | 写入 observations/ |
| **Stop** | 会话总结 | 触发 Pattern Detector |

| 不使用 | 原因 |
|--------|------|
| **PreToolUse Hook** | 会干扰 Skill 执行的上下文，导致行为不确定 |

### 4.4 执行流程示例

```
用户: "查销售额"
    │
    ▼
danalyzer-core 执行分析
    │
    ├── 技能决策: data-query → visual
    │
    ├── 执行 Skill (data-query)
    │
    ├── 获取查询结果
    │
    ├── 【新增】检查匹配的 Instinct
    │   (从 instincts/ 加载，匹配当前上下文)
    │
    └── 返回结果 + 智能建议
        │
        ▼
返回:
"销售额查询结果: 100万

💡 智能建议:
- 您可能还需要: 环比对比 (+15%采纳)
- 华东区域增长显著，建议关注"
```

---

## 五、技术实现

### 5.1 Hook配置

```json
// .claude-plugin/hooks.json 更新
{
  "hooks": {
    "SessionStart": [
      {
        "hooks": ["learn/hooks/load-instincts"]
      }
    ],
    "PostToolUse": [
      {
        "matchers": ["Skill", "Read"],
        "hooks": ["learn/hooks/analyze-observe"]
      }
    ],
    "Stop": [
      {
        "hooks": ["learn/hooks/session-summary"]
      }
    ]
  }
}
```

#### 配置说明

| Hook | 作用 |
|------|------|
| **SessionStart** | 加载高置信度 Instinct 作为系统级指导 |
| **PostToolUse** | 记录分析行为到 learn/data/observations/ |
| **Stop** | 会话总结，触发 Pattern Detector |

#### 为什么不用 PreToolUse

```
PreToolUse Hook 的问题:
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│  用户输入                                                        │
│      │                                                          │
│      ▼                                                          │
│  danalyzer-core 决策: 使用 data-query                           │
│      │                                                          │
│      ▼                                                          │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  PreToolUse Hook                                        │   │
│  │  (在 data-query 执行前)                                 │   │
│  │                                                           │   │
│  │  ⚠️ 问题:                                                │   │
│  │  - 注入的内容污染 Skill 的输入上下文                     │   │
│  │  - Skill 不知道为何突然多了额外指令                      │   │
│  │  - 可能导致执行结果不符合预期                            │   │
│  └─────────────────────────────────────────────────────────┘   │
│      │                                                          │
│      ▼                                                          │
│  Skill 执行 (结果可能已被污染)                                  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 5.2 观察数据Schema

```json
// observations/sessions/{session_id}.jsonl
{
  "timestamp": "2026-04-25T10:30:00Z",
  "type": "query|analysis|output|error|feedback",
  "session_id": "xxx",
  "data": {
    "natural_language": "查本月销售额",
    "generated_sql": "SELECT SUM(sales) FROM ...",
    "industry": "ecommerce",
    "indicators": ["sales_amount", "sales_growth"],
    "dimensions": ["month", "region"],
    "output_format": "chart",
    "error_type": null,
    "recovery": null
  }
}
```

### 5.3 模式数据结构

```yaml
# patterns/analysis/query-patterns.yaml
query_patterns:
  - id: qp-001
    type: query_pattern
    pattern: "销售.*查询"
    frequency: 12
    confidence: 0.85
    recent_sessions: ["s1", "s3", "s5", "s8"]
    suggested_insight: |
      销售查询是高频需求 (12次)，建议:
      - 预置销售仪表盘
      - 添加销售趋势分析
    suggested_instinct:
      name: sales-query-helper
      trigger: "销售" in query
      action: "提供销售相关指标快捷选项"
    created_at: "2026-04-20"
    updated_at: "2026-04-25"

  - id: qp-002
    type: query_pattern
    pattern: ".*对比.*"
    frequency: 8
    confidence: 0.72
    variations: ["环比", "同比", "区域对比", "产品对比"]
    suggested_action: "comparison-recommendation"

# patterns/analysis/error-patterns.yaml
error_patterns:
  - id: ep-001
    type: error_pattern
    pattern: "除零错误"
    occurrences: 3
    confidence: 0.9
    contexts:
      - "毛利率 = 毛利/销售额"
      - "转化率 = 订单数/访客数"
    solution: "使用 NULLIF 避免除零"
    prevention_hint: "检测到除法运算符时自动提示使用 NULLIF"
    suggested_instinct:
      name: division-safety
      trigger: "/" in generated_sql
      action: "检查除数可能为0时，提示使用 NULLIF"
```

### 5.4 Instinct执行

```python
# scripts/learn/instinct-engine.py
class InstinctEngine:
    def __init__(self, instinct_dir):
        self.instincts = self.load_instincts(instinct_dir)

    def match(self, context):
        """匹配当前上下文"""
        matched = []
        for instinct in self.instincts:
            if self._match_trigger(context, instinct.trigger):
                instinct.score = self._calculate_confidence(context, instinct)
                matched.append(instinct)
        return sorted(matched, key=lambda x: x.score, reverse=True)

    def apply(self, instinct, context):
        """应用匹配的instinct"""
        return instinct.apply(context)
```

---

## 六、预期效果

### 6.1 效果量化

| 能力 | 预期效果 | 衡量指标 |
|------|----------|----------|
| **模式发现率** | > 10条/周 | 每周识别的新模式 |
| **模式准确率** | > 80% | 经人工确认正确的比例 |
| **行为追踪** | 完整记录分析过程 | 观察覆盖率 > 95% |
| **错误学习** | 错误重复率降低 | 错误率下降 60% |
| **智能推荐** | 主动提供相关分析 | 推荐采纳率 > 40% |
| **自动发现** | 行业指标自动补充 | 新指标发现率 > 10% |
| **效率提升** | 减少重复分析 | 分析效率提升 50% |

### 6.2 用户体验

#### 场景1: 重复查询
```
用户: "查销售额"
系统: [查询 + 结果]

用户: "再查一下"
系统: [检测到重复查询]
    → "您上次查询了'销售额'，是否需要：
       1. 复制上次查询
       2. 查看同期对比
       3. 添加时间筛选"
```

#### 场景2: 错误预防
```
用户: "计算毛利率"
系统: [检测到除法运算]
    → "提示: 毛利率 = 毛利/销售额，建议使用 NULLIF
       防止除零错误"
```

#### 场景3: 智能延伸
```
用户: "查本月销售"
系统: [执行查询]
    → "基于您的查询，提供以下延伸分析：
       📈 趋势: 连续3个月上升
       🏆 Top: 销售Top3产品
       📊 分布: 区域销售占比
       建议: 华东区环比增长15%，值得关注"
```

#### 场景4: 行业适应
```
用户: [在电商场景查询客单价]
系统: [检测到电商行业]
    → [自动加载电商行业指标]
    → "已识别为电商场景，自动启用:
       客单价、转化率、复购率等电商指标"
```

### 6.3 学习效果展示

```
┌─────────────────────────────────────────────────────────────────┐
│                      dAnalyzer 学习看板                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  📊 本月学习统计                                                 │
│  ┌─────────────┬─────────────┬─────────────┬─────────────┐      │
│  │ 观察记录   │ 识别模式    │ 生效Instinct │ 采纳建议    │      │
│  │   1,247   │     23     │      8      │     156    │      │
│  └─────────────┴─────────────┴─────────────┴─────────────┘      │
│                                                                 │
│  🔥 检测到的模式:                                                │
│                                                                 │
│  📊 查询模式 (5个)                                              │
│     • "销售" 查询 - 12次 → 建议预置销售看板                    │
│     • "转化" 分析 - 8次  → 建议添加转化漏斗                    │
│     • "区域" 对比 - 6次  → 建议添加区域维度                    │
│                                                                 │
│  ⚠️ 错误模式 (2个)                                              │
│     • 除零错误 - 3次  → NULLIF防护已启用                        │
│     • 字段缺失 - 2次  → 自动补全已启用                          │
│                                                                 │
│  🏭 行业模式 (1个)                                              │
│     • 电商: 客单价 - 5次 → 建议添加到电商指标                  │
│                                                                 │
│  ✨ 生成的Instinct (3个)                                        │
│     • smart-recommendation (置信度 0.85)                       │
│     • error-avoidance (置信度 0.90)                            │
│     • industry-discovery (置信度 0.65)                         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 七、实施计划

### 7.1 实施阶段

```
Phase 1: 基础观察 (Week 1-2)
├── Hooks配置
├── 观察数据收集
└── 基础存储结构

Phase 2: 模式检测 (Week 3-4)
├── Pattern Detector Agent
├── 模式数据结构
└── 模式索引

Phase 3: 智能应用 (Week 5-6)
├── Instinct Engine
├── 推荐系统
└── 错误学习
```

### 7.2 文件清单

| 阶段 | 文件 | 说明 |
|------|------|------|
| 1 | `learn/hooks/session-start` (现有) | SessionStart加载Instinct |
| 1 | `learn/hooks/analyze-observe` | 观察Hook (新增) |
| 1 | `learn/hooks/session-summary` | 会话总结Hook (新增) |
| 1 | `learn/data/observations/` | 观察存储 |
| 1 | `learn/data/config.yaml` | 学习配置 |
| 2 | `learn/agents/pattern-detector.md` | 模式检测Agent |
| 2 | `learn/data/patterns/` | 模式存储 |
| 3 | `learn/scripts/instinct-engine.py` | Instinct引擎 |
| 3 | `learn/data/instincts/` | Instinct存储 |

---

## 八、总结

本方案借鉴ECC的自学习系统，为dAnalyzer打造了分析层面的学习能力：

| 核心设计 | 说明 |
|----------|------|
| **行为观察** | 全量追踪分析过程 |
| **Pattern Detector** | 后台模式识别 (借鉴ECC observer.py) |
| **模式识别** | 自动发现4类模式 (查询/分析/错误/行业) |
| **智能应用** | 基于模式的主动建议 (Instinct) |
| **错误学习** | 从错误中学习预防 |
| **行业适应** | 自动发现行业指标 |

**与现有架构结合**:
- SessionStart: 加载高置信度 Instinct 作为系统级指导
- PostToolUse Hook: 记录观察
- Stop Hook: 触发模式检测
- danalyzer-core集成: Skill执行后附加智能建议

**Instinct应用方式** (不使用PreToolUse):
- SessionStart: 加载高置信度(≥0.8) Instinct
- danalyzer-core: Skill执行后以"建议"形式返回
- 原因: PreToolUse Hook会干扰Skill执行的上下文

**不涉及模板进化**：模板（报告模板、可视化模板、分析模型）是dAnalyzer的预设资产，不需要进化。

预期效果：
- 模式发现率 > 10条/周
- 错误率降低 60%
- 智能推荐采纳率 > 40%
- 行业指标自动发现 > 10%

---

*方案版本: 1.3*
*设计参考: ECC自学习系统 (observer.py)*
*最后更新: 2026-04-25*
