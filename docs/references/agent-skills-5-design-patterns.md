# Agent Skills 5种设计模式 (Google ADK 2026.3)

> 来源: Google ADK/Antigravity 官方最佳实践
> 与 Claude Code Skills 高度兼容，可跨平台复用

---

## 核心原则

| 原则 | 描述 |
|------|------|
| **单一职责** | 一个技能只做一件事（如 "代码审查" 与 "测试生成" 拆分） |
| **最小权限** | allowed-tools 仅开放必要工具（如审查技能仅允许 Read/Grep） |
| **动态加载** | 规则外置到 references/ 目录，提升可维护性 |

---

## 模式1: External Tool/Library Wrapper (外置工具封装)

### 定义
将外部工具/库封装为技能，动态加载规范文档，避免硬编码。

### 目录结构
```
skill-name/
├── SKILL.md
└── references/
    └── tool-conventions.md
```

### 适用场景
- 封装特定技术栈的最佳实践（FastAPI、React、Go等）
- 团队统一代码规范
- 工具版本管理

### 示例
```
# fastapi-best-practice 技能
references/fastapi-conventions.md:
- 路由命名规范
- 错误处理模式
- 中间件使用标准
- Pydantic 模型定义规范
```

---

## 模式2: Template-Driven (模板驱动)

### 定义
将模板文件放在 assets/ 目录，运行时加载并填充变量。

### 目录结构
```
skill-name/
├── SKILL.md
└── assets/
    └── template.md
```

### 适用场景
- 文档生成（API文档、README）
- 代码生成（组件模板、配置文件）
- 报告生成（周报、测试报告）

### 示例
```
# api-doc-generator 技能
assets/openapi-template.md:
{{title}}
{{description}}
{{endpoints}}
→ 运行时替换变量生成完整文档
```

---

## 模式3: Checklist-Driven (清单驱动)

### 定义
加载审查清单，分级标记问题（CRITICAL/HIGH/MEDIUM/LOW）。

### 目录结构
```
skill-name/
├── SKILL.md
└── references/
    └── review-checklist.md
```

### 适用场景
- 代码审查
- 安全审计
- 合规检查
- 性能审查

### 示例
```
# code-reviewer 技能
references/review-checklist.md:
## CRITICAL
- [ ] 无硬编码密码/密钥
- [ ] 无SQL注入漏洞

## HIGH
- [ ] 错误处理完整
- [ ] 资源正确释放

## MEDIUM
- [ ] 代码注释充分
- [ ] 命名清晰
```

---

## 模式4: Interactive Consultation (交互咨询)

### 定义
强制在行动前先问清楚关键信息，确保充分理解需求后再执行。

### 适用场景
- 项目规划
- 需求分析
- 复杂任务启动
- 技术方案设计

### 关键问题清单
```
开始规划前必须确认:
□ 业务目标是什么？
□ 预算和时间约束？
□ 关键里程碑/截止日期？
□ 核心干系人？
□ 成功标准是什么？
```

### 示例
```
# project-planner 技能
SKILL.md:
1. 先询问项目背景和目标
2. 确认预算、人力、时间约束
3. 了解关键干系人
4. 只有信息充分时才进入规划阶段
```

---

## 模式5: Pipeline/Workflow (流水线)

### 定义
分解为多步骤流程，任一步失败则终止，确保质量。

### 目录结构
```
skill-name/
├── SKILL.md
└── stages/
    ├── 01-parse.md      # 解析输入
    ├── 02-generate.md   # 生成内容
    ├── 03-review.md     # 审查质量
    └── 04-output.md     # 输出结果
```

### 适用场景
- 文档处理（解析→生成→审查→输出）
- 数据转换流水线
- 内容生产工作流

### 示例
```
# doc-pipeline 技能
stages/
  01-parse.md:  解析源文档，提取关键信息
  02-generate.md: 根据模板生成目标文档
  03-review.md: 审查内容完整性
  04-output.md:  输出并记录日志

规则: 任一步失败 → 终止流水线，报告错误
```

---

## Claude Code Skills 兼容性对比

| 维度 | Google ADK | Claude Code |
|------|------------|-------------|
| **标准来源** | 官方5种设计模式 (2026.3) | 社区规范 + 内置最佳实践 |
| **元数据字段** | 更精简（无 disable-model-invocation） | 扩展字段更多 |
| **权限控制** | 手动/自动触发 | 细粒度允许/拒绝 |
| **资源加载** | 强调动态加载 references/ | 支持内联 + 外置 |

### 兼容性保证
- ✅ 目录结构完全兼容
- ✅ SKILL.md 格式兼容
- ✅ 5种模式可直接复用
- ✅ 可同时适配 Google ADK 与 Claude Code

---

## 快速开始模板

### 最小 SKILL.md
```yaml
---
name: skill-name
description: 技能简短描述
trigger: /command 或自动触发
allowed-tools:
  - Read
  - Edit
  - Write
---

# 技能指令
[你的指令内容]
```

### 建议的技能存放位置
```
优先级: 企业 > 个人 > 项目
插件技能: 插件名:技能名 (命名空间隔离)
```

---

## 参考资料

- [Google ADK Skills 文档](https://google.github.io/adk-docs/skills/)
- [Google 5种设计模式博客](https://cloud.google.com/blog/ai-machine-learning/5-agent-skill-design-patterns-every-adk-developer-should-know)
- [Claude Code Skills 官方](https://docs.claude.com/en/docs/claude-code/skills)
- [Agent Skills 开放标准](https://agentskills.io)
