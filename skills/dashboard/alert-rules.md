# 告警规则

## 概述

配置看板的告警监控规则，支持阈值告警、异常检测、通知推送等功能。

## 告警类型

### 1. 阈值告警

当指标超过/低于设定阈值时触发。

```yaml
alert:
  name: sales_low_alert
  type: threshold
  enabled: true
  metric: daily_sales
  condition:
    operator: lt  # lt/gt/lte/gte/eq/ne
    value: 10000
    unit: yuan
  evaluation:
    period: 5m  # 持续5分钟
    interval: 1m  # 每1分钟检查一次
    aggregation: avg  # avg/sum/min/max
  severity: critical  # critical/warning/info
```

### 2. 变化率告警

当指标变化幅度超过阈值时触发。

```yaml
alert:
  name: traffic_surge_alert
  type: change_rate
  enabled: true
  metric: hourly_traffic
  condition:
    operator: gt
    value: 50
    unit: percent
    direction: both  # both/up/down
  evaluation:
    period: 10m
    interval: 2m
    compare:
      type: relative  # relative(环比)/absolute(同比)
      period: 1h
  severity: warning
```

### 3. 异常检测告警

基于历史数据自动检测异常。

```yaml
alert:
  name: anomaly_detection
  type: anomaly
  enabled: true
  metric: transaction_count
  condition:
    method: isolation_forest  # isolation_forest/zscore
    threshold: 3  # 标准差倍数
    sensitivity: medium  # low/medium/high
  evaluation:
    period: 15m
    interval: 5m
    history:
      days: 30
      minSamples: 100
  severity: critical
```

### 4. 趋势告警

当指标趋势持续下降/上升时触发。

```yaml
alert:
  name: downward_trend_alert
  type: trend
  enabled: true
  metric: daily_orders
  condition:
    direction: down  # up/down
    points: 5  # 连续N个点
    minChange: -10  # 最小变化幅度
  evaluation:
    period: 1h
    interval: 10m
  severity: warning
```

## 告警条件

| 条件类型 | 说明 | 适用场景 |
|----------|------|----------|
| threshold | 阈值比较 | 销售额低于X |
| change_rate | 变化率 | 流量波动超过X% |
| anomaly | 异常检测 | 数据异常 |
| trend | 趋势告警 | 连续下降 |
| composite | 复合条件 | 多条件组合 |

## 告警级别

| 级别 | 颜色 | 说明 | 默认动作 |
|------|------|------|----------|
| critical | 红色 | 紧急，需立即处理 | 电话+短信+邮件 |
| warning | 橙色 | 警告，需关注 | 短信+邮件 |
| info | 蓝色 | 提示，信息 | 邮件 |

## 通知渠道

### 1. 邮件

```yaml
notification:
  channels:
    - type: email
      enabled: true
      config:
        to:
          - manager@example.com
        cc:
          - director@example.com
        subject: "[告警] 销售数据异常"
        template: alert-email-template
        priority: high
```

### 2. 钉钉

```yaml
notification:
  channels:
    - type: dingtalk
      enabled: true
      config:
        webhook: https://oapi.dingtalk.com/robot/send?access_token=xxx
        secret: xxx
        msgtype: markdown
        atMobiles:
          - 13800138000
        isAtAll: false
```

### 3. 短信

```yaml
notification:
  channels:
    - type: sms
      enabled: true
      config:
        template: 告警通知
        phones:
          - 13800138000
        sign: dAnalyzer
```

### 4. Slack

```yaml
notification:
  channels:
    - type: slack
      enabled: true
      config:
        webhook: https://hooks.slack.com/services/xxx
        channel: "#alerts"
        username: dAnalyzer Alert
        iconEmoji: :warning:
```

### 5. Webhook

```yaml
notification:
  channels:
    - type: webhook
      enabled: true
      config:
        url: https://api.example.com/webhook
        method: POST
        headers:
          Authorization: Bearer xxx
        retry:
          enabled: true
          maxAttempts: 3
```

## 告警抑制

避免告警风暴，同一问题只发送一次通知。

```yaml
suppression:
  enabled: true
  rules:
    - name: same_alert_cooldown
      description: 同一告警30分钟内不重复发送
      condition:
        sameMetric: true
        sameAlertId: true
      duration: 30m
    - name: alert_grouping
      description: 多个类似告警合并为一条
      condition:
        metricPattern: "sales.*"
        timeWindow: 5m
      mergeStrategy: summary
```

## 告警升级

告警未处理时自动升级。

```yaml
escalation:
  enabled: true
  rules:
    - name: unhandled_escalation
      description: 告警30分钟未处理自动升级
      condition:
        status: triggered
        duration: 30m
      actions:
        - level: warning
          notify: supervisor
        - level: critical
          duration: 60m
          notify: manager
```

## 告警历史

```yaml
history:
  storage:
    type: database  # database/elasticsearch
    retention: 90d  # 保留90天
  fields:
    - alertId
    - alertName
    - metric
    - value
    - threshold
    - condition
    - severity
    - status  # triggered/resolved/acknowledged
    - triggeredAt
    - resolvedAt
    - acknowledgedBy
    - notificationChannels
    - responseTime
```

## 输出

- 告警规则配置 JSON
- 告警通知代码
- 告警历史查询接口
- 告警Dashboard组件
