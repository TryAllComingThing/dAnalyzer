# dAnalyzer — Agent Instructions

> 数据分析核心 Agent 系统，提供按需加载 + 自主决策的数据分析能力
> 版本: 3.1

---

## 设计理念

1. **按需加载** — Skills 元数据预加载，完整指令仅在需要时读取
2. **自主决策** — Agent 根据用户需求自主决定使用哪些技能，不预设固定流程
3. **无状态** — 不依赖 workflows/ 或 storage/ 目录
4. **灵活组合** — 根据实际需求动态组合技能，可跳过不需要的步骤

---

## 可用 Agents

| Agent | 目的 | 使用场景 |
|-------|------|----------|
| danalyzer-core | 数据分析核心，按需决策 | 唯一入口，内嵌需求拆解+任务规划+结果格式化 |
| error-handler | 错误处理 | 异常捕获与恢复（唯一 spawn Agent） |

> demand-parse、task-planner、data-validator、result-formatter 已合并为 danalyzer-core 内嵌能力。

---

## Agent 编排

danalyzer-core 是**唯一执行入口**，所有能力内嵌：

```
用户输入
    │
    ▼
danalyzer-core (核心调度)
    │
    ├── 需求理解 (内嵌)
    ├── 需求模糊? → 需求拆解 (内嵌)
    ├── 任务复杂? → 任务规划 (内嵌)
    ├── 技能决策 (内嵌)
    ├── 按需加载 & 执行 Skills
    └── 发生异常? → error-handler (唯一 spawn)
```

**条件触发规则**:

| 条件 | 处理方式 |
|------|----------|
| 需求模糊/不明确 | 内嵌需求拆解 |
| 任务复杂 (>2技能) | 内嵌任务规划 |
| 需要数据校验 | 内嵌校验 (或调用 data-quality-check Skill) |
| 发生异常 | spawn error-handler Agent |
| 需要标准化输出 | 内嵌格式化 |

---

## 可调用 Skills

| Skill | 用途 | 调用方式 |
|-------|------|----------|
| data-query | 多数据源查询 | Skill tool |
| data-clean | 数据清洗 | Skill tool |
| data-quality-check | 质量校验 | Skill tool |
| data-analysis | 数据分析 | Skill tool |
| model | 数据建模 (含RFM、漏斗) | Skill tool |
| visual | 可视化 | Skill tool |
| query | 高级查询 | Skill tool |
| report | 报告生成 | Skill tool |
| security | 安全合规 (含脱敏) | Skill tool |
| dashboard | 看板技能 | Skill tool |
| insight-gen | 洞察生成 | Skill tool |

## 技能组合示例

danalyzer-core 根据用户需求自主决定技能组合：

| 用户需求 | 技能组合 |
|----------|----------|
| 销售周报 | data-query → data-clean → data-analysis → visual → report |
| 用户RFM | data-query → model (rfm) → visual |
| 合规导出 | data-query → security → 输出 |
| 简单查询 | data-query → visual |
| 漏斗分析 | model (funnel) → data-query → visual |
| 归因分析 | data-query → model (attribution) → visual |

---

## 数据安全规范

### 处理数据前必须检查

- [ ] **敏感数据识别** — 调用 security/sensitive-detection
- [ ] **合规检查** — 调用 security (包含合规能力)
- [ ] **脱敏处理** — 调用 security/masking-engine
- [ ] **审计日志** — 调用 security/audit-log-gen

### 禁止行为

- ❌ 禁止导出未脱敏的 PII 数据
- ❌ 禁止绕过合规检查 (security)
- ❌ 禁止记录敏感信息到日志
- ❌ 禁止跳过 data-quality-check 直接分析

### 合规流程

所有输出场景必须经过 security 处理:

```
分析后输出流程:
  data-query → data-analysis → (清洗) → visual/report/dashboard → security → 输出
                                                                          ↑
                                                            脱敏 + 合规检查 (默认嵌入)
```

### 安全处理原则

1. **默认嵌入**: 所有输出技能后默认添加 security
2. **数据完整**: 分析阶段使用原始数据保证准确性
3. **输出安全**: 最终输出前进行脱敏和合规检查

---

## 错误处理

1. **数据不可用** → 提示用户提供或确认数据源
2. **技能执行失败** → 记录错误 → 尝试恢复或报告
3. **依赖不满足** → 智能调整方案
4. **权限不足** → 提示用户获取权限

---

## 项目结构

```
agents/          — 2个 Agent (danalyzer-core + error-handler)
skills/          — 17个技能
rules/           — 19个规则 (4级)
checks/          — 15个校验钩子
connectors/      — 9个连接器
data/            — 28个资产
commands/        — 7个快捷指令
```

---

## 与 ECC 的区别

| 维度 | ECC | dAnalyzer |
|------|-----|-----------|
| 领域 | 软件开发 | 数据分析 |
| 执行方式 | 多 Agent 协作 | danalyzer-core 单一入口 |
| 流程预设 | 无 | 无 (自主决策) |
| 技能调用 | 按需加载 | 按需加载 |
| 安全要求 | 通用安全 | 数据安全 + 合规 |

---

## 核心原则

1. **不预设固定流程** — 由 danalyzer-core 自主决定
2. **可跳过不需要的步骤** — 如不需要清洗则跳过
3. **支持动态组合** — 根据上下文调整
4. **按需加载** — 只读取需要的 SKILL.md
5. **安全优先** — 数据处理前必须合规检查
