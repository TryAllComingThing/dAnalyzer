---
name: recipe
description: 固定报表/看板配方调度器。触发词命中 PRESET 后由路由协议加载，参数为子配方名。不要在动态分析中使用。
---

# 固定场景配方调度器

## 加载方式

```
Skill({skill: "danalyzer:recipe", args: "<子配方名>"})

示例:
  Skill({skill: "danalyzer:recipe", args: "weekly-east"})
  Skill({skill: "danalyzer:recipe", args: "sales-dashboard"})
```

## 工作方式

```
1. 接收 args → 子配方名
2. Read skills/recipe/<子配方名>.md → 获取固化指令
3. 严格按子配方执行（不修改、不扩展、不优化）
4. 配方内未显式指定 security → 执行链末级自动追加
```

## 子配方文件

位置: `skills/recipe/<name>.md`
格式: Markdown（无 frontmatter），必须包含以下四段：

| 段 | 说明 |
|----|------|
| `## 数据源` | 每个数据源的注册名 + 查询 SQL |
| `## 指标` | 指标计算口径与格式化 |
| `## 输出` | KPI 卡片布局 + 图表配置 + 诊断条件 |
| `## 红线` | 禁止的行为（至少含「不可修改 SQL」和「不可跳过 security」） |

---

## 硬约束（所有子配方共享）

- SQL 不可修改、不可优化、不可扩展条件
- 图表类型/维度不可替换
- security 为强制末级（子配方中未列也强行追加）
- 不经过问题理解、知识注入、数据匹配、复杂度判定

## 用户添加新配方

1. 复制 `skills/recipe/_template.md` → `skills/recipe/<新场景>.md`
2. 填入数据源/查询/指标/输出
3. 在 `hooks/session-routing.md` 固定场景速查表新增一行

## 验证（所有子配方共享）

1. 所有查询返回非空结果
2. 所有 KPI 计算成功
3. 所有图表已渲染
4. `security_scan.py` 退出码 0
5. 输出文件存在且非空
