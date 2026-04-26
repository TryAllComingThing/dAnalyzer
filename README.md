# dAnalyzer Plugin

> 数分ECC - 数据分析企业命令中心 | 配置化数据分析自动化平台

## 简介

dAnalyzer 是一个基于 Claude Code 的数据分析 Plugin，提供完整的数据分析能力，包括数据查询、清洗、分析、报告生成、合规检查等。

**设计理念**：按需加载 + 自主决策 (参考 Everything Claude Code)

---

## 目录结构

```
dAnalyzer/
├── agents/              # 智能体 (6个)
│   ├── base/            # 基础通用 (5个)
│   └── dispatch/        # 调度器 (1个) + 模板 (5个)
├── skills/              # 技能 (16个, 56个文件)
├── rules/               # 规则 (19个, 4级)
├── checks/              # 校验钩子 (15个)
├── connectors/          # 工具对接 (9个)
├── data/                # 数据资产 (28个)
├── commands/            # 快捷指令 (6个)
├── docs/                # 文档
├── scripts/             # 脚本
└── CLAUDE.md            # 核心规范
```

---

## 核心组件

### 1. 智能体 (Agents)

| 目录 | 数量 | 说明 |
|------|------|------|
| base/ | 5 | 基础通用能力（需求拆解、任务规划、数据校验、错误处理、结果格式化） |
| dispatch/ | 1 | **核心调度器**：danalyzer-core，按需决策 |

**核心执行入口**：`danalyzer-core` - 根据用户需求自主决定调用哪些技能

### 2. 技能 (Skills) - 16个

| 技能 | 说明 | 子技能 |
|------|------|--------|
| data-query | 多数据源查询 | - |
| data-clean | 数据清洗 | 6 |
| data-analysis | 数据分析 | - |
| data-quality-check | 数据质量检查 | - |
| compliance | 合规检查 | - |
| rfm-analysis | RFM分析 | - |
| funnel-analysis | 漏斗分析 | - |
| model | 数据建模 | 8 |
| query | 高级查询 | 6 |
| report | 报告生成 | 6 |
| security | 安全脱敏 | 7 |
| visual | 可视化 | 7 |

### 3. 规则 (Rules) - 19个

| 级别 | 数量 | 说明 |
|------|------|------|
| legal | 4 | 法律级 - 最高优先级，违规终止 |
| core | 5 | 企业核心 - 强制生效 |
| base | 5 | 基础规范 - 建议遵循 |
| dynamic | 4 | 动态规则 - 临时生效 |

### 4. 校验 (Checks) - 15个

| 分类 | 数量 | 说明 |
|------|------|------|
| data-quality | 7 | 空值、异常值、重复值、断层检测 |
| caliber | 4 | 口径一致性、维度统一性 |
| compliance | 4 | 敏感数据、违规输出扫描 |

### 5. 连接器 (Connectors) - 9个

| 类型 | 数量 | 说明 |
|------|------|------|
| datawarehouse | 5 | Hive、ClickHouse、MySQL、PostgreSQL、Oracle |
| tool | 4 | CSV、JSON、Excel、Python |

### 6. 快捷指令 (Commands) - 6个

| 指令 | 说明 |
|------|------|
| /weekly-report | 生成周报 |
| /data-query | 数据查询 |
| /rfm-analysis | RFM分析 |
| /funnel-analysis | 漏斗分析 |
| /data-check | 数据检查 |
| /compliance-scan | 合规扫描 |

---

## 使用示例

```bash
# 生成周报
/weekly-report 电商 2026年第17周

# 数据查询
/data-query hive SELECT * FROM sales WHERE dt = '2026-04-24'

# RFM分析
/rfm-analysis 电商 近30天

# 数据质量检查
/data-check ./data/sales.csv
```

---

## 执行流程

```
用户输入
    │
    ▼
danalyzer-core (决策)
    │
    ├── 需求理解：解析数据源、分析目标、输出格式
    ├── 技能决策：自主选择技能组合
    └── 按需加载：仅读取需要的 SKILL.md
    │
    ▼
执行技能
    │
    ▼
返回结果
```

---

## 设计理念

| 理念 | 说明 |
|------|------|
| **按需加载** | Skills 元数据预加载，完整指令仅在需要时读取 |
| **自主决策** | Agent 根据用户需求自主决定使用哪些技能，不预设固定流程 |
| **无状态** | 不依赖 workflows/ 或 storage/ 目录 |
| **灵活组合** | 根据实际需求动态组合技能，可跳过不需要的步骤 |

---

## 文件统计

| 类型 | 数量 |
|------|------|
| Commands | 6 |
| Skills | 56 |
| Agents | 11 |
| Rules | 19 |
| Checks | 15 |
| Connectors | 22 |
| Data Assets | 28 |
| **总计** | **157** |

---

## 版本

- v3.1 (2026-04-25) - 精简 agents，删除重复文件和预设流程
- v3.0 (2026-04-25) - 初始版本

---

## 相关文档

- [CLAUDE.md](CLAUDE.md) - 核心规范
- [agents/README.md](agents/README.md) - 智能体说明
- [skills/README.md](skills/README.md) - 技能说明
- [rules/README.md](rules/README.md) - 规则说明
- [checks/README.md](checks/README.md) - 校验说明
- [connectors/README.md](connectors/README.md) - 连接器说明
- [data/README.md](data/README.md) - 资产说明

---

MIT
