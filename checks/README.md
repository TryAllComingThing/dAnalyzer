# 自动化校验钩子 (checks)

## 目录用途

自动化校验钩子，CLI前置/后置触发，用于规避风险、确保数据质量。主要包括：

- **数据质量校验（data-quality）**：空值、异常值、重复值、断层检测
- **口径校验（caliber）**：指标口径一致性、维度统一性、版本一致性
- **合规校验（compliance）**：敏感数据、违规输出、扫描逻辑

## 目录结构

```
checks/
├── data-quality/        # 数据质量校验 (7个)
│   ├── data-quality-check.md
│   ├── null-check.md
│   ├── abnormal-check.md
│   ├── duplicate-check.md
│   ├── continuity-check.md
│   ├── type-check.md
│   └── README.md
├── caliber/             # 口径校验 (4个)
│   ├── caliber-consistency-check.md
│   ├── dimension-consistency-check.md
│   ├── calculation-logic-check.md
│   ├── version-consistency-check.md
│   └── README.md
├── compliance/           # 合规校验 (4个)
│   ├── compliance-scan.md
│   ├── sensitive-data-scan.md
│   ├── output-format-check.md
│   ├── authorization-check.md
│   └── README.md
└── README.md
```

## 校验列表 (15个)

### data-quality (数据质量) - 7个
| 校验 | 说明 |
|------|------|
| data-quality-check | 数据质量总检 |
| null-check | 空值检测 |
| abnormal-check | 异常值检测 |
| duplicate-check | 重复值检测 |
| continuity-check | 连续性检测 |
| type-check | 数据类型检测 |

### caliber (口径校验) - 4个
| 校验 | 说明 |
|------|------|
| caliber-consistency-check | 指标口径一致性 |
| dimension-consistency-check | 维度一致性 |
| calculation-logic-check | 计算逻辑一致性 |
| version-consistency-check | 版本一致性 |

### compliance (合规校验) - 4个
| 校验 | 说明 |
|------|------|
| compliance-scan | 合规扫描 |
| sensitive-data-scan | 敏感数据扫描 |
| output-format-check | 输出格式检查 |
| authorization-check | 授权检查 |

## 校验执行流程

### 前置校验流程
```
1. CLI触发任务
2. 调用checks前置校验
3. 校验通过 → 继续执行
4. 校验失败 → 按规则处理（预警/终止）
```

### 后置校验流程
```
1. 任务执行完成
2. 调用checks后置校验
3. 校验通过 → 输出结果
4. 校验失败 → 按规则处理（预警/终止/删除）
```

## 调用规范

### 路径格式
```
checks/[校验类型]/[文件名].md
```

### 调用时机
- **前置校验**：任务执行前触发，确保输入数据符合要求
- **后置校验**：任务执行后触发，确保输出结果符合规范
- 校验失败需输出明确提示，可选择：预警/终止/继续

### 调用要求
1. 校验失败时，根据校验类型决定处理方式
2. 校验结果需记录至storage/log/
3. 合规校验违规时**必须终止任务**

## 文件统计

- data-quality: 7个
- caliber: 4个
- compliance: 4个
- **总计: 15个md文件**

## 注意事项

1. 合规校验违规必须终止任务并删除输出
2. 数据质量校验支持自动处理（剔除重复等）
3. 口径校验依赖指标字典资产
4. 所有校验日志需记录至storage/log/
