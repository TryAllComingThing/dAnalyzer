# 实时数据

## 概述

配置看板数据的实时更新机制，包括 WebSocket、轮询、推送等技术方案。

## 更新方式

### 1. WebSocket 长连接

适用于高实时性场景（秒级延迟）。

```yaml
realTime:
  type: websocket
  config:
    url: wss://api.example.com/realtime
    protocols:
      - json
    reconnect:
      enabled: true
      maxAttempts: 5
      delay: 1000  # ms
    heartbeat:
      enabled: true
      interval: 30000  # ms
      message: ping
    messageFormat:
      type: json
      encoding: utf-8
```

**适用场景**：
- 实时交易监控
- 实时流量监控
- 实时预警通知

### 2. HTTP 轮询

适用于低实时性场景（分钟级延迟）。

```yaml
realTime:
  type: polling
  config:
    url: /api/data/refresh
    method: GET
    interval: 30000  # 30秒
    immediate: true
    params:
      dashboardId: ${dashboardId}
    headers:
      Authorization: Bearer ${token}
```

**适用场景**：
- 日报/周报看板
- 运营数据展示
- 报表看板

### 3. Server-Sent Events (SSE)

适用于单向数据推送。

```yaml
realTime:
  type: sse
  config:
    url: /api/stream/events
    lastEventId: ${lastEventId}
    reconnect:
      enabled: true
      delay: 1000
```

**适用场景**：
- 任务进度推送
- 告警通知推送
- 状态变更通知

### 4. 定时刷新

适用于低频更新场景。

```yaml
realTime:
  type: scheduled
  config:
    cron: "0 */5 * * *"  # 每5分钟
    timezone: Asia/Shanghai
    strategy: full  # full/incremental
```

## 刷新策略

### 全量刷新 (Full)

每次请求返回完整数据。

```yaml
refresh:
  strategy: full
  cache:
    enabled: false
```

**优点**：数据一致性好
**缺点**：资源消耗大

### 增量刷新 (Incremental)

只返回变化的数据。

```yaml
refresh:
  strategy: incremental
  cache:
    enabled: true
    key: ${dashboardId}_${componentId}
    ttl: 3600
  diff:
    enabled: true
    fields: [id, update_time]
```

**优点**：性能好，资源消耗小
**缺点**：需要后端支持

## 数据缓存

```yaml
cache:
  enabled: true
  type: memory  # memory/localStorage/sessionStorage
  ttl: 300  # 秒
  maxSize: 50  # MB
  strategy: lru  # lru/fifo
```

## 状态管理

```yaml
state:
  loading:
    show: true
    template: 加载中...
  error:
    show: true
    retry: true
    maxRetries: 3
  empty:
    show: true
    template: 暂无数据
  offline:
    show: true
    message: 网络已断开
    autoReconnect: true
```

## 性能优化

| 优化点 | 方案 |
|--------|------|
| 请求合并 | 多个组件合并为一个请求 |
| 请求去重 | 相同请求在时间窗口内去重 |
| 请求取消 | 组件卸载时取消未完成的请求 |
| 懒加载 | 不在可视区域的组件延迟加载 |
| Web Workers | 大数据处理在 Worker 中 |

```yaml
performance:
  requestMerge:
    enabled: true
    window: 100  # ms
  deduplication:
    enabled: true
    window: 500  # ms
  cancelOnDestroy:
    enabled: true
  lazyLoad:
    enabled: true
    threshold: 200  # px
  webWorker:
    enabled: true
    threshold: 10000  # 数据行数
```

## 错误处理

```yaml
errorHandling:
  retry:
    enabled: true
    maxAttempts: 3
    backoff: exponential  # linear/exponential
    initialDelay: 1000
  fallback:
    enabled: true
    useCache: true
    showError: true
  logging:
    enabled: true
    level: error
```

## 监控指标

```yaml
monitoring:
  metrics:
    - requestCount
    - requestDuration
    - errorCount
    - cacheHitRate
    - dataFreshness
  report:
    enabled: true
    interval: 60000  # ms
    endpoint: /api/metrics
```

## 输出

- 实时配置 JSON
- WebSocket 连接代码
- 轮询调度代码
- 性能监控代码
