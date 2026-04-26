# 导出分享

## 概述

配置看板的导出和分享功能，支持多种格式导出、链接分享、嵌入等。

## 导出格式

### 1. PDF 导出

```yaml
export:
  pdf:
    enabled: true
    config:
      orientation: portrait  # portrait/landscape
      paperSize: A4  # A4/Letter
      margins:
        top: 20
        right: 20
        bottom: 20
        left: 20
      header:
        enabled: true
        template: "{{dashboardName}} - {{date}}"
      footer:
        enabled: true
        template: "第 {{page}} 页，共 {{totalPages}} 页"
      quality: high  # standard/high
      compression: true
      watermark:
        enabled: false
        text: "Confidential"
        opacity: 0.1
      charts:
        rasterize: true
        dpi: 300
```

### 2. Excel 导出

```yaml
export:
  excel:
    enabled: true
    config:
      sheets:
        - name: 核心指标
          range: A1:D5
          dataType: kpi
        - name: 趋势数据
          range: A1:Z100
          dataType: chart
        - name: 明细数据
          dataType: table
      formatting:
        headerStyle:
          bgColor: "#4264F5"
          fontColor: "#FFFFFF"
          bold: true
        dataStyle:
          numberFormat: "#,##0.00"
          dateFormat: "yyyy-mm-dd"
      formulas: true
      charts: true
      images: true
```

### 3. 图片导出

```yaml
export:
  image:
    enabled: true
    formats:
      - type: png
        config:
          width: 1920
          height: 1080
          dpi: 300
          quality: 1.0
          background: "#FFFFFF"
      - type: jpeg
        config:
          quality: 0.9
      - type: svg
        config:
          embeddedFonts: true
```

### 4. HTML 导出

```yaml
export:
  html:
    enabled: true
    config:
      inlineCSS: true
      inlineJS: false
      minify: true
      addTimestamp: true
      responsive: true
```

### 5. PPT 导出

```yaml
export:
  pptx:
    enabled: false  # 需扩展
    config:
      template: corporate
      layout: titleAndContent
      chartsAsImage: true
```

## 分享功能

### 1. 链接分享

```yaml
share:
  link:
    enabled: true
    config:
      urlPattern: "https://danalyzer.app/d/{dashboardId}?token={token}"
      token:
        type: jwt  # jwt/uuid/static
        expiresIn: 7d
        maxUses: unlimited  # unlimited/number
      access:
        view: true
        export: false
        edit: false
```

### 2. 嵌入分享

```yaml
share:
  embed:
    enabled: true
    config:
      iframe:
        allow: "fullscreen"
        width: 100%
        height: 600
      parameters:
        - name: theme
          values: [light, dark]
        - name: language
          values: [zh, en]
      security:
        allowedDomains:
          - "*.example.com"
        frameAncestors:
          - "https://app.example.com"
```

### 3. 邮件分享

```yaml
share:
  email:
    enabled: true
    config:
      subject: "{{userName}} 与您分享了 {{dashboardName}}"
      body: |
        {{userName}} 分享了一个数据分析看板给您：

        看板名称：{{dashboardName}}
        分享时间：{{shareTime}}

        点击链接查看：{{dashboardUrl}}
      recipients:
        max: 50
      attachment:
        enabled: true
        formats: [pdf, png]
```

## 权限控制

```yaml
share:
  permissions:
    allowExport: role:editor,role:admin
    allowShare: role:admin
    allowEmbed: role:admin
    allowPublicLink: false
    requireApproval: true  # 分享需审批
```

## 导出历史

```yaml
history:
  enabled: true
  storage: database  # database/s3
  retention: 90d
  fields:
    - exportId
    - dashboardId
    - userId
    - format
    - timestamp
    - fileSize
    - downloadUrl
    - expiresAt
```

## 输出

- 导出功能代码
- 分享功能代码
- 权限控制代码
- 导出历史查询
