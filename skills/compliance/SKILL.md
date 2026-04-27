---
name: compliance
description: 合规检查技能，用于数据导出、报表生成时的合规校验，确保符合法律法规和企业政策。
tools: ["Read", "Grep", "Bash"]
model: sonnet
required: true
---

# Compliance Check Skill

## 核心职责

- 数据脱敏合规检查
- 隐私保护合规校验
- 导出权限检查
- 敏感字段识别
- 合规规则匹配

## 适用场景

- 数据导出前检查
- 报表生成合规审核
- 用户数据访问控制
- 批量数据处理

## 合规规则

### 1. 个人信息识别

```
必须脱敏字段:
- 身份证号: 18位身份证 → 前6位+后4位 (其余***)
- 手机号: 11位手机 → 138****5678
- 银行卡号: 16-19位 → 前4位+****+后4位
- 姓名: 2字姓名 → 张* ; 3字姓名 → 张*某
- 邮箱: 完整邮箱 → xxx***@domain.com
- 地址: 详细地址 → 省市+***(模糊化)
```

### 2. 数据分级

```
数据敏感等级:
- L1 公开数据: 可导出 (如统计数据)
- L2 内部数据: 需审批 (如运营数据)
- L3 敏感数据: 需脱敏 (如用户基本信息)
- L4 机密数据: 禁止导出 (如交易明细)
```

### 3. 权限检查

```
导出权限矩阵:
| 角色       │ L1  │ L2  │ L3  │ L4  │
├────────────┼─────┼─────┼─────┼─────┤
│ 普通用户   │ ✓   │ ✗   │ ✗   │ ✗   │
│ 运营       │ ✓   │ ✓   │ ✗   │ ✗   │
│ 分析师     │ ✓   │ ✓   │ ✓   │ ✗   │
│ 管理员     │ ✓   │ ✓   │ ✓   │ ✓   │
│ 审计       │ ✓   │ ✓   │ ✓   │ ✓ (仅查看)│
```

## 输入要求

| 字段 | 必填 | 说明 |
|------|------|------|
| operation | 是 | 操作类型 (export/generate/query) |
| data_type | 是 | 数据类型 |
| fields | 是 | 涉及字段列表 |
| user_role | 是 | 用户角色 |
| target | 是 | 目标对象 (table/file/user) |

## 执行逻辑

### 1. 字段扫描

```
检查步骤:
1. 读取字段定义
2. 匹配敏感字段规则
3. 识别需要脱敏的字段
4. 生成脱敏策略
```

### 2. 脱敏处理

```python
# 脱敏规则示例
def mask_sensitive(data: dict, rules: dict) -> dict:
    result = data.copy()

    for field, rule in rules.items():
        if field in result:
            value = result[field]
            if rule == "id_card":
                result[field] = f"{value[:6]}****{value[-4:]}"
            elif rule == "phone":
                result[field] = f"{value[:3]}****{value[-4:]}"
            elif rule == "name":
                result[field] = f"{value[0]}*{value[-1]}" if len(value) > 2 else f"{value[0]}*"

    return result
```

### 3. 合规判定

```
判定结果:
- PASS: 完全合规，可直接执行
- MASK: 需要脱敏后可执行
- APPROVE: 需要审批后执行
- DENY: 禁止执行
```

## 输出结果

### 标准输出格式

```json
{
  "operation": "export",
  "data_type": "user_orders",
  "compliance_status": "MASK",
  "sensitive_fields": [
    {
      "field": "user_phone",
      "sensitivity": "L3",
      "mask_rule": "phone",
      "action": "required_mask"
    },
    {
      "field": "user_id_card",
      "sensitivity": "L4",
      "mask_rule": "id_card",
      "action": "deny_export"
    }
  ],
  "export_permission": {
    "allowed": false,
    "reason": "包含L4级别敏感字段",
    "required_actions": [
      "移除 user_id_card 字段",
      "对 user_phone 进行脱敏"
    ],
    "approval_required": true
  },
  "masked_data_example": {
    "user_id": "U10001",
    "user_phone": "138****5678",
    "order_amount": 599.00
  },
  "compliance_report": {
    "checked_fields": 12,
    "sensitive_count": 2,
    "mask_applied": 1,
    "blocked": 1,
    "passed": 9
  }
}
```

## 合规规则来源

### 1. 法律级规则 (最高优先级)

- 《个人信息保护法》
- 《数据安全法》
- 《网络安全法》
- 行业特定法规

### 2. 企业级规则

- 数据分类分级标准
- 隐私保护政策
- 员工数据访问规范

### 3. 动态规则

- 临时合规要求
- 特定活动规则
- 地区特殊规定

## 与其他技能协同

| 技能 | 协同方式 |
|------|----------|
| data-query | 检查查询权限 |
| security | 执行脱敏操作 |
| data-quality-check | 验证脱敏效果 |

## 注意事项

1. 脱敏不可逆，导出后无法还原
2. 不同地区法规有差异
3. 定期更新敏感字段规则
4. 保留脱敏审计日志

## 示例查询

```
"检查这个用户数据导出是否合规"
"订单数据导出需要哪些脱敏处理"
"查询用户手机号是否需要脱敏"
"验证这批数据是否符合隐私保护要求"
```
