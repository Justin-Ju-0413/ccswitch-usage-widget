<div align="center">

# █ TokenTicker

### 你的 AI 用量行情终端

桌面悬浮窗,把 [CC Switch](https://github.com/farion1231/cc-switch) 记录的 AI 用量做成**行情终端**:花费 K 线 + 涨跌幅 + 用量表格,桌面常驻实时刷新,像看股票一样看你的 AI 花费。

[功能](#功能) · [安装](#安装) · [使用](#使用) · [配置](#配置) · [关于开发者](#关于开发者)

</div>

## 功能

- **花费 K 线图**:**5m / 15m / 30m / 1h / 24h / 7d** 六档可切换
  - 每根 K 线 = 一个时间桶,OHLC = 桶内请求花费的首 / 最大 / 最小 / 末
  - 涨红跌绿(A 股风格),当前 K 线黄框,右上角涨跌幅 ▲▼,网格 + Y 轴 4 位小数
- **用量表格**:近 24h + 本月,两级层次(agent 第一级,具体 model 第二级),Token + 花费
- **设置页面**:右键 -> 设置,刷新间隔 / 透明度 / 主题 / 默认范围,持久化到 `~/.ccswitch-widget/settings.json`
- **3 套主题**:Catppuccin Mocha(深)/ Latte(浅)/ Nord
- **桌面常驻**:置顶 + 半透明 + 无边框,可拖动,支持开机自启
- **花费预警**:金额随阈值变色(绿 < $20 / 黄 $20–50 / 红 ≥ $50)

## 数据源

只读 CC Switch 的数据库 `~/.cc-switch/cc-switch.db`(`proxy_request_logs` 代理请求日志 + CLI 会话日志同步)。需先安装并运行 [CC Switch](https://github.com/farion1231/cc-switch) v3.13+。

不联网,不上传,所有计算本地完成。

## 安装

仅需 Python 3.8+(自带 tkinter,无需额外依赖)。

```bash
python ccswitch_widget.py
```

也可打包成单 exe:

```bash
pyinstaller --onefile --noconsole --name TokenTicker ccswitch_widget.py
```

## 使用

| 操作 | 方法 |
|---|---|
| 移动窗口 | 鼠标按住左键拖动 |
| 切换 K 线范围 | 点击 5m / 15m / 30m / 1h / 24h / 7d 按钮 |
| 设置 | 右键 -> 设置(刷新间隔 / 透明度 / 主题 / 默认范围) |
| 刷新 | 右键 -> 立即刷新(或等自动刷新) |
| 退出 | 右键 -> 退出,或按 Esc |

## 开机自启(Windows)

运行 `setup_autostart.ps1` 创建开机自启 + 桌面快捷方式(用 `pythonw.exe` 静默启动,无控制台窗口):

```powershell
powershell -ExecutionPolicy Bypass -File setup_autostart.ps1
```

## 配置

设置保存在 `~/.ccswitch-widget/settings.json`,可直接编辑或通过设置页面修改:

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

## 限制

- 仅 Windows 测试通过(Segoe UI 字体;macOS/Linux 需改字体)
- 依赖 CC Switch 记录的数据;未走代理或未同步会话日志的请求不统计
- K 线 OHLC 基于单请求花费,值很小(0.00x 美元),幅度可能不大;「近 24h」为滚动 24 小时,「本月」为自然月

## 关于开发者

**Justin Ju**(@[Justin-Ju-0413](https://github.com/Justin-Ju-0413))--独立开发者,AI 编码工具重度用户。日常用 CC Switch + Claude Code / Codex,顺手做了 TokenTicker,把散落在各处的 AI 用量数据变成桌面上一眼能看的行情终端。

如果对你有用,欢迎 [Star ⭐](https://github.com/Justin-Ju-0413/ccswitch-usage-widget) 或提 Issue / PR。

## License

MIT © Justin Ju
