---
name: 调度核心设计
description: dAnalyzer 核心调度器架构与执行模型
version: 1.1
date: 2026-04-26
---

# dAnalyzer 调度核心设计

## 1. 设计概述

### 1.1 设计目标

dAnalyzer 调度核心 (danalyzer-core) 是整个系统的唯一执行入口，负责：
- 理解用户数据分析需求
- 自主决策技能组合
- 按需加载技能指令
- 协调多 Agent 协作
- 处理异常并返回结果

### 1.2 核心设计原则

| 原则 | 说明 | 实践 |
|------|------|------|
| **唯一入口** | 所有请求必须经过 danalyzer-core | 不允许绕过直接调用 Skills |
| **按需加载** | 仅在需要时读取 SKILL.md | 元数据预加载，指令按需读取 |
| **自主决策** | Agent 根据需求决定技能组合 | 不预设固定流程，动态组合 |
| **无状态设计** | 不依赖 workflows/ 或 storage/ | 每次请求独立处理 |
| **安全嵌入** | 所有输出必须经过 security | 脱敏+合规强制执行 |

---

## 2. 架构设计

### 2.1 系统架构图

```
                              ┌─────────────────────────────────────┐
                              │          用户输入                    │
                              └─────────────────┬───────────────────┘
                                                │
                                                ▼
                              ┌─────────────────────────────────────┐
                              │       danalyzer-core               │
                              │    (唯一执行入口调度器)              │
                              └─────────────────┬───────────────────┘
                                                │
                ┌───────────────┬───────────────┼───────────────┬───────────────┐
                │               │               │               │               │
                ▼               ▼               ▼               ▼               ▼
         ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐
         │  需求理解  │   │ 需求拆解  │   │ 任务规划  │   │ 技能决策  │   │ 异常处理  │
         │ (内嵌)    │   │ demand   │   │ task     │   │ (内嵌)    │   │ error    │
         │          │   │ -parse   │   │ -planner │   │          │   │ -handler │
         └──────────┘   └──────────┘   └──────────┘   └──────────┘   └──────────┘
                │               │               │               │               │
                └───────────────┴───────────────┼───────────────┴───────────────┘
                                                │
                     ┌──────────────────────────┼──────────────────────────┐
                     │                          │                          │
                     ▼                          ▼                          ▼
              ┌────────────┐             ┌────────────┐             ┌────────────┐
              │ data-query │             │  context   │             │  security  │
              │   skill    │             │ -retriever │             │   skill    │
              └────────────┘             └────────────┘             └────────────┘
                     │                          │                          │
                     └──────────────────────────┼──────────────────────────┘
                                                │
                              ┌─────────────────┴───────────────────┐
                              │         result-formatter            │
                              │        (结果格式化输出)             │
                              └─────────────────────────────────────┘
```

### 2.2 组件职责

| 组件 | 类型 | 职责 |
|------|------|------|
| danalyzer-core | 核心调度器 | 唯一入口，决策调度 |
| demand-parse | 辅助 Agent | 需求拆解，明确目标 |
| task-planner | 辅助 Agent | 任务规划，生成计划 |
| error-handler | 辅助 Agent | 异常处理，策略决策 |
| result-formatter | 辅助 Agent | 结果格式化，标准化输出 |
| Skills | 执行单元 | 具体业务能力 |
| context-retriever | 上下文组件 | 行业知识检索 |

---

## 3. 执行流程

### 3.1 完整执行流程

```
用户输入
    │
    ▼
┌─────────────────────────────────────┐
│ danalyzer-core                      │
│ (唯一执行入口)                      │
└─────────────────┬───────────────────┘
                  │
                  ▼
         ┌─────────────────┐
         │ 1. 需求理解     │
         │ (内嵌)          │
         └────────┬────────┘
                  │
                  ▼
         ┌─────────────────┐
         │ 需求模糊/不明确? │
         └────────┬────────┘
                  │
         ┌────────┴────────┐
         ▼                 ▼
        是                否
         │                 │
         ▼                 ▼
  ┌───────────────┐  ┌─────────────────┐
  │ demand-parse  │  │ 2. 技能决策     │
  │ (调用 Agent)  │  │ (内嵌)          │
  └───────┬───────┘  └────────┬────────┘
          │                    │
          ▼            ┌───────┴───────┐
     获取任务清单       ▼               ▼
     + 确认问题    简单任务        复杂任务
          │        (>2技能?)        (>2技能?)
          │            │               │
          ▼            ▼               ▼
     ┌────┴────┐    否              是
     │用户确认  │    │               │
     └────┬────┘    ▼               ▼
          │   ┌──────────┐   ┌─────────────┐
          │   │ 3.按需  │   │ task-planner│
          │   │ 加载    │   │ (调用 Agent) │
          │   │ Skills  │   └──────┬──────┘
          │   └────┬────┘          │
          │        │          获取执行计划
          │        │          (依赖图+时间估算)
          │        └───────┬───────┘
          │                │
          ▼                ▼
     ┌────────────────────────┐
     │ 4. 执行 & 返回结果       │
     └────────────────────────┘
```

### 3.2 决策规则

| 场景 | demand-parse | task-planner |
|------|--------------|--------------|
| 需求明确 + 任务简单 | ❌ 不调用 | ❌ 不调用 |
| 需求明确 + 任务复杂 | ❌ 不调用 | ✅ 调用 |
| 需求模糊 + 任务简单 | ✅ 调用 | ❌ 不调用 |
| 需求模糊 + 任务复杂 | ✅ 调用 | ✅ 调用 |

**需求模糊判断**:
- 缺少时间范围
- 缺少指标定义
- 缺少输出形式
- 存在多重解释

**任务复杂判断**:
- 技能数量 > 2
- 任务间有依赖
- 涉及多数据源
- 涉及合规/脱敏

---

## 4. 技能组合

### 4.1 技能分类

| 类别 | Skills | 用途 |
|------|--------|------|
| 数据查询 | data-query, query | 多数据源查询 |
| 数据处理 | data-clean, data-quality-check | 清洗与校验 |
| 数据分析 | data-analysis, rfm-analysis, funnel-analysis, model | 分析与建模 |
| 输出 | visual, report, dashboard | 可视化与报告 |
| 安全 | security, compliance | 脱敏与合规 |
| 上下文 | context-retriever | 行业知识检索 |

### 4.2 典型技能组合

| 用户需求 | 技能组合 |
|----------|----------|
| 销售周报 | data-query → data-clean → data-analysis → visual → report → security |
| 用户RFM | data-query → rfm-analysis → visual → security |
| 合规导出 | data-query → compliance → security |
| 漏斗分析 | context-retriever → data-query → funnel-analysis → visual → security |

### 4.3 安全嵌入机制

所有输出流程必须嵌入 security 技能：

```
data-query → data-analysis → 输出技能 → security → result-formatter
                                              ↑
                                      脱敏 + 合规检查 (强制)
```

---

## 5. 上下文检索

### 5.1 设计原理

按需从行业知识库检索相关信息，动态注入上下文：

```
用户输入: "查询上月各地区配送时效"
    │
    ▼
[判断] 需要行业知识?
    ├── 包含行业特征词 ("配送时效"→物流)
    ├── 需要生成 SQL
    └── 尚未加载行业上下文
    ↓ 是
调用 context-retriever (Skill 或 Python 模块)
    │
    ▼
检索结果:
├── 指标定义 (avg_delivery_time)
├── 表映射 (delivery_orders)
├── 时间范围 (2026-03)
└── 维度 (region)
    │
    ▼
注入到目标 Skill 生成 SQL
```

### 5.2 检索方式

| 方式 | 实现 | 性能 |
|------|------|------|
| FTS5 全文检索 | SQLite FTS5 | < 2ms |
| N-gram 向量检索 | Python 标准库 | < 3ms |
| RRF 融合 | 业界标准算法 | 组合排序 |
| 时间衰减 | 越新越重要 | 动态权重 |

---

## 6. 异常处理

### 6.1 错误分类

| 错误类型 | 严重程度 | 示例 | 策略 |
|----------|----------|------|------|
| 取数超时 | 可恢复 | Hive查询超时 | 重试(3次) |
| 数据为空 | 警告 | 查询无结果 | 跳过 |
| 格式错误 | 可恢复 | CSV编码错误 | 重试(1次) |
| 权限不足 | 致命 | 无表权限 | 中止 |
| 规则违规 | 致命 | 敏感数据 | 中止 |

### 6.2 处理策略

| 策略 | 适用场景 | 处理方式 |
|------|---------|---------|
| **重试** | 临时性错误 | 等待后重试，指数退避 |
| **跳过** | 非关键错误 | 记录警告，继续执行 |
| **降级** | 部分数据不可用 | 简化逻辑/备用数据源 |
| **中止** | 致命错误 | 停止执行，报告错误 |

### 6.3 错误处理流程

```
技能执行 (Skill tool)
    │
    ▼
执行成功? ──是──→ 继续下一个技能
    │
    否
    │
    ▼
调用 error-handler
    │
    ▼
error-handler 分析错误
    │
    ▼
┌─────────────────────┬─────────────────────┐
│     可恢复错误       │     不可恢复错误      │
│ (超时/网络/格式)     │ (权限/合规/致命)     │
├─────────────────────┼─────────────────────┤
│ 重试 → 成功?        │ 中止任务             │
│   ├─ 是 → 继续      │ 返回错误报告         │
│   └─ 否 → 跳过      │                      │
└─────────────────────┴─────────────────────┘
```

---

## 7. 组件详解

### 7.1 danalyzer-core

**核心职责**:
- 理解用户需求
- 决策技能组合
- 按需加载 Skills
- 协调执行流程

**关键特性**:
- 唯一执行入口
- 按需加载机制 (元数据预加载 + 指令按需读取)
- 自主决策 (不预设固定流程)
- 安全嵌入 (所有输出强制经过 security)

### 7.2 demand-parse

**触发条件**: 需求模糊、不明确、多意

**输入**: 用户原始需求

**输出**:
```json
{
  "tasks": [
    {"id": 1, "description": "查询销售数据", "skill": "data-query"},
    {"id": 2, "description": "数据清洗", "skill": "data-clean"}
  ],
  "clarifications": [
    {"question": "需要分析哪个时间范围?", "options": ["近7天", "近30天", "自定义"]}
  ]
}
```

### 7.3 task-planner

**触发条件**: 任务复杂 (>2个技能)、有依赖关系

**输入**: 任务清单 + 可用资源 + 约束条件

**输出**:
```json
{
  "execution_plan": [
    {"step": 1, "task": "data-query", "duration": "2min", "dependencies": []},
    {"step": 2, "task": "data-clean", "duration": "1min", "dependencies": [1]},
    {"step": 3, "task": "data-analysis", "duration": "3min", "dependencies": [2]}
  ],
  "total_duration": "6min",
  "parallel_groups": [[1], [2], [3]]
}
```

### 7.4 error-handler

**输入参数**:
- 错误类型 (error_type)
- 错误消息 (error_message)
- 执行上下文 (execution_context)
- 原始请求 (original_request)

**输出**:
```json
{
  "decision": "retry|skip|degrade|abort",
  "max_retries": 3,
  "continue_execution": true,
  "repair_suggestion": "修复建议"
}
```

### 7.5 result-formatter

**核心职责**: 标准化输出格式

**输出格式**:
```json
{
  "success": true,
  "data": {},
  "errors": [],
  "warnings": [],
  "metadata": {}
}
```

---

## 8. 调用示例

### 示例1: 简单需求

```
用户: 查询销售数据并画图

决策:
1. 需求明确 → 跳过 demand-parse
2. 任务简单 → 跳过 task-planner
3. 行业特征 "销售" → 触发 context-retriever

执行流程:
context-retriever → data-query → visual → security → result-formatter
```

### 示例2: 模糊需求

```
用户: 分析销售数据

决策:
1. 需求模糊 → 调用 demand-parse
2. 需确认: 时间范围? 业务线? 核心指标?

用户确认后:
data-query → data-analysis → visual → security → result-formatter
```

### 示例3: 复杂任务

```
用户: 生成电商部门Q1月报

决策:
1. 需求明确 → 跳过 demand-parse
2. 任务复杂 → 调用 task-planner
3. 生成10+步骤执行计划

按计划执行:
data-query(销售) → data-clean → data-analysis
data-query(用户) → rfm-analysis
data-query(渠道) → data-analysis
→ visual → report → security → result-formatter
```

---

## 9. Hooks 集成设计

### 9.1 Hooks 架构概述

dAnalyzer 利用 Claude Code 的 Hooks 系统实现自动化协作，通过事件驱动的方式增强调度核心的能力。

```
┌─────────────────────────────────────────────────────────────────┐
│                     Claude Code 运行环境                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐     │
│  │ SessionStart │    │  PreToolUse  │    │  PostToolUse │     │
│  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘     │
│         │                   │                   │              │
│         ▼                   ▼                   ▼              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐     │
│  │ load-instincts│   │  pre-check   │    │ analyze-    │     │
│  │ session-start │   │  security    │    │ observe     │     │
│  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘     │
│         │                   │                   │              │
│         │                   │                   ▼              │
│         │                   │           ┌──────────────┐       │
│         │                   │           │ instinct-apply│       │
│         │                   │           └──────┬───────┘       │
│         │                   │                   │              │
│         ▼                   ▼                   ▼              │
│  ┌──────────────────────────────────────────────────────┐      │
│  │              hooks.json 配置                          │      │
│  │  • SessionStart: 加载引导 + 知识索引                  │      │
│  │  • PreToolUse: 执行前检查 (Bash/Write/Edit)           │      │
│  │  • PostToolUse: 技能后检查 + 学习系统                  │      │
│  │  • Stop: 会话总结 + 模式检测                           │      │
│  └──────────────────────────────────────────────────────┘      │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │  danalyzer-core  │
                    │   (调度核心)     │
                    └──────────────────┘
```

### 9.2 Hook 类型与职责

| Hook 类型 | 触发时机 | dAnalyzer 职责 | 上下文影响 |
|-----------|----------|----------------|-----------|
| **SessionStart** | 会话开始 | 加载使用指南、角色定义、知识体系 | ~2KB |
| **PreToolUse** | 工具执行前 | 安全检查、权限验证 | 无 |
| **PostToolUse** | 工具执行后 | 技能检查、学习记录、instinct 匹配 | ~300B |
| **Stop** | 会话结束 | 清理、会话总结、模式检测 | 无 |

### 9.3 核心 Hook 脚本

#### 9.3.1 SessionStart Hook

**文件**: `hooks/session-start`

**功能**:
1. 加载 danalyzer-guide 使用指南
2. 加载角色定义 (role.md)
3. 加载核心理念 (soul.md)
4. 加载知识体系 (knowledge.md)

**执行时机**: 会话启动时 (startup/clear/compact)

**输出**: 注入到上下文的角色定义和知识体系

```json
{
  "additionalContext": "<EXTREMELY_IMPORTANT>你是 dAnalyzer，一位资深数据分析师顾问...<\/EXTREMELY_IMPORTANT>"
}
```

#### 9.3.2 PreToolUse Hooks

**配置**:
```json
{
  "matcher": "Bash",
  "hooks": [{ "type": "command", "command": "echo 'dAnalyzer: Pre-execution check'" }]
}
```

**功能**:
- Bash 命令执行前检查
- Write/Edit 文件修改前检查

#### 9.3.3 PostToolUse Hooks

**技能检查 Hook** (`hooks/post-skill-check`):
```json
{
  "matcher": "Skill",
  "hooks": [{ "command": "hooks/run-hook.cmd post-skill-check" }]
}
```

**功能**:
- 检查技能输出是否需要安全处理
- 识别输出类技能 (visual/dashboard/report)

**学习系统 Hooks**:
```json
{
  "matcher": "Skill|Read",
  "hooks": [
    { "command": "learn/hooks/analyze-observe", "async": false },
    { "command": "learn/hooks/instinct-apply", "async": true, "timeout": 10 }
  ]
}
```

**功能**:
- `analyze-observe`: 记录行为观察
- `instinct-apply`: 按需匹配应用建议

#### 9.3.4 Stop Hook

**功能**:
- 会话清理
- 会话总结
- 触发模式检测 (pattern-detector)

### 9.4 学习系统集成

#### 9.4.1 按需匹配设计

```
❌ 旧: SessionStart 加载所有高置信度 Instinct (~1.5KB)

✅ 新:
  - SessionStart: 只加载索引信息 (~100B)
  - PostToolUse: 按需匹配，只返回匹配的建议 (~300B)
```

#### 9.4.2 Hook 流程

```
SessionStart
  └→ load-instincts: 只加载索引 (~100B)

danalyzer-core 执行 Skill
  └→ PostToolUse:
       ├→ analyze-observe: 记录观察
       └→ instinct-apply: 按需匹配
           → 调用 learn/scripts/instinct-engine.py
           → 只返回匹配的建议 (~300B)
```

#### 9.4.3 学习数据流

```
observations/ (原始记录)
      │
      ▼
pattern-detector.md (后台 Agent)
      │
      ▼
patterns/ (识别的模式)
      │
      ▼
instincts/ (应用规则)
      │
      ▼
按需匹配 (Hook)
      │
      ▼
智能建议 (注入上下文)
```

### 9.5 安全集成

#### 9.5.1 安全配置

```json
{
  "security_config": {
    "auto_security": true,
    "output_skills": ["visual", "dashboard", "report", "result-formatter"],
    "scan_on_write": true,
    "block_on_violation": true
  },
  "security_rules": {
    "forbidden_patterns": [
      "\\d{17}[\\dXx]",    // 身份证
      "1[3-9]\\d{9}",      // 手机号
      "\\d{16,19}"         // 银行卡
    ],
    "masking_rules": {
      "phone": "(\\d{3})\\d{4}(\\d{4})",
      "id_card": "(\\d{6})\\d{8}(\\d{4})"
    }
  }
}
```

#### 9.5.2 安全处理流程

```
Skill 输出 (visual/dashboard/report)
    │
    ▼
PostToolUse: post-skill-check
    │
    ▼
扫描敏感数据 (正则匹配)
    │
    ▼
┌─────────────────────────────────────┐
│  发现敏感数据?                       │
├─────────────┬───────────────────────┤
│     是      │         否             │
│     ▼       │         ▼              │
│  数据脱敏    │    继续输出            │
│  合规检查    │                       │
└─────────────┴───────────────────────┘
```

### 9.6 调度核心与 Hooks 协同

#### 9.6.1 协同流程

```
用户输入
    │
    ▼
┌───────────────────────────────────┐
│ SessionStart Hook               │
│ • 加载索引 (load-instincts)      │
│ • 加载知识 (session-start)       │
└───────────────┬───────────────────┘
                │
                ▼
┌───────────────────────────────────┐
│ danalyzer-core                   │
│ • 需求理解                        │
│ • 技能决策                        │
│ • 按需加载 Skills                │
└───────────────┬───────────────────┘
                │
    ┌───────────┴───────────┐
    │                       │
    ▼                       ▼
Skill 执行              Skill 执行
    │                       │
    ▼                       ▼
┌───────────────────────────────────┐
│ PostToolUse Hooks                │
│ • analyze-observe (记录)         │
│ • instinct-apply (智能建议)      │
│ • post-skill-check (安全)        │
└───────────────┬───────────────────┘
                │
                ▼
┌───────────────────────────────────┐
│ 返回结果 + 智能建议              │
└───────────────────────────────────┘
```

#### 9.6.2 上下文影响控制

| 阶段 | 加载内容 | 上下文影响 |
|------|---------|-----------|
| SessionStart | 索引 + 知识索引 | ~100B |
| Skill 执行后 | 匹配的建议 | ~300B |
| 会话结束 | 清理 | 0 |

**设计目标**: 全程上下文控制在 ~2KB 以内

### 9.7 hooks.json 配置详解

```json
{
  "$schema": "https://json.schemastore.org/claude-code-settings.json",
  "hooks": {
    "SessionStart": [
      {
        "matcher": "startup",
        "hooks": [
          { "command": "hooks/run-hook.cmd session-start", "async": false }
        ]
      },
      {
        "matcher": "startup",
        "hooks": [
          { "command": "learn/hooks/load-instincts", "async": false }
        ]
      }
    ],
    "PreToolUse": [
      { "matcher": "Bash", "hooks": [...] },
      { "matcher": "Write|Edit", "hooks": [...] }
    ],
    "PostToolUse": [
      { "matcher": "Skill", "hooks": [...] },
      { "matcher": "Skill|Read", "hooks": [...] },
      { "matcher": "*", "hooks": [...] }
    ],
    "Stop": [
      { "matcher": "*", "hooks": [...] }
    ]
  },
  "security_config": { ... },
  "security_rules": { ... },
  "learning_config": { "enabled": true }
}
```

### 9.8 扩展 Hooks

可根据需要扩展新的 Hooks:

| Hook 场景 | 示例 |
|----------|------|
| 数据源连接 | PreToolUse: 检查数据源权限 |
| SQL 预审 | PreToolUse: SQL 语法检查 |
| 结果缓存 | PostToolUse: 缓存分析结果 |
| 性能监控 | PostToolUse: 记录执行时间 |
| 审计日志 | Stop: 记录完整操作日志 |

---

## 10. 设计特点总结

| 特点 | 说明 | 优势 |
|------|------|------|
| **单一入口** | 统一调度，避免混乱 | 易于追踪和管控 |
| **按需加载** | 延迟加载完整指令 | 减少上下文膨胀 |
| **自主决策** | Agent 决定技能组合 | 灵活性高，适配多场景 |
| **条件触发** | 满足条件才调用辅助 Agent | 避免不必要的开销 |
| **安全嵌入** | 输出强制经过 security | 确保数据安全合规 |
| **上下文感知** | 按需检索行业知识 | 精准生成 SQL/图表 |
| **异常容错** | 多策略处理异常 | 提高系统鲁棒性 |

---

## 10. 与传统工作流引擎对比

| 维度 | 传统工作流引擎 | dAnalyzer 调度核心 |
|------|---------------|-------------------|
| 流程定义 | 预定义 XML/JSON | 运行时动态决策 |
| 节点执行 | 固定节点 | 按需加载 Skill |
| 异常处理 | 预定义分支 | Agent 智能决策 |
| 上下文传递 | 固定变量传递 | 动态注入 |
| 扩展性 | 修改流程定义 | 增加 Skill 即可 |
| 状态管理 | 需要持久化 | 无状态设计 |

---

*本文档于 2026-04-26 创建 (v1.1) - 新增 Hooks 集成设计*
