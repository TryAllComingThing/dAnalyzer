# 主题定制

## 概述

配置看板的主题样式，包括配色方案、字体、阴影、圆角等视觉元素。

## 主题系统

```yaml
theme:
  system: css-variable  # css-variable/compiled
  default: light
  support: [light, dark, custom]
```

## 预设主题

### 1. 浅色主题 (Light)

```yaml
theme:
  light:
    name: 浅色主题
    colors:
      # 主色
      primary: "#4264F5"
      primaryHover: "#3451D8"
      primaryActive: "#2944C4"
      
      # 背景
      bgBase: "#FFFFFF"
      bgBody: "#F5F6FA"
      bgCard: "#FFFFFF"
      bgHeader: "#FFFFFF"
      bgSidebar: "#F8F9FC"
      
      # 文字
      textPrimary: "#1A1D21"
      textSecondary: "#5C5F66"
      textTertiary: "#9095A0"
      textDisabled: "#C0C2C8"
      
      # 边框
      border: "#E4E5E7"
      borderFocus: "#4264F5"
      
      # 状态
      success: "#0E9F6E"
      warning: "#F5A623"
      error: "#E5484D"
      info: "#3082FE"

    # 图表配色
    chartColors:
      - "#4264F5"
      - "#0E9F6E"
      - "#F5A623"
      - "#E5484D"
      - "#9F70F5"
      - "#3082FE"
      - "#F472C6"
      - "#38BDF8"
```

### 2. 深色主题 (Dark)

```yaml
theme:
  dark:
    name: 深色主题
    colors:
      primary: "#6B7FFF"
      primaryHover: "#8B9AFF"
      primaryActive: "#A5B1FF"
      
      bgBase: "#1A1D21"
      bgBody: "#0F1114"
      bgCard: "#242830"
      bgHeader: "#1A1D21"
      bgSidebar: "#1F2229"
      
      textPrimary: "#F4F4F5"
      textSecondary: "#A1A1AA"
      textTertiary: "#71717A"
      textDisabled: "#52525B"
      
      border: "#3F3F46"
      borderFocus: "#6B7FFF"
      
      success: "#34D399"
      warning: "#FBBF24"
      error: "#F87171"
      info: "#60A5FA"

    chartColors:
      - "#6B7FFF"
      - "#34D399"
      - "#FBBF24"
      - "#F87171"
      - "#C084FC"
      - "#60A5FA"
      - "#F472C6"
      - "#38BDF8"
```

### 3. 企业主题

```yaml
theme:
  corporate:
    name: 企业蓝
    colors:
      primary: "#0052CC"
      primaryHover: "#0747A6"
      bgCard: "#FFFFFF"
      textPrimary: "#172B4D"
    chartColors:
      - "#0052CC"
      - "#36B37E"
      - "#FFAB00"
      - "#FF5630"
```

## 样式配置

### 圆角

```yaml
borderRadius:
  none: 0
  sm: 2px
  md: 4px
  lg: 8px
  xl: 12px
  full: 9999px
```

### 阴影

```yaml
shadow:
  sm: "0 1px 2px rgba(0,0,0,0.05)"
  md: "0 4px 6px -1px rgba(0,0,0,0.1)"
  lg: "0 10px 15px -3px rgba(0,0,0,0.1)"
  xl: "0 20px 25px -5px rgba(0,0,0,0.1)"
```

### 字体

```yaml
font:
  family:
    primary: "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"
    mono: "'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace"
  size:
    xs: 12px
    sm: 13px
    base: 14px
    lg: 16px
    xl: 18px
    2xl: 20px
    3xl: 24px
  weight:
    normal: 400
    medium: 500
    semibold: 600
    bold: 700
```

### 间距

```yaml
spacing:
  xs: 4px
  sm: 8px
  md: 12px
  lg: 16px
  xl: 24px
  2xl: 32px
  3xl: 48px
```

## 自定义主题

```yaml
customTheme:
  name: 我的主题
  extends: light  # 继承基础主题
  overrides:
    colors:
      primary: "#FF6B6B"
      success: "#4ECDC4"
    font:
      family:
        primary: "'Poppins', sans-serif"
    borderRadius:
      md: 8px
```

## 主题切换

```yaml
switching:
  enabled: true
  default: system  # light/dark/system
  persist: true  # 持久化到 localStorage
  options:
    - value: light
      label: 浅色
      icon: sun
    - value: dark
      label: 深色
      icon: moon
    - value: system
      label: 跟随系统
      icon: monitor
```

## 组件主题覆盖

```yaml
componentOverrides:
  kpiCard:
    bgGradient: true
    shadow: lg
    borderRadius: xl
  chart:
    showGrid: false
    legendPosition: bottom
  table:
    stripe: true
    hover: true
    compact: false
```

## 输出

- 主题配置文件
- CSS 变量定义
- 主题切换代码
- 自定义主题编辑器
