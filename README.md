<div align="center">

# 📈 TokenTicker

### 你的 AI 用量行情终端

<p>
  <a href="https://github.com/Justin-Ju-0413/ccswitch-usage-widget">
    <img src="https://img.shields.io/github/stars/Justin-Ju-0413/ccswitch-usage-widget?style=social" alt="stars" />
  </a>
  <img src="https://img.shields.io/badge/Python-3.8+-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/Windows-0078D6?style=flat-square&logo=windows&logoColor=white" alt="Windows" />
  <img src="https://img.shields.io/badge/License-MIT-yellow?style=flat-square" alt="license" />
</p>

桌面悬浮窗，把 [CC Switch](https://github.com/farion1231/cc-switch) 记录的 AI 用量做成**行情终端**：
<br>花费 K 线 + 涨跌幅 + 用量表格，桌面常驻实时刷新，像看股票一样看你的 AI 花费。

[功能特性](#-功能特性) · [快速开始](#-快速开始) · [操作指南](#-操作指南) · [配置说明](#-配置说明)

</div>

## ✨ 功能特性

### 🕯️ K 线图 — 像看股票一样看 AI 花费
- **6 档时间范围**：5m / 15m / 30m / 1h / 24h / 7d 一键切换
- **标准 OHLC**：每根 K 线 = 一个时间桶，开盘/最高/最低/收盘 = 桶内首/最大/最小/末花费
- **A 股风格配色**：涨红跌绿，当前 K 线黄框高亮
- **实时涨跌幅**：右上角 ▲▼ 显示当前区间涨跌幅
- **精细刻度**：Y 轴 4 位小数，网格线辅助读数

### 📋 用量表格 — 钱花在哪一目了然
- **两级层次**：agent 第一级，具体 model 第二级，折叠展开
- **两个维度**：近 24h + 本月，Token 数 + 花费金额
- **花费预警**：金额随阈值变色（🟢 < $20 / 🟡 $20–50 / 🔴 ≥ $50）

### 🖼️ 桌面悬浮 — 常驻不打扰
- **液态玻璃风格**：customtkinter 圆角卡片 + 半透明 + 亮边
- **三套主题**：Mocha (深) / Latte (浅) / Nord
- **置顶 + 无边框 + 可拖动**，透明度可调
- **开机自启**：用 `pythonw.exe` 静默启动，无控制台窗口

### ⚙️ 高度可配置
- 刷新间隔 / 透明度 / 主题 / 默认范围 / 窗口大小
- 持久化到 `~/.ccswitch-widget/settings.json`
- 右键菜单快速操作

### 🔒 纯本地计算
- 只读 CC Switch 的数据库，不联网、不上传
- 所有计算在本地完成，数据不出电脑

## 🚀 快速开始

### 前置要求
- 已安装并运行 [CC Switch](https://github.com/farion1231/cc-switch) **v3.13+**
- Python 3.8+

### 运行

```bash
pip install customtkinter
python ccswitch_widget.py
```

### 打包成 exe（可选）

```bash
pyinstaller --onefile --noconsole --name TokenTicker --collect-all customtkinter ccswitch_widget.py
```

### 开机自启（Windows）

运行 `setup_autostart.ps1` 创建开机自启 + 桌面快捷方式：

```powershell
powershell -ExecutionPolicy Bypass -File setup_autostart.ps1
```

## 🎮 操作指南

| 操作 | 方法 |
|---|---|
| 移动窗口 | 鼠标按住左键拖动 |
| 切换 K 线范围 | 点击 5m / 15m / 30m / 1h / 24h / 7d 按钮 |
| 打开设置 | 右键 → 设置 |
| 立即刷新 | 右键 → 立即刷新（或等自动刷新） |
| 退出 | 右键 → 退出，或按 Esc |

## ⚙️ 配置说明

设置保存在 `~/.ccswitch-widget/settings.json`，可直接编辑或通过设置页面修改：

```json
{
  "refresh_ms": 30000,
  "alpha": 0.95,
  "theme": "Mocha",
  "default_range": "24h",
  "win_w": 440,
  "win_h": 700
}
```

## 📊 数据源

只读 CC Switch 的数据库文件 `~/.cc-switch/cc-switch.db`：
- `proxy_request_logs` — 代理请求日志
- CLI 会话日志同步

> 未走 CC Switch 代理、或未同步会话日志的请求不会被统计。

## ⚠️ 已知限制

- 仅 Windows 测试通过（Segoe UI 字体；macOS / Linux 需改字体）
- K 线 OHLC 基于单请求花费，值很小（0.00x 美元），幅度可能不大
- 「近 24h」为滚动 24 小时，「本月」为自然月

## 👤 关于开发者

**Justin Ju** ([@Justin-Ju-0413](https://github.com/Justin-Ju-0413)) — 独立开发者，AI 编码工具重度用户。
日常用 CC Switch + Claude Code / Codex，顺手做了 TokenTicker，把散落在各处的 AI 用量数据变成桌面上一眼能看的行情终端。

如果对你有用，欢迎 ⭐ Star 或提 Issue / PR！

## 📄 License

MIT © Justin Ju
