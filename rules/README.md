# 分级规则库 (rules)

## 目录用途

分级强制规则库，用于约束和规范数分任务执行过程中的行为。按优先级从高到低分为：

- **法律级合规规则（legal）**：最高优先级，拦截式校验，违规立即终止任务
- **企业级核心规则（core）**：强制生效，前置校验，口径不一致时禁止执行
- **基础规范规则（base）**：建议性，提醒式校验，不强制终止但给出优化建议
- **动态规则（dynamic）**：临时合规、节日/季度口径变更，可设置生效时间

## 目录结构

```
rules/
├── legal/           # 法律级规则 (4个)
│   ├── data-security.md
│   ├── export-control.md
│   ├── privacy-protection.md
│   └── sensitive-data.md
├── core/            # 企业核心规则 (5个)
│   ├── access-control.md
│   ├── data-freshness.md
│   ├── dimension-standard.md
│   ├── indicator-caliber.md
│   └── naming-convention.md
├── base/            # 基础规范规则 (5个)
│   ├── code-comment.md
│   ├── data-type.md
│   ├── file-naming.md
│   ├── report-format.md
│   └── sql-write.md
└── dynamic/        # 动态规则 (4个)
    ├── holiday-caliber-2026.md
    ├── new-indicator-rule.md
    ├── promotion-caliber.md
    └── test-environment-rule.md
```

## 规则列表 (19个)

### legal (法律级) - 4个
| 规则 | 说明 |
|------|------|
| sensitive-data | 敏感数据合规规则 |
| privacy-protection | 隐私保护规则 |
| data-security | 数据安全规则 |
| export-control | 出口管控规则 |

### core (企业核心) - 4个
| 规则 | 说明 |
|------|------|
| indicator-caliber | 指标口径统一规则 |
| dimension-standard | 维度标准规范 |
| naming-convention | 命名规范 |
| data-freshness | 数据时效规则 |

> ⚠️ 注意：access-control.md 已简化为说明文档，不再包含权限控制逻辑

### base (基础规范) - 5个
| 规则 | 说明 |
|------|------|
| sql-write | SQL编写规范 |
| file-naming | 文件命名规范 |
| report-format | 报告格式规范 |
| code-comment | 代码注释规范 |
| data-type | 数据类型规范 |

### dynamic (动态规则) - 4个
| 规则 | 说明 |
|------|------|
| holiday-caliber-2026 | 2026节假日口径 |
| promotion-caliber | 促销口径规则 |
| new-indicator-rule | 新指标规则 |
| test-environment-rule | 测试环境规则 |

## 校验执行流程

```
1. CLI触发任务
2. 执行legal级规则 → 拦截式，违规终止
3. 执行core级规则 → 前置校验，不一致禁止
4. 执行base级规则 → 提醒式，给出建议
5. 执行dynamic级规则 → 仅在生效期内执行
6. 记录校验日志
```

## 校验触发顺序

CLI执行数分任务前，自动调用rules目录下对应规则，**优先级：legal > core > base > dynamic**

## 调用规范

### 路径格式
```
rules/[级别]/[文件名].md
```

### 调用要求
1. 不可跨级别调用无关规则
2. **动态规则调用**：仅在生效时间范围内，CLI才会调用dynamic目录下的规则，到期自动停止调用并归档
3. 校验结果需记录至操作日志

## 文件统计

- legal: 4个
- core: 5个
- base: 5个
- dynamic: 4个
- **总计: 19个md文件**

## 注意事项

1. legal级规则必须严格遵守，违规会导致任务终止
2. dynamic规则到期后需归档至storage/version/
3. 所有规则校验结果需记录至storage/log/
4. 规则更新需遵循版本管理规范
