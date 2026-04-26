# dAnalyzer 学习系统

> 版本: 1.4 (按需匹配设计)
> 说明: dAnalyzer 分析行为学习与智能应用系统

---

## 概述

dAnalyzer 学习系统借鉴 ECC 自学习系统，采用**按需匹配**设计，避免上下文膨胀。

## 核心设计原则

```
❌ 之前: SessionStart 加载所有高置信度 Instinct (~1.5KB)

✅ 现在: 
  - SessionStart: 只加载索引信息 (~100字节)
  - Skill执行后: 按需匹配，只返回匹配的建议 (~几百字节)
```

## 目录结构

```
learn/
├── hooks/                 # Hook 脚本
│   ├── load-instincts    # SessionStart: 加载索引 (轻量)
│   ├── instinct-apply   # PostToolUse: 按需匹配建议
│   ├── analyze-observe  # PostToolUse: 记录观察
│   └── session-summary  # Stop: 会话总结
│
├── agents/               # Agent
│   └── pattern-detector.md  # 模式检测 Agent
│
├── scripts/              # 脚本
│   └── instinct-engine.py  # Instinct 引擎 (按需匹配)
│
├── data/                 # 数据存储
│   ├── observations/    # 观察记录
│   ├── patterns/        # 识别的模式
│   └── instincts/       # Instinct 存储
│
└── README.md             # 本文件
```

## 工作流程

```
用户输入
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│ SessionStart                                                │
│ load-instincts: 只加载索引信息 (~100字节)                   │
└─────────────────────────────────────────────────────────────┘
    │
    ▼
danalyzer-core 执行分析
    │
    ├── 技能决策 + 执行 Skill
    │
    ├── PostToolUse:
    │   ├── analyze-observe: 记录观察
    │   └── instinct-apply: 按需匹配 Instinct
    │       → 调用 instinct-engine.py
    │       → 只返回匹配的建议 (~几百字节)
    │
    └── 返回结果 + 匹配的建议
```

## 上下文负载对比

| 设计 | SessionStart | 按需匹配 | 总计 |
|------|-------------|----------|------|
| 旧版 | ~1.5KB | 0 | ~1.5KB |
| 新版 | ~100B | ~300B | ~400B |

## Instinct 类型

| Instinct | 作用 | 触发方式 |
|----------|------|----------|
| smart-recommendation | 智能推荐 | 按需匹配 |
| error-avoidance | 错误预防 | 按需匹配 |
| industry-discovery | 行业适应 | 按需匹配 |

## 使用方式

```bash
# 手动触发模式检测
Skill: pattern-detector

# 按需匹配自动发生 (无需调用)
# 在 Skill 执行后自动匹配并返回建议
```

---

*版本: 1.4 - 按需匹配设计*
*最后更新: 2026-04-25*
