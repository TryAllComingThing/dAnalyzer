# learn/agents/pattern-detector.md
---
name: pattern-detector
description: 分析模式检测Agent - 定期扫描观察记录，识别有价值的模式
type: background-agent
trigger: interval (每50次分析或每小时) 或 Stop Hook
---

## 什么是 Pattern Detector？

```
┌─────────────────────────────────────────────────────────────────┐
│                   Pattern Detector Agent                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   输入: learn/data/observations/ (观察记录)                    │
│         ↓                                                       │
│   处理: 模式识别算法                                            │
│         ↓                                                       │
│   输出: learn/data/patterns/ (模式存储)                         │
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

## 执行流程

```
Step 1: 数据加载
  │
  ├── 读取 learn/data/observations/sessions/*.jsonl
  │
  ├── 按会话分组
  │
  └── 统计频次
          │
          ▼
Step 2: 模式检测
  │
  ├── 查询模式检测 (Query Pattern)
  │   └── 重复的查询意图
  │
  ├── 分析模式检测 (Analysis Pattern)
  │   └── 固定的指标+维度组合
  │
  ├── 错误模式检测 (Error Pattern)
  │   └── 重复的错误类型
  │
  └── 行业模式检测 (Industry Pattern)
      └── 行业特定指标发现
          │
          ▼
Step 3: 模式存储
  │
  └── 更新 learn/data/patterns/
          │
          ▼
Step 4: 生成建议
  │
  └── 生成 Instinct 建议到 learn/data/instincts/
```

## 模式检测算法详解

### 1. 查询模式检测 (Query Pattern)

```python
def detect_query_patterns(observations):
    """检测重复的查询意图"""
    # 1. 按自然语言查询分组
    query_groups = group_by(observations, "nl_query")

    # 2. 筛选高频查询 (出现 >= 3次)
    frequent_queries = {
        query: count
        for query, count in query_groups.items()
        if count >= 3
    }

    # 3. 提取共性模式
    patterns = []
    for query, count in frequent_queries.items():
        pattern = extract_pattern(query)
        confidence = min(0.9, 0.5 + count * 0.05)

        patterns.append({
            "type": "query_pattern",
            "pattern": pattern,
            "frequency": count,
            "confidence": confidence,
            "example": query
        })

    return patterns
```

### 2. 分析模式检测 (Analysis Pattern)

```python
def detect_analysis_patterns(observations):
    """检测固定的分析套路"""
    # 1. 提取指标组合
    indicator_combos = group_by(observations, "indicators")

    # 2. 提取维度组合
    dimension_combos = group_by(observations, "dimensions")

    # 3. 找出高共现的组合
    patterns = []
    for combo, count in indicator_combos.items():
        if count >= 5:  # 出现5次以上
            patterns.append({
                "type": "analysis_pattern",
                "indicators": combo,
                "frequency": count,
                "confidence": min(0.85, 0.4 + count * 0.05)
            })

    return patterns
```

### 3. 错误模式检测 (Error Pattern)

```python
def detect_error_patterns(observations):
    """检测重复的错误类型"""
    # 1. 筛选错误类型观察
    errors = [o for o in observations if o.type == "error"]

    # 2. 按错误类型分组
    error_groups = group_by(errors, "error_type")

    # 3. 生成错误模式
    patterns = []
    for error_type, occurrences in error_groups.items():
        if len(occurrences) >= 2:  # 出现2次以上
            patterns.append({
                "type": "error_pattern",
                "error_type": error_type,
                "occurrences": len(occurrences),
                "contexts": extract_contexts(occurrences),
                "solution": lookup_solution(error_type),
                "confidence": min(0.9, 0.5 + len(occurrences) * 0.15)
            })

    return patterns
```

### 4. 行业模式检测 (Industry Pattern)

```python
def detect_industry_patterns(observations):
    """检测行业特定指标"""
    # 1. 按行业分组
    by_industry = group_by(observations, "industry")

    # 2. 统计指标频率
    patterns = []
    for industry, obs_list in by_industry.items():
        indicator_freq = count_indicators(obs_list)

        for indicator, freq in indicator_freq.items():
            if freq >= 3:  # 出现3次以上
                # 检查是否已在配置中
                if not is_in_config(industry, indicator):
                    patterns.append({
                        "type": "industry_pattern",
                        "industry": industry,
                        "indicator": indicator,
                        "frequency": freq,
                        "confidence": min(0.8, 0.4 + freq * 0.08)
                    })

    return patterns
```

## 模式存储格式

```yaml
# learn/data/patterns/analysis/query-patterns.yaml
query_patterns:
  - id: qp-001
    type: query_pattern
    pattern: "销售.*查询"
    frequency: 12
    confidence: 0.85
    recent_sessions: ["s1", "s3", "s5"]
    suggested_insight: "销售查询是高频需求 (12次)，建议预置销售仪表盘"
    suggested_instinct:
      name: sales-query-helper
      trigger:
        type: context_match
        pattern: "销售"
      action: "提供销售相关指标快捷选项"
    created_at: "2026-04-25"

# learn/data/patterns/analysis/error-patterns.yaml
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
      trigger:
        type: error_context
        pattern: "division_by_zero"
      action: "检查除数可能为0时，提示使用 NULLIF"
```

## 触发方式

| 触发方式 | 时机 | 说明 |
|----------|------|------|
| **定时触发** | 每小时或每50次分析 | 后台定期运行 |
| **事件触发** | Stop Hook | 会话结束时检查 |
| **手动触发** | Skill调用 | 用户主动请求 |

## 与 ECC observer.py 的关系

借鉴 ECC 的 `observer.py` 实现，适配 dAnalyzer 分析场景：

| ECC | dAnalyzer Pattern Detector |
|-----|----------------------------|
| 项目级隔离 | 全局 + 行业双维度 |
| 行为模式 | 分析模式 |
| 命令建议 | Instinct 建议 |

---

## 调用方式

```bash
# 手动触发
Skill: pattern-detector

# 在 Stop Hook 中自动触发 (达到阈值时)
```

## 与其他模块的关系

```
Pattern Detector
       │
       ├──▶ learn/data/observations/ (读取)
       │       └── sessions/*.jsonl
       │
       ├──▶ learn/data/patterns/ (写入)
       │       ├── analysis/query-patterns.yaml
       │       ├── analysis/error-patterns.yaml
       │       └── industry/*.yaml
       │
       └──▶ learn/data/instincts/ (生成建议)
               └── suggested_instinct/
```

## 输出示例

```
#[dAnalyzer Pattern Detector] Starting pattern detection...
#[dAnalyzer Pattern Detector] Loaded 150 observations from 12 sessions
#[dAnalyzer Pattern Detector] Detected patterns:
  - Query patterns: 5 (confidence >= 0.6)
  - Analysis patterns: 3 (confidence >= 0.6)
  - Error patterns: 2 (confidence >= 0.7)
  - Industry patterns: 1 (confidence >= 0.6)
#[dAnalyzer Pattern Detector] Generated 4 Instinct suggestions
#[dAnalyzer Pattern Detector] Pattern detection completed
```

---

*参考: ECC observer.py 设计*
*版本: 1.3*
