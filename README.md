# CC Switch 用量 Widget

桌面悬浮窗,可视化 [CC Switch](https://github.com/farion1231/cc-switch) 记录的 AI 用量:近 24h / 本月 Token 与花费(按 Claude / Codex 分项)+ 时间范围可切换的花费柱状图 + 内置设置页面。

## 功能

- **用量表格**:近 24h + 本月,两级层次(agent 第一级,具体 model 第二级),显示 Token 和花费
- **花费柱状图**:**1h / 24h / 7d 三档可切换**,按 5 分钟 / 1 小时 / 1 天分桶,Claude(紫)/ Codex(青)堆叠,**当前时刻黄边框高亮**
- **设置页面**:右键 -> 设置,可调刷新间隔、窗口透明度、主题、默认时间范围,持久化到 `~/.ccswitch-widget/settings.json`
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

## 使用

| 操作 | 方法 |
|---|---|
| 移动窗口 | 鼠标按住左键拖动 |
| 切换柱状图范围 | 点击柱状图上方 1h / 24h / 7d 按钮 |
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
  "win_h": 680
}
```

## 限制

- 仅 Windows 测试通过(Segoe UI 字体;macOS/Linux 需改字体)
- 依赖 CC Switch 记录的数据;未走代理或未同步会话日志的请求不统计
- 「近 24h」为滚动 24 小时;「本月」为自然月

## License

MIT © Justin Ju
