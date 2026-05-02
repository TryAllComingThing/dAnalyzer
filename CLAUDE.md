# dAnalyzer 架构参考

> 版本: 4.5 (2026-05-02)
> 说明: Claude Code 数据分析 Agent 系统 — V4 自进化完备
> 设计理念: 按需加载 + 自主决策 + 行业适配 + Skill 规则优先
> 用途: **架构参考文档（仅供人工查阅，不注入运行时上下文）**

**运行时路由决策以 `hooks/routing-table.md`（SessionStart 注入）为准。运行时执行决策以 `skills/danalyzer-core/SKILL.md` 为准。**

---

## 1. 核心设计理念

| 理念 | 说明 |
|------|------|
| **按需加载** | Skills 元数据预加载，完整指令仅在需要时 Read |
| **自主决策** | 根据用户需求动态选择技能组合，不预设固定流程 |
| **灵活组合** | 可跳过不需要的步骤，按实际需求编排 |

---

## 2. 技能与 Agent 目录（11 技能 + 3 Agent）

### 技能

| 技能 | 用途 |
|------|------|
| data-query | 多数据源查询（含高级查询：聚合/跨库/时间区间） |
| data-clean | 数据清洗 + 质量校验（空值/异常/重复/格式/文本） |
| data-analysis | 统计分析（描述性/趋势/相关性/分布） |
| model | 数据建模（RFM/漏斗/归因/聚类/预测/留存/相关性） |
| visual | 可视化（ECharts 图表/HTML 自适应多端） |
| report | 报告生成（日报/周报/月报/临时/对比） |
| security | 安全脱敏 + 合规检查（敏感检测/脱敏/审计） |
| context-retriever | 行业数据检索 |
| dashboard | 仪表盘（布局/组件/实时/告警/导出） |
| insight-gen | 洞察生成 |

### Agent

| Agent | 职责 | 文件 |
|-------|------|------|
| danalyzer | 数据分析全链路（查询/清洗/建模/可视化/报告） | agents/danalyzer.md |
| research | 深度研究报告/调研/PPT/总结建议（预留） | *待创建* |
| error-handler | 错误类型分析/重试/降级/中止决策 | agents/error-handler.md |

---

## 3. 数据资产

| 目录 | 用途 |
|------|------|
| `knowledge/industry/` | 行业配置（可切换：电商/物流/制造/金融） |
| `knowledge/industry/_base/` | 通用基础配置（indicators/scenarios/mappings） |
| `knowledge/model/` | 通用分析模型 |
| `knowledge/template/` | 已废弃 — 模板已迁移至各 skill 的 assets/ 和 references/ |

---

## 4. 目录结构

```
dAnalyzer/
├── skills/          # 技能（11 个）
├── agents/          # Agent 定义（含 README.md 体系文档）
├── connectors/      # 数据源连接器（统一 I/O 接口）
├── knowledge/       # 领域知识（行业配置/模型/模板）
├── learn/           # V4 自进化学习系统
│   ├── ingest/      #   信号检测 + session 处理 + 计数器
│   ├── analyze/     #   聚类 + 置信度 + 模板偏离 + 草稿发现
│   ├── validate/    #   75/25 hold-out 验证 + 组合校验
│   ├── apply/       #   补丁应用 + 权重爬坡 + 草稿管理 + 模板更新
│   ├── monitor/     #   48h 窗口 + 周报 + 异常检测
│   └── data/        #   进化配置 (config.yaml)
├── commands/        # 快捷指令
└── hooks/           # 自动化脚本 + 路由表（routing-table.md）
```

---

## 5. V4 自进化系统（2026-05-02 完备）

| 组件 | 文件 | 功能 |
|------|------|------|
| 信号引擎 | `learn/ingest/` | 4 类信号检测 + session 处理 + JSONL 持久化 |
| 聚类分析 | `learn/analyze/signal_analyzer.py` | 纠正/补充/扩展聚类 + 假设生成 |
| 置信度 | `learn/analyze/confidence.py` | 频率(α=0.35) + 一致性(β=0.30) + 多样性(γ=0.20) + 邻近(δ=0.15) |
| 语义传播 | `learn/analyze/propagation.py` | 共现矩阵 + 跨行业迁移(0.125x) |
| 验证 | `learn/validate/` | 75/25 hold-out + 组合冲突检测 |
| 补丁 | `learn/apply/patch_builder.py` | canonical/patches 双栈 → _active/ 重建 |
| 权重爬坡 | `learn/apply/weight_climber.py` | +0.15/week climb → freeze → decay → defunct 状态机 |
| 模板进化 | `learn/analyze/template_*.py` | 四重门草稿发现 + 偏离监控 + 原子调整 + 冷却期 |
| 监控 | `learn/monitor/` | 48h 窗口 + 周报 + 用户主导/突发/退化检测 |
| 主动学习 | `scripts/intent_parser.py` | Feature flag 控制的反问分支（默认关闭） |

**测试:** 189 个（单元 + 集成），覆盖全链路闭环。

---

*本文档于 2026-05-02 更新 (v4.4)。架构参考用途，不参与运行时路由与决策。*
