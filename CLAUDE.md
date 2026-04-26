# dAnalyzer 核心规范

> 版本: 3.6 (2026-04-26)
> 说明: Claude Code 数据分析 Agent 系统
> 设计理念: 按需加载 + 自主决策 + 行业适配 + 智能学习

---

## 1.1 规范目的

统一 dAnalyzer 数据分析 Agent 系统的配置标准，确保 Agent 可正常调用技能、规则、校验，实现端到端的数据分析任务。

---

## 1.2 核心设计理念

| 理念 | 说明 |
|------|------|
| **按需加载** | Skills 元数据预加载，完整指令仅在需要时读取 |
| **自主决策** | Agent 根据用户需求自主决定使用哪些技能，不预设固定流程 |
| **无状态** | 不依赖 workflows/ 或 storage/ 目录 |
| **灵活组合** | 根据实际需求动态组合技能，可跳过不需要的步骤 |

---

## 1.3 目录调用规范

### 1.3.1 智能体（agents）调用规范

扁平化目录结构，直接位于 agents/ 目录：

| Agent | 用途 |
|-------|------|
| danalyzer-core.md | ⭐ 核心调度器，唯一执行入口 |
| demand-parse.md | 需求拆解 |
| task-planner.md | 任务规划 |
| data-validator.md | 数据校验 |
| error-handler.md | 错误处理 |
| result-formatter.md | 结果格式化 |
| template/ | 报告模板 (5个) |

### 1.3.2 技能（skills）调用规范

**按需加载机制**:
1. Skills 元数据 (name/description/location) 预加载
2. 仅在需要时读取 `SKILL.md` 完整指令
3. Agent 自主决策调用哪些技能

**当前技能列表** (17个技能):

| 技能 | 用途 | 按需加载路径 |
|------|------|---------------|
| danalyzer-guide | 入门引导 | skills/danalyzer-guide/SKILL.md |
| data-query | 多数据源查询 | skills/data-query/SKILL.md |
| data-clean | 数据清洗 | skills/data-clean/SKILL.md |
| data-quality-check | 质量校验 | skills/data-quality-check/SKILL.md |
| data-analysis | 数据分析 | skills/data-analysis/SKILL.md |
| model | 数据建模 | skills/model/SKILL.md |
| funnel-analysis | 漏斗分析 | skills/funnel-analysis/SKILL.md |
| rfm-analysis | RFM分析 | skills/rfm-analysis/SKILL.md |
| visual | 可视化 | skills/visual/SKILL.md |
| query | 高级查询 | skills/query/SKILL.md |
| report | 报告生成 | skills/report/SKILL.md |
| security | 安全脱敏 | skills/security/SKILL.md |
| compliance | 合规检查 | skills/compliance/SKILL.md |
| context-retriever | 行业数据检索 | skills/context-retriever/SKILL.md |
| dashboard | 仪表盘 | skills/dashboard/SKILL.md |
| insight-gen | 洞察生成 | skills/insight-gen.md |

### 1.3.3 规则（rules）调用规范

| 级别 | 优先级 | 用途 |
|------|--------|------|
| legal/ | 最高 | 法律级合规规则（拦截式校验） |
| core/ | 高 | 企业级核心规则（强制生效） |
| base/ | 中 | 基础规范规则（建议性） |
| dynamic/ | 低 | 动态规则（临时合规、口径变更） |

### 1.3.4 数据资产（data）

| 目录 | 用途 | 现状 |
|------|------|------|
| `industry/` | ⭐ 行业配置（可切换） | 新增 |
| `model/` | 通用分析模型 | ✅ |
| `template/` | 通用模板 | ✅ |

**行业配置说明**：
- `data/industry/_base/` - 通用基础配置 (indicators/scenarios/mappings)
- `data/industry/ecommerce/` - 电商行业（默认）
- `data/industry/` 下可扩展更多行业

### 1.3.5 Hooks 自动化

> Claude Code 生态的核心差异：使用 Hooks 实现自动化

| 目录 | 用途 | 现状 |
|------|------|------|
| .claude-plugin/hooks.json | Hooks 配置文件 | ✅ 已实现 |

**Hook 类型**:
- `PreToolUse` - 工具执行前触发
- `PostToolUse` - 工具执行后触发
- `Stop` - 会话结束时触发

**当前配置**: `.claude-plugin/hooks.json`
- 基础 hooks 已配置
- 可扩展数据分析专用 hooks

### 1.3.6 命令系统（commands）

> 分层命令结构 + 多层帮助系统

| 目录 | 用途 | 现状 |
|------|------|------|
| commands/help.md | 多层帮助入口 | ✅ |
| commands/query/ | 查询命令 | ✅ |
| commands/analysis/ | 分析命令 | ✅ |
| commands/report/ | 报告命令 | ✅ |

**使用方式**:
```
/help                    → 显示所有命令分类
/help query              → 显示查询域命令
/help query nl           → 显示自然语言查询详细用法
/help analysis           → 显示分析域命令
```

### 1.3.7 不需要的目录

> ⚠️ **明确说明**: 以下目录在 Claude Code 生态中**不需要**:
> - ❌ `workflows/` - 不需要预设流程，Agent 自主决策
> - ❌ `storage/` - 不需要持久化，无状态设计

---

## 1.4 执行模型

### 1.4.1 danalyzer-core 执行流程

```
用户输入
    │
    ▼
┌──────────────────────────────────┐
│     danalyzer-core Agent         │
│  (数据分析核心 Agent)             │
└──────────────┬───────────────────┘
               │
   ┌───────────┼───────────┐
   │           │           │
   ▼           ▼           ▼
理解意图   技能决策   按需加载
   │           │           │
   │           │           └─→ Read: skills/xxx/SKILL.md
   │           │
   │           └─→ 根据需求选择技能组合
   │               (可跳过不需要的)
   │
   └─→ 解析用户需求:
       - 数据源
       - 分析目标
       - 输出格式
       - 特殊要求
               │
               ▼
          执行技能
               │
               ▼
          返回结果
```

### 1.4.2 技能组合示例

| 用户需求 | 技能组合 (Agent 自主决策) |
|----------|--------------------------|
| 销售周报 | data-query → data-clean → data-analysis → visual → report |
| 用户RFM | data-query → rfm-analysis → visual |
| 合规导出 | data-query → compliance → security |
| 简单查询 | data-query → visual |
| 漏斗分析 | funnel-analysis (含咨询) → data-query → visual |

---

## 1.5 文件命名规范

- 所有配置文件均以 `.md` 为后缀
- 文件名采用"小写字母+下划线"格式
- 目录命名固定，不可修改

---

## 1.6 文档编写规范

- 所有配置文件采用 Markdown 格式编写
- 核心内容需包含："核心职责/作用"、"执行逻辑/规则"、"输出结果"三部分
- Agent 格式: YAML frontmatter + Markdown
- Skill 格式: YAML frontmatter + Markdown

---

## 附录: 完整目录结构 (v3.6)

```
dAnalyzer/
├── AGENTS.md               # Agent 说明文档
├── agents/                 # 智能体配置 (6个 + 模板)
│   ├── danalyzer-core.md   # ⭐ 核心调度器
│   ├── demand-parse.md     # 需求拆解
│   ├── task-planner.md     # 任务规划
│   ├── data-validator.md   # 数据校验
│   ├── error-handler.md    # 错误处理
│   ├── result-formatter.md # 结果格式化
│   └── template/           # 报告模板 (5个)
├── skills/                 # 技能 (17个)
├── rules/                  # 规则 (4级)
├── checks/                 # 校验钩子
├── connectors/             # 工具对接
├── learn/                  # ⭐ 学习系统 (v1.4)
│   ├── hooks/              # Hook 脚本 (4个)
│   ├── agents/             # Agent (1个)
│   ├── scripts/            # 脚本 (含行业存储检索)
│   └── data/              # 数据存储
├── data/                   # 数据资产
│   ├── industry/          # ⭐ 行业配置 (可切换)
│   │   ├── _base/          # 通用基础配置
│   │   └── ecommerce/      # 电商行业 (默认)
│   ├── model/              # 通用分析模型
│   └── template/           # 通用模板
├── commands/              # 快捷指令 (分层结构)
│   ├── help.md            # 多层帮助入口
│   ├── query/             # 查询命令 (sql/nl/export)
│   ├── analysis/          # 分析命令 (trend/rfm/funnel/audit)
│   └── report/            # 报告命令 (daily/weekly/custom)
├── hooks/                 # 自动化脚本
├── docs/                  # 文档
│   └── overview.md        # ⭐ 设计哲学与架构概览
└── CLAUDE.md              # 本规范文件
```

---

## 附录: 与 ECC 设计对齐

| ECC 做法 | dAnalyzer 实现 |
|----------|----------------|
| 隐式 Skill 调用 | ✅ danalyzer-core 按需加载 |
| Agent 自主决策 | ✅ 不预设固定流程 |
| 无 workflows/ | ✅ 不创建该目录 |
| 无 storage/ | ✅ 不创建该目录 |
| Skills 元数据预加载 | ✅ 17 个技能元数据 |
| 按需读取 SKILL.md | ✅ 仅在需要时读取 |

---

## 附录: 学习系统 (learn/)

> 版本: 1.4 - 按需匹配设计
> 设计理念: 借鉴ECC自学习系统，避免上下文膨胀

### 设计原则

```
❌ 旧: SessionStart 加载所有高置信度 Instinct (~1.5KB)

✅ 新:
  - SessionStart: 只加载索引信息 (~100B)
  - Skill执行后: 按需匹配，只返回匹配的建议 (~300B)
```

### 目录结构

```
learn/
├── hooks/                      # Hook 脚本
│   ├── load-instincts         # SessionStart: 加载索引 (轻量)
│   ├── instinct-apply         # PostToolUse: 按需匹配建议
│   ├── analyze-observe        # PostToolUse: 记录观察
│   └── session-summary        # Stop: 会话总结
│
├── agents/                    # Agent
│   └── pattern-detector.md   # 模式检测 Agent
│
├── scripts/                   # 脚本
│   ├── instinct-engine.py    # Instinct 引擎
│   └── industry/             # ⭐ 行业数据存储检索
│       ├── store.py         # IndustryStore (混合存储)
│       └── retriever.py    # IndustryRetriever (高级检索)
│
└── data/                      # 数据存储
    ├── config.yaml            # 学习配置
    ├── observations/          # 观察记录 (输入)
    ├── patterns/              # 识别的模式 (输出)
    └── instincts/             # 应用规则 (交付)
```

### 工作流程

```
SessionStart
  └→ load-instincts: 只加载索引 (~100B)

danalyzer-core: 执行 Skill
  └→ PostToolUse:
       ├→ analyze-observe: 记录观察
       └→ instinct-apply: 按需匹配
           → 调用 instinct-engine.py
           → 只返回匹配的建议
```

### 数据流

```
observations/ (原始记录)  ──▶  Pattern Detector  ──▶  patterns/ (模式)
                              (后台Agent)              │
                                                          ▼
                                              instincts/ (应用规则)
                                                          │
                                                          ▼
                                              按需匹配 (Hook)
                                                          │
                                                          ▼
                                                    智能建议
```

### Hooks 配置

| Hook | 触发时机 | 作用 | 上下文影响 |
|------|----------|------|-----------|
| load-instincts | SessionStart | 加载索引 | ~100B |
| instinct-apply | PostToolUse | 按需匹配 | ~300B |
| analyze-observe | PostToolUse | 记录观察 | 无 |
| session-summary | Stop | 会话总结 | 无 |

### 与 ECC 的关系

| ECC | dAnalyzer Learning |
|-----|-------------------|
| observer.py | pattern-detector.md |
| instincts/ | learn/data/instincts/ |
| 项目级隔离 | 全局 + 行业双维度 |
| 全部加载 | **按需匹配** (避免上下文膨胀) |

---

*本文档于 2026-04-26 更新 (v3.6 + commands分层结构 + danalyzer-guide技能)*
