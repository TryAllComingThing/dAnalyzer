---
name: danalyzer
description: "dAnalyzer 统一入口命令。所有数据分析请求必须通过此命令路由到 danalyzer-core Agent，由核心调度器统一拆解、规划、执行。"
trigger: danalyzer
---

# dAnalyzer 统一入口命令

## 核心原则

**⚠️ 这是所有数据分析请求的唯一入口。**

当用户输入任何数据分析相关的需求时，必须通过 danalyzer-core Agent 进行处理，而不是直接执行某个 Skill。

## 使用方式

```
/danalyzer <你的数据分析需求>
```

## 执行流程

```
用户: /danalyzer 分析mysql数据库中的订单数据形成看板
                              │
                              ▼
                    ┌─────────────────────┐
                    │   danalyzer-core    │
                    │   (核心调度器)       │
                    └──────────┬──────────┘
                               │
                    ┌──────────┼──────────┐
                    ▼          ▼          ▼
              需求理解    技能决策    按需加载
                    │          │          │
                    ▼          ▼          ▼
              demand-parse  data-query  security
              task-planner  data-analysis  result-formatter
                            dashboard
```

## 为什么需要统一入口

| 问题 | 原因 | 解决 |
|------|------|------|
| 直接使用 `/danalyzer:data-analysis` 会跳过编排 | Skill 直接加载到上下文，绕过了 danalyzer-core | 统一通过 `/danalyzer` 入口 |
| 缺少需求拆解环节 | 没有经过 demand-parse 确认模糊需求 | danalyzer-core 按需调用 demand-parse |
| 缺少任务规划环节 | 没有经过 task-planner 制定执行计划 | danalyzer-core 按需调用 task-planner |
| 缺少安全校验环节 | 输出没有经过 security 脱敏 | danalyzer-core 默认嵌入 security |
| 缺少行业上下文 | 没有调用 context-retriever 检索行业指标 | danalyzer-core 按需检索 |

## 与普通 slash 命令的区别

| 命令 | 行为 |
|------|------|
| `/query nl` | 直接执行自然语言查询 (跳过编排) |
| `/analysis trend` | 直接执行趋势分析 (跳过编排) |
| `/report daily` | 直接生成日报 (跳过编排) |
| **`/danalyzer`** | **通过 danalyzer-core 完整编排流程** |

## 推荐使用场景

- 首次分析某个业务问题时 → 使用 `/danalyzer`
- 需要完整数据分析流程时 → 使用 `/danalyzer`
- 需要行业上下文时 → 使用 `/danalyzer`
- 简单已知操作 → 可使用快捷命令 (`/query nl` 等)
