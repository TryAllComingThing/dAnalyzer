# dAnalyzer Hooks 机制

> 版本: 1.0 (2026-04-25)
> 说明: 自动化钩子配置，参考 Everything Claude Code 设计

---

## 1. Hooks 概述

Hooks 是 Claude Code 的自动化机制，允许在工具执行前/后自动触发自定义操作。

### Hook 类型

| 类型 | 触发时机 | 用途 |
|------|----------|------|
| **PreToolUse** | 工具执行前 | 验证、检查、预处理 |
| **PostToolUse** | 工具执行后 | 格式化、记录、日志 |
| **Stop** | 会话结束时 | 资源清理、会话保存 |

---

## 2. 当前配置

### 2.1 配置文件位置

```
.claude-plugin/hooks.json
```

### 2.2 当前 Hooks

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [{ "type": "command", "command": "echo 'dAnalyzer: Pre-execution check'" }],
        "description": "dAnalyzer pre-execution hook for Bash commands"
      },
      {
        "matcher": "Write|Edit",
        "hooks": [{ "type": "command", "command": "echo 'dAnalyzer: File modification detected'" }],
        "description": "dAnalyzer hook for file modifications"
      }
    ],
    "PostToolUse": [
      {
        "matcher": "*",
        "hooks": [{ "type": "notification", "message": "dAnalyzer: Tool execution completed" }],
        "description": "dAnalyzer post-execution notification",
        "async": true,
        "timeout": 5
      }
    ],
    "Stop": [
      {
        "matcher": "*",
        "hooks": [{ "type": "command", "command": "echo 'dAnalyzer: Session ending - cleaning up'" }],
        "description": "dAnalyzer session cleanup hook"
      }
    ]
  }
}
```

---

## 3. Hook 配置说明

### 3.1 Matcher (匹配器)

| Matcher | 匹配工具 |
|---------|----------|
| `*` | 所有工具 |
| `Bash` | Bash 命令 |
| `Write` | 写入文件 |
| `Edit` | 编辑文件 |
| `Read` | 读取文件 |
| `Glob` | 文件搜索 |
| `Grep` | 内容搜索 |
| `Agent` | Agent 调用 |
| `Skill` | Skill 调用 |
| `Write\|Edit` | 写入或编辑 |

### 3.2 Hook 类型

| 类型 | 说明 | 参数 |
|------|------|------|
| `command` | 执行 shell 命令 | `command` |
| `notification` | 发送通知 | `message` |
| `command` (async) | 异步执行命令 | `command`, `async: true`, `timeout` |

### 3.3 选项

- `async`: 是否异步执行 (默认 false)
- `timeout`: 超时时间 (秒)
- `description`: 描述说明

---

## 4. 自定义 Hooks

### 4.1 数据质量检查 Hook

```json
{
  "matcher": "Bash",
  "hooks": [
    {
      "type": "command",
      "command": "node scripts/hooks/data-quality-check.js",
      "description": "Execute data quality check after query"
    }
  ]
}
```

### 4.2 合规检查 Hook

```json
{
  "matcher": "Write|Edit",
  "hooks": [
    {
      "type": "command",
      "command": "node scripts/hooks/compliance-check.js",
      "description": "Check for sensitive data before writing"
    }
  ]
}
```

### 4.3 日志记录 Hook

```json
{
  "matcher": "Bash",
  "hooks": [
    {
      "type": "command",
      "command": "node scripts/hooks/log-execution.js",
      "async": true,
      "timeout": 10,
      "description": "Log command execution for audit"
    }
  ]
}
```

---

## 5. 最佳实践

### 5.1 保持简洁

- Hook 命令应该快速执行
- 避免长时间运行的命令
- 使用异步处理不阻塞主流程

### 5.2 错误处理

- Hook 执行失败不应阻止主流程
- 使用 try-catch 包裹敏感操作
- 提供有意义的错误消息

### 5.3 安全性

- 不要在 Hook 中硬编码敏感信息
- 使用环境变量存储密钥
- 验证输入参数

---

## 6. 与 ECC 对比

| 特性 | ECC | dAnalyzer |
|------|-----|-----------|
| PreToolUse | ✅ 丰富 | ✅ 基础 |
| PostToolUse | ✅ 多种 | ✅ 基础 |
| Stop | ✅ 多种 | ✅ 基础 |
| 自定义 Hooks | ✅ 完整 | ✅ 框架已搭建 |

---

## 7. 扩展建议

### 7.1 数据分析专用 Hooks

| Hook | 用途 |
|------|------|
| 数据查询日志 | 记录所有查询操作 |
| 合规检查 | 写入前检查敏感数据 |
| 质量验证 | 执行后验证数据质量 |
| 结果归档 | 自动保存分析结果 |

### 7.2 实现示例

```javascript
// scripts/hooks/data-query-log.js
const fs = require('fs');
const path = require('path');

module.exports = async function(args) {
  const logEntry = {
    timestamp: new Date().toISOString(),
    query: args.command,
    user: process.env.USER
  };

  const logPath = path.join(process.env.HOME, '.dAnalyzer/logs/queries.json');
  // 写入日志...
};
```

---

*文档完成 - 2026-04-25*
