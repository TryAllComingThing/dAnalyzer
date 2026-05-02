---
name: 上下文管理系统详细设计
description: dAnalyzer 上下文加载、动态注入与按需管理完整设计文档
version: 1.0
date: 2026-04-26
---

# dAnalyzer 上下文管理系统详细设计

## 1. 设计哲学

### 1.1 核心哲学

dAnalyzer 上下文管理系统的核心哲学是**「按需加载 + 分层管理 + 动态注入」**。

| 哲学 | 描述 | 实践方式 |
|------|------|----------|
| **按需加载** | 延迟加载完整内容 | SessionStart 加载索引，按需加载完整内容 |
| **分层管理** | 不同层级不同策略 | 角色/知识/技能/行业/规则 分层管理 |
| **动态注入** | 运行时动态添加 | 根据用户需求动态注入上下文 |
| **上下文控制** | 严格控制总量 | 全程 ~2KB 以内，避免膨胀 |

### 1.2 设计意图

```
传统方案:
  SessionStart 加载所有内容 (~10KB+)
  问题: 上下文膨胀，响应变慢

dAnalyzer 方案:
  SessionStart: 轻量索引 (~100B)
  Skill 执行: 按需加载 (~1-2KB)
  按需注入: 仅注入需要的上下文 (~500B)
  优势: 响应快，精准匹配，动态灵活
```

### 1.3 上下文组成

```
dAnalyzer 完整上下文:

┌─────────────────────────────────────────────────────────────────────┐
│                         dAnalyzer 上下文                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐  │
│  │   角色/灵魂     │    │    学习系统     │    │   Skills 元数据  │  │
│  │   (~500B)      │    │    (~100B)      │    │   (~1KB)        │  │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘  │
│                                                                     │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐  │
│  │   行业知识     │    │    规则索引     │    │   动态注入     │  │
│  │   (按需)       │    │   (~200B)       │    │   (按需)       │  │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘  │
│                                                                     │
│  总计: ~2KB (严格控制)                                            │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 2. 设计原则与理念

### 2.1 核心设计原则

#### 原则 1: 分层加载

```
┌─────────────────────────────────────────────────────────────────┐
│                      分层加载架构                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Layer 1: SessionStart (会话开始)                              │
│  ├─ 角色定义 (role.md) - ~500B                                 │
│  ├─ 核心理念 (soul.md) - ~300B                                 │
│  ├─ 学习索引 (load-instincts) - ~100B                         │
│  └─ Skills 元数据 - ~1KB                                       │
│          │                                                      │
│          ▼                                                      │
│  Layer 2: 技能执行时 (Skill Execution)                         │
│  ├─ 按需加载 SKILL.md - ~5-10KB (仅加载使用的)                │
│  └─ 动态注入行业知识 - ~500B (仅需要的)                        │
│          │                                                      │
│          ▼                                                      │
│  Layer 3: 输出时 (Output)                                      │
│  └─ 安全检查 (security) - ~200B                                │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

#### 原则 2: 索引 + 内容分离

```
❌ 错误: SessionStart 加载完整内容
  - role.md (5KB)
  - soul.md (7KB)
  - 所有 SKILL.md (50KB+)

✅ 正确: 分离索引和内容
  SessionStart: 仅加载索引 (~100B)
  需要时: 动态加载完整内容
```

#### 原则 3: 动态上下文注入

```
用户输入: "查询上月各地区配送时效"
    │
    ▼
判断需要行业知识
    │
    ▼
动态注入:
    - 配送时效指标定义
    - 地区字段映射
    - 时间范围解析
    │
    ▼
生成准确 SQL
```

#### 原则 4: 安全嵌入

```
所有输出必须经过 security 处理:
  data-query → data-analysis → 输出技能 → security → result-formatter
                                                        ↑
                                              脱敏 + 合规 (强制)
```

### 2.2 设计模式

| 模式 | 说明 | 实践 |
|------|------|------|
| **Lazy Load** | 延迟加载 | SKILL.md 仅在需要时读取 |
| **Index** | 索引模式 | SessionStart 加载索引 |
| **Injection** | 动态注入 | 行业知识按需注入 |
| **Layered** | 分层管理 | Session/Skill/Output 分层 |

---

## 3. 上下文组件设计

### 3.1 角色与灵魂 (knowledge/profile/)

**目录结构**:
```
knowledge/profile/
├── role.md     # 角色定位 (~5KB)
└── soul.md    # 核心理念 (~7KB)
```

**role.md 内容**:
```markdown
# dAnalyzer 画像

## 角色定位
资深数据分析师顾问 (10年+ 经验)

## 专业特质
- 专业: 使用规范的数据分析方法
- 精准: 理解数据口径和局限性
- 主动: 主动思考业务含义
- 务实: 关注实际业务价值

## 沟通风格
- 专业但易懂
- 先给结论再给细节
- 主动提供延伸洞察

## 分析偏好
- 趋势分析、对比分析、占比分析
- 基础/标准/深度 三档输出
```

**soul.md 内容**:
```markdown
# dAnalyzer 灵魂

## 核心理念
让数据说话，让洞察发光

## 核心价值观
- 数据第一: 用数据说话
- 业务导向: 分析服务决策
- 主动思考: 不只是执行命令
- 专业谨慎: 知道局限性

## 分析思维链
1. 理解需求
2. 设计分析
3. 解读数据
4. 给出洞察
```

**加载方式**:
```bash
# hooks/session-start 加载
role_content=$(cat "${PLUGIN_ROOT}/knowledge/profile/role.md")
soul_content=$(cat "${PLUGIN_ROOT}/knowledge/profile/soul.md")

# 注入上下文
session_context="<EXTREMELY_IMPORTANT>
你是 dAnalyzer，一位资深数据分析师顾问。

角色定义:
${role_escaped}

核心理念:
${soul_escaped}
</EXTREMELY_IMPORTANT>"
```

**上下文影响**: ~500-800B

### 3.2 Skills 元数据 (skills/)

**目录结构**:
```
skills/
├── data-query/SKILL.md       # 完整指令 (~10KB)
├── data-clean/SKILL.md       # 完整指令 (~8KB)
├── visual/SKILL.md           # 完整指令 (~15KB)
├── report/SKILL.md           # 完整指令 (~8KB)
└── ... (16个 Skills)
```

**元数据内容** (预加载):
```yaml
# AGENTS.md 中的 Skills 列表
skills_metadata:
  - name: data-query
    description: 多数据源查询
    location: skills/data-query/SKILL.md
  
  - name: visual
    description: 可视化技能
    location: skills/visual/SKILL.md
  # ... 16个 Skills
```

**加载方式**:
```python
# danalyzer-core 初始化时加载
def load_skills_metadata():
    return [
        {"name": "data-query", "description": "多数据源查询"},
        {"name": "data-clean", "description": "数据清洗"},
        {"name": "visual", "description": "可视化"},
        # ...
    ]  # ~1KB
```

**按需加载**:
```python
# 当需要执行特定 Skill 时
def load_skill(skill_name):
    skill_path = f"skills/{skill_name}/SKILL.md"
    return read_file(skill_path)  # ~5-15KB
```

**上下文影响**:
- 预加载元数据: ~1KB
- 按需加载 SKILL.md: 5-15KB (仅加载使用的)

### 3.3 行业知识 (knowledge/industry/)

**目录结构**:
```
knowledge/industry/
├── _base/                    # 通用基础配置
│   ├── config.yaml           # 通用设置
│   ├── indicators/           # 通用指标 (6个)
│   └── scenarios/            # 通用场景 (3个)
│
└── ecommerce/                # 电商行业
    ├── config.yaml           # 行业配置
    ├── indicators/           # 行业指标
    ├── scenarios/            # 行业场景
    └── mappings/            # 表映射
```

**检索方式**:
```python
# 使用 context-retriever 或 Python 模块
from scripts.industry import get_store, get_retriever

store = get_store("ecommerce")
retriever = get_retriever(store)

# FTS5 + 向量 + RRF 融合检索
results = retriever.search(
    query="配送时效",
    use_fts=True,
    use_vector=True,
    use_rrf=True
)

# 返回: 指标、表映射、时间范围
```

**注入时机**:
- 用户输入包含行业特征词
- 需要生成 SQL 查询
- 尚未加载行业上下文

**上下文影响**: ~500B (按需注入)

### 3.4 学习系统 (learn/)

**目录结构**:
```
learn/
├── hooks/
│   ├── load-instincts      # SessionStart: 加载索引
│   ├── instinct-apply      # Skill后: 按需匹配
│   ├── analyze-observe     # Skill后: 记录观察
│   └── session-summary     # Stop: 会话总结
│
├── data/
│   ├── instincts/          # Instinct 存储
│   ├── patterns/           # 识别的模式
│   └── observations/       # 观察记录
│
└── scripts/
    └── instinct-engine.py # 匹配引擎
```

**加载方式**:
```bash
# SessionStart: 仅加载索引 (~100B)
$ learn/hooks/load-instincts
#[dAnalyzer Learning] Available instinct types: recommendation, error_learning
#[dAnalyzer Learning] Total instincts: 5
```

**按需匹配** (PostToolUse):
```bash
# Skill 执行后匹配 (~300B)
$ learn/hooks/instinct-apply
#[dAnalyzer Learning] Matched Instincts:
#  • smart-recommendation: 查询补全建议 (confidence: 0.7)
```

**上下文影响**: ~100B (SessionStart) + ~300B (按需匹配)

---

## 4. 执行流程

### 4.1 完整上下文加载流程

```
┌─────────────────────────────────────────────────────────────────────┐
│                    dAnalyzer 上下文加载流程                         │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  1. SessionStart (会话开始)                                        │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │                                                               │ │
│  │  hooks/session-start                                         │ │
│  │    ├─ 加载 role.md (~500B)                                   │ │
│  │    ├─ 加载 soul.md (~300B)                                   │ │
│  │    └─ 构建上下文注入                                          │ │
│  │                                                               │ │
│  │  hooks/load-instincts                                        │ │
│  │    └─ 加载学习索引 (~100B)                                   │ │
│  │                                                               │ │
│  │  danalyzer-core                                               │ │
│  │    └─ 加载 Skills 元数据 (~1KB)                              │ │
│  │                                                               │ │
│  │  上下文总计: ~2KB                                            │ │
│  │                                                               │ │
│  └───────────────────────────────────────────────────────────────┘ │
│                              │                                      │
│                              ▼                                      │
│  2. 用户输入处理                                                   │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │                                                               │ │
│  │  用户: "查询上月各地区配送时效"                               │ │
│  │                                                               │ │
│  │  danalyzer-core: 需求理解                                     │ │
│  │    ├─ 识别行业特征词: "配送时效" → 物流行业                   │ │
│  │    ├─ 判断需要行业知识                                        │ │
│  │    └─ 决策技能组合                                            │ │
│  │                                                               │ │
│  └───────────────────────────────────────────────────────────────┘ │
│                              │                                      │
│                              ▼                                      │
│  3. 按需加载阶段                                                   │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │                                                               │ │
│  │  3.1 加载 context-retriever SKILL.md                         │ │
│  │      └─ ~8KB (仅加载使用的)                                  │ │
│  │                                                               │ │
│  │  3.2 行业知识检索                                            │ │
│  │      ├─ 指标: avg_delivery_time                              │ │
│  │      ├─ 表: delivery_orders                                   │ │
│  │      └─ 字段: duration_hours, region                         │ │
│  │      └─ 注入上下文 (~500B)                                    │ │
│  │                                                               │ │
│  │  3.3 加载 data-query SKILL.md                                │ │
│  │      └─ ~10KB (仅加载使用的)                                  │ │
│  │                                                               │ │
│  └───────────────────────────────────────────────────────────────┘ │
│                              │                                      │
│                              ▼                                      │
│  4. 技能执行                                                       │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │                                                               │ │
│  │  Skill: data-query                                           │ │
│  │    ├─ 使用注入的上下文生成 SQL                                │ │
│  │    └─ 执行查询                                                │ │
│  │                                                               │ │
│  │  Skill: visual                                                │ │
│  │    ├─ 加载 visual SKILL.md (~15KB)                           │ │
│  │    └─ 生成图表                                                │ │
│  │                                                               │ │
│  │  PostToolUse Hooks                                           │ │
│  │    ├─ analyze-observe: 记录观察                               │ │
│  │    └─ instinct-apply: 按需匹配 (~300B)                       │ │
│  │                                                               │ │
│  └───────────────────────────────────────────────────────────────┘ │
│                              │                                      │
│                              ▼                                      │
│  5. 输出阶段                                                       │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │                                                               │ │
│  │  Skill: security                                             │ │
│  │    └─ 脱敏处理 + 合规检查 (~200B)                            │ │
│  │                                                               │ │
│  │  Skill: result-formatter                                     │ │
│  │    └─ 标准化输出                                            │ │
│  │                                                               │ │
│  └───────────────────────────────────────────────────────────────┘ │
│                              │                                      │
│                              ▼                                      │
│  6. Stop Hook                                                     │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │                                                               │ │
│  │  session-summary                                             │ │
│  │    ├─ 会话统计                                               │ │
│  │    └─ 触发模式检测 (可选)                                    │ │
│  │                                                               │ │
│  └───────────────────────────────────────────────────────────────┘ │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 4.2 按需加载决策流程

```
用户输入
    │
    ▼
danalyzer-core 需求理解
    │
    ▼
需要加载 SKILL.md?
    │
    ├─ 是 → 读取 skills/{skill}/SKILL.md
    └─ 否 → 跳过
    │
    ▼
需要行业知识?
    │
    ├─ 是 → 调用 context-retriever
    │      ├─ 检索指标定义
    │      ├─ 检索表映射
    │      └─ 注入上下文 (~500B)
    └─ 否 → 跳过
    │
    ▼
执行技能组合
```

### 4.3 动态注入流程

```
行业知识检索结果:
{
  "indicators": [
    {
      "code": "avg_delivery_time",
      "name": "平均配送时长",
      "formula": "AVG(TIMESTAMPDIFF(HOUR, order_time, delivery_time))",
      "table": "delivery_orders",
      "field": "duration_hours"
    }
  ],
  "mappings": [...],
  "time": {"上月": {"start": "2026-03-01", "end": "2026-03-31"}},
  "dimensions": [...]
}
    │
    ▼
注入到 NL2SQL Prompt:
    │
    ▼
"根据以下指标定义生成 SQL:
- 平均配送时长 (avg_delivery_time): AVG(TIMESTAMPDIFF(HOUR, order_time, delivery_time))
- 表: delivery_orders
- 字段: duration_hours, region, order_time

用户需求: 查询上月各地区配送时效

SQL:
SELECT region, AVG(duration_hours) as avg_delivery_time
FROM delivery_orders
WHERE order_time >= '2026-03-01' AND order_time < '2026-04-01'
GROUP BY region"
```

---

## 5. 与其他模块的协同

### 5.1 与 Hooks 的协同

```
hooks.json 配置:
{
  "hooks": {
    "SessionStart": [
      {
        "matcher": "startup",
        "hooks": [
          { "command": "hooks/run-hook.cmd session-start" },      // 角色/灵魂
          { "command": "learn/hooks/load-instincts" }            // 学习索引
        ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Skill",
        "hooks": [
          { "command": "hooks/run-hook.cmd post-skill-check" }   // 安全检查
        ]
      },
      {
        "matcher": "Skill|Read",
        "hooks": [
          { "command": "learn/hooks/analyze-observe" },          // 记录观察
          { "command": "learn/hooks/instinct-apply" }              // 按需匹配
        ]
      }
    ],
    "Stop": [
      {
        "matcher": "*",
        "hooks": [
          { "command": "learn/hooks/session-summary" }           // 会话总结
        ]
      }
    ]
  }
}
```

### 5.2 与 Agents 的协同

```
danalyzer-core (核心调度器)
    │
    ├─ 初始化时加载:
    │   ├─ Skills 元数据 (~1KB)
    │   └─ Rules 索引 (~200B)
    │
    ├─ 处理请求时:
    │   ├─ 理解用户需求
    │   ├─ 决策技能组合
    │   ├─ 按需加载 SKILL.md
    │   └─ 动态注入上下文
    │
    └─ 调用辅助 Agents:
        ├─ demand-parse (需求拆解)
        ├─ task-planner (任务规划)
        ├─ error-handler (错误处理)
        └─ result-formatter (结果格式化)
```

### 5.3 与 Skills 的协同

```
按需加载 SKILL.md:
  │
  ├─ data-query/SKILL.md      → 生成 SQL
  ├─ context-retriever/SKILL.md → 检索行业知识
  ├─ visual/SKILL.md          → 生成图表
  ├─ report/SKILL.md         → 生成报告
  └─ security/SKILL.md        → 脱敏处理
```

### 5.4 与 Rules 的协同

```
规则层级:
  │
  ├─ legal/ (最高) → 合规检查，触发即中止
  ├─ core/ (高)    → 强制执行
  ├─ base/ (中)    → 建议执行
  └─ dynamic/ (低) → 按需加载

按需加载:
  - 需要数据校验 → 加载 data-quality-check 相关规则
  - 需要指标定义 → 加载 indicator-caliber 规则
```

---

## 6. 上下文控制策略

### 6.1 分层控制

| 阶段 | 加载内容 | 上下文影响 |
|------|---------|-----------|
| SessionStart | 角色/灵魂/学习索引/Skills元数据 | ~2KB |
| Skill执行 | 按需加载 SKILL.md | +5-15KB (仅使用的) |
| 输出 | security 嵌入 | +200B |
| **峰值** | | **~20KB** |
| **有效上下文** | 实际被引用的 | ~2KB |

### 6.2 缓存策略

```python
# SKILL.md 缓存
@lru_cache(maxsize=16)
def load_skill(skill_name):
    """加载并缓存 SKILL.md"""
    return read_file(f"skills/{skill_name}/SKILL.md")

# 行业知识缓存
@lru_cache(maxsize=100)
def search_industry(query, industry):
    """缓存热门行业检索"""
    return retriever.search(query)
```

### 6.3 清理策略

```bash
# 观察记录: 30天自动清理
# 模式存储: 90天自动清理
# 临时缓存: 会话结束清理
```

---

## 7. 与 Claude Code 的集成

### 7.1 加载机制

```
Claude Code 会话启动
    │
    ▼
读取 .claude-plugin/hooks.json
    │
    ▼
SessionStart Hooks 执行
    │
    ├─ hooks/session-start
    │   └─ 注入角色/灵魂上下文
    │
    └─ learn/hooks/load-instincts
        └─ 注入学习索引
    │
    ▼
danalyzer-core 初始化
    │
    └─ 加载 Skills 元数据 (~1KB)
    │
    ▼
用户输入 → 处理 → 输出
    │
    ▼
PostToolUse Hooks 执行
    │
    ├─ 按需加载 SKILL.md
    ├─ 记录观察
    └─ 按需匹配 Instinct
    │
    ▼
Stop Hooks 执行
    │
    └─ 会话总结 + 模式检测
```

### 7.2 环境变量

```bash
# Claude Code 提供
CLAUDE_SESSION_ID=sess_001
CLAUDE_TOOL_NAME=Skill
CLAUDE_TOOL_INPUT="Skill: data-query ..."
CLAUDE_TOOL_RESULT="..."
CLAUDE_PLUGIN_ROOT=/path/to/dAnalyzer
```

### 7.3 上下文注入格式

```xml
<EXTREMELY_IMPORTANT>
你是 dAnalyzer，一位资深数据分析师顾问。

角色定义:
${role_content}

核心理念:
${soul_content}

可用技能:
${skills_metadata}

学习系统索引:
${instincts_index}
</EXTREMELY_IMPORTANT>
```

---

## 8. 方案优势与劣势

### 8.1 方案优势

| 优势 | 说明 | 效果 |
|------|------|------|
| **轻量启动** | SessionStart 仅 ~2KB | 快速响应 |
| **按需加载** | 仅加载需要的 SKILL.md | 控制峰值 |
| **动态注入** | 行业知识按需注入 | 精准匹配 |
| **分层管理** | 不同层级不同策略 | 清晰可控 |
| **安全嵌入** | 输出强制经过 security | 数据安全 |
| **学习增强** | 按需匹配 Instinct | 持续优化 |
| **灵活扩展** | 新增内容不影响启动 | 易于维护 |

### 8.2 方案劣势

| 劣势 | 说明 | 缓解措施 |
|------|------|----------|
| **首次加载延迟** | 首次使用 Skill 有延迟 | 缓存已加载的 |
| **复杂度** | 多层加载逻辑 | 清晰文档 |
| **调试困难** | 动态加载难以追踪 | 增加日志 |
| **缓存管理** | 内存占用需要控制 | LRU 淘汰 |

### 8.3 上下文大小对比

| 设计 | SessionStart | 峰值 | 有效上下文 |
|------|-------------|------|-----------|
| 传统方案 | ~10KB | ~50KB | ~10KB |
| **dAnalyzer** | **~2KB** | **~20KB** | **~2KB** |
| 降低 | **80%** | **60%** | **80%** |

### 8.4 性能指标

| 指标 | 数值 |
|------|------|
| SessionStart 加载 | ~50ms |
| SKILL.md 按需加载 | ~10-50ms |
| 行业知识检索 | < 5ms (FTS5) |
| 上下文注入 | < 5ms |

---

## 9. 扩展设计

### 9.1 新增上下文类型

```python
# 扩展上下文管理器
class ContextManager:
    def register_loader(self, name, loader):
        """注册新的上下文加载器"""
        self.loaders[name] = loader
    
    def load(self, name):
        """加载指定上下文"""
        return self.loaders[name]()

# 示例: 新增多语言支持
context_manager.register_loader("i18n", load_i18n)
```

### 9.2 条件加载规则

```yaml
# context-rules.yaml
load_rules:
  - condition: "industry_specific"
    load: ["industry/{industry}/*"]
  
  - condition: "complex_analysis"
    load: ["model/attribution", "model/forecasting"]
  
  - condition: "report_generation"
    load: ["report/*", "visual/*"]
```

### 9.3 优先级配置

```yaml
# 上下文优先级
priority:
  role: 100       # 最高 - 角色定义
  soul: 90         # 核心理念
  skills: 80       # Skills 元数据
  instincts: 70    # 学习索引
  industry: 60    # 行业知识 (按需)
  rules: 50        # 规则 (按需)
  output: 40       # 安全处理
```

---

## 10. 总结

### 10.1 设计要点

dAnalyzer 上下文管理系统通过以下设计实现轻量、灵活、动态的上下文管理:

1. **分层加载**: SessionStart/Skill执行/输出 三层分离
2. **按需加载**: 仅加载需要的 SKILL.md 和行业知识
3. **动态注入**: 根据用户需求动态注入上下文
4. **严格控制**: 全程 ~2KB 有效上下文
5. **安全嵌入**: 输出强制经过 security

### 10.2 与其他模块的协同

| 模块 | 协同方式 |
|------|----------|
| Hooks | SessionStart/PostToolUse/Stop 触发加载 |
| Agents | danalyzer-core 决策加载时机 |
| Skills | 按需加载 SKILL.md |
| Rules | 按需加载规则文件 |
| Learn | 按需匹配 Instinct |

### 10.3 性能优化

| 指标 | 优化前 | 优化后 |
|------|--------|--------|
| SessionStart | ~10KB | ~2KB |
| 峰值 | ~50KB | ~20KB |
| 响应时间 | ~500ms | ~100ms |

### 10.4 演进方向

- 增加更多上下文类型
- 优化缓存策略
- 添加预加载预测
- 完善监控和日志

---

*本文档于 2026-04-26 创建 (v1.0)*
