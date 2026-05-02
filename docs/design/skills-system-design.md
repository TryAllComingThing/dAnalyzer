---
name: Skills 系统详细设计
description: dAnalyzer 技能系统完整设计文档
version: 1.0
date: 2026-04-26
---

# dAnalyzer Skills 系统详细设计

## 1. 设计哲学

### 1.1 核心哲学

dAnalyzer Skills 系统的核心哲学是**「按需加载 + 模块化 + 安全嵌入」**。

| 哲学 | 描述 | 实践方式 |
|------|------|----------|
| **按需加载** | SKILL.md 仅在需要时读取 | 元数据预加载，完整指令延迟加载 |
| **模块化设计** | 每个 Skill 专注单一功能 | 高内聚、低耦合 |
| **安全嵌入** | 输出必须经过 security | 脱敏+合规强制执行 |
| **技能组合** | 根据需求动态组合 | Agent 自主决策调用链 |
| **无状态** | 每个 Skill 独立可调用 | 不依赖持久化状态 |

### 1.2 设计意图

```
传统数据分析系统:
  用户 → 固定流程 → 数据清洗 → 分析 → 可视化 → 输出
  问题: 流程固化，无法灵活适配多场景

dAnalyzer Skills:
  用户 → 需求理解 → 技能决策 → 按需组合 → 安全输出
  优势: 动态组合，按需加载，灵活安全
```

### 1.3 Skill 与 Agent 的关系

```
Agent (调度决策):
  └─ danalyzer-core: 唯一入口，负责决策调用哪些 Skills
  └─ demand-parse: 需求拆解
  └─ task-planner: 任务规划

Skill (执行单元):
  └─ data-query: 数据查询
  └─ data-clean: 数据清洗
  └─ data-analysis: 数据分析
  └─ visual: 可视化
  └─ security: 安全脱敏
  └─ ... (共16个技能)

关系:
  - Agent 负责"何时调用"和"调用什么"
  - Skill 负责"具体执行"
  - Agent 调用 Skill 工具执行任务
```

---

## 2. 设计原则与理念

### 2.1 核心设计原则

#### 原则 1: 单一职责

```
✅ 正确:
  data-query: 只负责查询
  data-clean: 只负责清洗
  visual: 只负责可视化

❌ 错误:
  一个 Skill 做了所有事情
```

#### 原则 2: 按需激活

```
Skill 激活条件:
  - 用户需求匹配
  - 上游 Skill 输出需要进一步处理
  - 需要特定能力时显式调用
```

#### 原则 3: 安全嵌入

```
输出流程 (强制):
  data-query → data-analysis → 输出技能 → security → result-formatter
                                                      ↑
                                              脱敏 + 合规 (强制)
```

#### 原则 4: 灵活组合

```
不同场景，技能组合不同:
  简单查询: data-query → visual → security
  完整分析: data-query → data-clean → data-analysis → visual → security
  RFM分析: data-query → rfm-analysis → visual → security
  漏斗分析: context-retriever → data-query → funnel-analysis → visual → security
```

### 2.2 Skill 设计模式

| 模式 | 说明 | 示例 |
|------|------|------|
| **Tool Wrapper** | 包装一个工具能力 | data-query, visual |
| **Multi-step** | 多步骤执行 | data-clean, model |
| **Reviewer** | 审核校验 | data-quality-check |
| **Aggregator** | 聚合多个子技能 | dashboard, report |
| **Specialized** | 专业分析能力 | rfm-analysis, funnel-analysis |

---

## 3. Skills 组件设计

### 3.1 Skills 目录结构

```
skills/
├── danalyzer-guide/       # 入门引导
├── data-query/            # 数据查询
├── data-clean/            # 数据清洗
├── data-quality-check/   # 数据校验 (Reviewer)
├── data-analysis/        # 数据分析
├── model/                # 数据建模
├── rfm-analysis/         # RFM分析 (专业)
├── funnel-analysis/      # 漏斗分析 (专业)
├── visual/               # 可视化
├── query/                # 高级查询
├── report/               # 报告生成
├── dashboard/            # 仪表盘
├── security/             # 安全脱敏
├── compliance/           # 合规检查
├── context-retriever/    # 上下文检索
└── insight-gen/          # 洞察生成
```

### 3.2 Skill 详细设计

#### 3.2.1 数据查询类 Skills

##### data-query (数据查询)

**定位**: 基础数据查询能力

**核心能力**:
- 自然语言转 SQL (NL2SQL)
- 多数据源支持 (Hive/ClickHouse/MySQL/Excel/CSV)
- SQL 解析与安全校验
- 参数化查询
- 结果统一化

**执行流程**:
```
用户输入 (自然语言/SQL)
    │
    ▼
判断输入类型
    │
    ├── 自然语言 → NL2SQL → SQL生成
    └── SQL输入 → SQL校验 (安全检查)
    │
    ▼
执行 SQL (调用连接器)
    │
    ▼
结果转换 (统一格式)
    │
    ▼
输出结果
```

**输出格式**:
```json
{
  "status": "success",
  "data": {
    "sql_generated": "SELECT ...",
    "query_sql": "SELECT ...",
    "row_count": 1000,
    "data_file": "knowledge/query_result_xxx.csv"
  }
}
```

##### query (高级查询)

**定位**: 复杂查询能力

**核心能力**:
- 聚合查询 (SUM/AVG/COUNT/MAX/MIN)
- 跨库关联 (多数据源 JOIN)
- 队列查询 (同期群)
- 漏斗查询 (转化数据)
- 时间区间查询

**子技能**:
- aggregation-query.md
- cross-db-join.md
- cohort-query.md
- funnel-query.md
- multi-source-query.md
- time-range-query.md

---

#### 3.2.2 数据处理类 Skills

##### data-clean (数据清洗)

**定位**: 数据预处理

**核心能力**:
- 空值处理 (填充/标记/删除)
- 异常值处理 (3σ原则/箱线图/业务规则)
- 重复值处理 (主键去重/完全去重)
- 格式标准化 (日期/数值/字符)

**处理模式**:
| 模式 | 适用场景 | 优势 |
|------|----------|------|
| SQL层处理 | 数据库数据 | 性能最优 |
| 内存处理 | 小文件 (<10万行) | 灵活性高 |
| 分块处理 | 大文件 | 避免 OOM |

##### data-quality-check (数据校验)

**定位**: Reviewer 模式 - 质量审核

**核心能力**:
- 空值校验
- 异常值校验
- 重复值校验
- 连续性校验

**校验规则**:
- 数值型字段空值≥5% → 预警
- 关键字段空值≥1条 → 终止
- 超出均值±3σ → 标记
- 主键重复 → 预警

---

#### 3.2.3 数据分析类 Skills

##### data-analysis (数据分析)

**定位**: 通用分析

**核心能力**:
- 描述性统计 (均值/中位数/最大最小/标准差)
- 趋势分析 (时间序列/环比/同比)
- 相关性分析 (变量关系)
- 分布分析 (数据分布特征)

##### model (数据建模)

**定位**: 高级建模

**核心能力**:
- 归因分析 (多渠道归因)
- 聚类分析 (用户分群)
- 队列分析 (同期群)
- 相关性分析
- 预测模型 (趋势/销量)
- 漏斗模型
- RFM模型
- 趋势分析

**执行模式**: Tool Wrapper + Multi-step
```
[模型选择器] → [用户确认] → [执行模型] → [结果校验] → [输出]
```

##### rfm-analysis (RFM分析)

**定位**: 用户价值分析

**核心概念**:
| 维度 | 说明 | 业务含义 |
|------|------|----------|
| R | 最近一次消费 | 流失可能性 |
| F | 消费频率 | 忠诚度 |
| M | 消费金额 | 价值贡献 |

**用户分群** (8类):
```
高R + 高F + 高M = 核心客户
高R + 高F + 低M = 潜力客户
低R + 低F + 低M = 流失客户
...
```

##### funnel-analysis (漏斗分析)

**定位**: 转化路径分析

**核心指标**:
- 步骤转化率 = 当前步骤 / 上一步骤 × 100%
- 总体转化率 = 当前步骤 / 第一步 × 100%
- 流失率 = 100% - 转化率

**标准漏斗**:
```
访问 → 浏览商品 → 加购 → 下单 → 支付 → 成交
```

##### insight-gen (洞察生成)

**定位**: 自动洞察

**洞察类型**:
- 趋势洞察 (数据走势)
- 异常洞察 (异常点)
- 对比洞察 (同比/环比)
- 构成洞察 (占比)
- 周期洞察 (周期性)

---

#### 3.2.4 输出类 Skills

##### visual (可视化)

**定位**: ECharts 图表生成

**核心能力**:
- 趋势图 (折线/面积)
- 对比图 (柱状/条形)
- 分布图 (直方/箱线)
- 占比图 (饼/环形)
- 热力图
- 仪表盘

**特色功能**:
- ECharts 集成
- HTML 自适应多端 (PC/平板/手机)
- 数据交互 (悬停/点击/查看/下载)

##### report (报告生成)

**定位**: 文档报告

**核心能力**:
- 日报生成
- 周报生成
- 月报生成
- 临时报告
- 对比报告

##### dashboard (仪表盘)

**定位**: 完整 HTML 看板

**核心能力**:
- 完整 HTML 页面生成
- 多图表集成
- 自适应布局
- 实时数据 (WebSocket/轮询)
- 告警配置
- 权限管理

**执行流程**:
```
需求理解 → 数据查询 → 图表生成 → 布局编排 → HTML生成 → 实时/告警配置
```

---

#### 3.2.5 安全类 Skills

##### security (安全脱敏)

**定位**: 数据安全

**核心能力**:
- 敏感数据检测
- 数据脱敏
- PII 识别
- 脱敏规则
- 合规检查
- 审计日志

**子技能**:
- sensitive-detection.md
- sensitive-desensitize.md
- pii-detection.md
- masking-engine.md
- masking-rules.md
- compliance-check.md
- audit-log-gen.md

##### compliance (合规检查)

**定位**: 合规校验

**合规规则**:
1. 个人信息识别 (身份证/手机号/银行卡/姓名/邮箱)
2. 数据分级 (L1-L4)
3. 权限检查 (角色×敏感等级矩阵)

**判定结果**:
- PASS: 完全合规
- MASK: 需脱敏
- APPROVE: 需审批
- DENY: 禁止执行

---

#### 3.2.6 上下文类 Skills

##### context-retriever (上下文检索)

**定位**: 行业知识检索

**核心能力**:
- 指标检索 (从行业配置中检索相关指标)
- 表映射检索 (数据库表字段映射)
- 时间解析 (自然语言时间解析)

**检索方式**:
- FTS5 全文检索 (< 2ms)
- N-gram 向量检索 (< 3ms)
- RRF 融合排序
- 时间衰减

##### danalyzer-guide (入门引导)

**定位**: 会话开始时加载

**核心内容**:
- 角色定位
- 核心理念
- 快速调用示例
- 安全优先提醒

---

## 4. 执行流程

### 4.1 Skill 调用流程

```
danalyzer-core 决策
    │
    ▼
判断是否需要 context-retriever
    │
    ├── 是 → 检索行业上下文
    └── 否
    │
    ▼
选择需要调用的 Skills
    │
    ▼
按依赖顺序执行 Skills
    │
    ├── data-query → 数据获取
    ├── data-clean → 数据清洗 (可选)
    ├── data-quality-check → 数据校验 (可选)
    ├── data-analysis → 数据分析 (可选)
    ├── rfm-analysis/funnel-analysis → 专业分析 (可选)
    ├── visual/report/dashboard → 输出
    │
    ▼
security 嵌入 (强制)
    │
    ▼
result-formatter 格式化
    │
    ▼
返回结果
```

### 4.2 Skill 组合示例

| 场景 | 技能组合 |
|------|----------|
| 简单查询 | data-query → visual → security |
| 完整分析 | data-query → data-clean → data-analysis → visual → security |
| 用户 RFM | data-query → rfm-analysis → visual → security |
| 漏斗分析 | context-retriever → data-query → funnel-analysis → visual → security |
| 报告生成 | data-query → data-clean → data-analysis → report → security |
| 仪表盘 | data-query → visual × n → dashboard → security |
| 合规导出 | data-query → compliance → security |

---

## 5. 与其他模块的协同

### 5.1 与 Agents 的协同

```
Agents (调度决策):
  └─ danalyzer-core: 唯一入口，决策调用 Skills
  └─ demand-parse: 需求拆解 (可选)
  └─ task-planner: 任务规划 (可选)
  └─ error-handler: 异常处理
  └─ result-formatter: 结果格式化

Skills (执行单元):
  └─ 由 danalyzer-core 按需调用
  └─ 执行具体业务逻辑
  └─ 返回执行结果
```

**调用方式**:
```markdown
使用 Skill 工具调用:
Skill: data-query
参数: query="SELECT ..."

Skill: visual
参数: chart_type="line", data=...
```

### 5.2 与 Hooks 的协同

| Hook 类型 | 协同方式 |
|-----------|----------|
| SessionStart | 加载 danalyzer-guide |
| PostToolUse (Skill) | 触发 post-skill-check (安全检查) |
| PostToolUse (Skill/Read) | 触发 analyze-observe + instinct-apply (学习系统) |

**hooks.json 配置**:
```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Skill",
        "hooks": [{ "command": "hooks/run-hook.cmd post-skill-check" }]
      },
      {
        "matcher": "Skill|Read",
        "hooks": [
          { "command": "learn/hooks/analyze-observe" },
          { "command": "learn/hooks/instinct-apply" }
        ]
      }
    ]
  }
}
```

### 5.3 与 Rules 的协同

| 规则级别 | 协同方式 |
|----------|----------|
| legal/ | security/compliance 强制检查 |
| core/ | 指标口径校验 (data-query 使用) |
| base/ | 图表规范 (visual 使用) |
| dynamic/ | 按需加载 |

### 5.4 与 Data 的协同

| 数据类型 | 协同方式 |
|----------|----------|
| industry/ | context-retriever 检索 |
| model/ | model Skill 使用 |
| template/ | report/dashboard 使用 |

### 5.5 与 Connectors 的协同

```
Skills 需要调用 Connectors 执行实际数据操作:
  - data-query → hive-connector / clickhouse-connector / mysql-connector
  - visual → excel-connector / csv-connector
  - data-clean → 各数据源连接器
```

---

## 6. 与 Claude Code 的集成

### 6.1 Skill Tool 集成

dAnalyzer 通过 Claude Code 的 **Skill 工具** 调用 Skills:

```markdown
# 调用数据查询
Skill: data-query
输入: {"query_input": "上月销售额", "data_source": "hive"}

# 调用可视化
Skill: visual
输入: {"chart_type": "line", "data": {...}}

# 调用安全脱敏
Skill: security
输入: {"data": [...], "rules": {...}}
```

### 6.2 按需加载机制

```
SessionStart:
  - 加载 Skills 元数据 (~1KB)
    * name
    * description
    * location

Skill 执行时:
  - 按需读取 SKILL.md (~5-10KB)
  - 执行具体能力
```

### 6.3 工作流程

```
Claude Code 会话
    │
    ▼
SessionStart Hooks
    ├─ session-start (加载指南)
    └─ load-instincts (加载索引)
    │
    ▼
danalyzer-core 接收请求
    │
    ▼
技能决策 + 按需加载
    │
    ▼
Skill 工具调用 Skills
    │
    ▼
PostToolUse Hooks
    ├─ post-skill-check (安全检查)
    ├─ analyze-observe (学习记录)
    └─ instinct-apply (智能建议)
    │
    ▼
返回结果
```

---

## 7. 方案优势与劣势

### 7.1 方案优势

| 优势 | 说明 | 效果 |
|------|------|------|
| **模块化** | 每个 Skill 专注单一功能 | 易于维护和扩展 |
| **按需加载** | 延迟加载完整指令 | 控制上下文膨胀 |
| **灵活组合** | 根据需求动态组合 | 适配多场景 |
| **安全嵌入** | 输出强制经过 security | 确保数据安全 |
| **专业分工** | 通用+专业 Skills | 覆盖各种分析需求 |
| **子技能支持** | 复杂 Skill 可拆分 | 灵活调用 |
| **行业感知** | context-retriever | 精准生成 SQL |

### 7.2 方案劣势

| 劣势 | 说明 | 缓解措施 |
|------|------|----------|
| ** Skill 数量多** | 16个 Skills 需要管理 | 元数据索引 |
| **调用链复杂** | 组合调用增加复杂度 | 清晰文档 |
| **依赖关系** | Skills 之间有依赖 | 明确定义 |
| **调试困难** | 动态组合难以追踪 | 增加日志 |

### 7.3 适用场景

| 场景 | 推荐 Skills |
|------|-------------|
| 简单数据查询 | data-query → visual |
| 完整数据分析 | data-query → data-clean → data-analysis → visual |
| 用户价值分析 | data-query → rfm-analysis → visual |
| 转化分析 | data-query → funnel-analysis → visual |
| 报告生成 | data-query → report |
| 仪表盘 | data-query → dashboard |
| 合规导出 | data-query → compliance → security |

---

## 8. 设计最佳实践

### 8.1 Skill 设计规范

1. **单一职责**: 每个 Skill 只做一件事
2. **清晰接口**: 定义明确的输入输出格式
3. **安全优先**: 输出类 Skill 必须嵌入 security
4. **错误处理**: 每个 Skill 都要有错误处理
5. **按需加载**: 不预加载完整指令

### 8.2 技能组合规范

1. **安全嵌入**: 所有输出必须经过 security
2. **顺序执行**: 按依赖关系排序
3. **可选跳过**: 非必要 Skill 可跳过
4. **上下文传递**: 正确传递数据

### 8.3 性能优化规范

1. **按需加载**: 只加载需要的 SKILL.md
2. **并行执行**: 独立 Skills 可并行
3. **缓存策略**: 索引信息缓存
4. **上下文控制**: 全程控制在 ~2KB

---

## 9. Skill 索引

### 9.1 按功能分类

| 类别 | Skills |
|------|--------|
| 数据查询 | data-query, query |
| 数据处理 | data-clean, data-quality-check |
| 数据分析 | data-analysis, model, rfm-analysis, funnel-analysis, insight-gen |
| 输出 | visual, report, dashboard |
| 安全 | security, compliance |
| 上下文 | context-retriever, danalyzer-guide |

### 9.2 按设计模式分类

| 模式 | Skills |
|------|--------|
| Tool Wrapper | data-query, visual, report, dashboard, security, compliance |
| Multi-step | data-clean, model, context-retriever |
| Reviewer | data-quality-check |
| Aggregator | dashboard, report |
| Specialized | rfm-analysis, funnel-analysis, insight-gen |

### 9.3 触发关键词

| Skill | 激活关键词 |
|-------|------------|
| data-query | 查询、取数、看看 |
| data-clean | 清洗、预处理、去重 |
| data-analysis | 分析、统计、趋势 |
| rfm-analysis | RFM、用户价值、用户分层 |
| funnel-analysis | 漏斗、转化、流失 |
| visual | 画图、图表、可视化 |
| report | 报告、日报、周报 |
| dashboard | 看板、监控、仪表盘 |
| security | 脱敏、安全、脱敏处理 |
| compliance | 合规、检查、是否合规 |
| context-retriever | 行业知识、指标定义 |
| insight-gen | 洞察、发现、建议 |

---

## 10. 总结

### 10.1 设计要点

dAnalyzer Skills 系统通过以下设计实现灵活、高效的数据分析能力:

1. **16个专业 Skills**: 覆盖查询/处理/分析/输出/安全/上下文
2. **按需加载**: 控制上下文膨胀
3. **灵活组合**: 根据需求动态调整
4. **安全嵌入**: 确保数据安全合规
5. **子技能支持**: 复杂 Skill 可拆分调用

### 10.2 与 Agents/Hooks 的协同

| 模块 | 职责 | 协同点 |
|------|------|--------|
| Agents | 调度决策 | 调用 Skills 执行 |
| Skills | 业务执行 | 被 Agents 调用 |
| Hooks | 自动化 | Skill 执行后触发检查 |

### 10.3 演进方向

- 增加更多专业分析 Skills
- 优化技能组合策略
- 增强 context-retriever 能力
- 完善安全规则库

---

*本文档于 2026-04-26 创建 (v1.0)*
