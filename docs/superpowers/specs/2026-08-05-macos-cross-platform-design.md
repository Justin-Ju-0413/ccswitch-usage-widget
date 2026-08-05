# TokenTicker macOS 跨平台适配 — 设计文档

- 日期：2026-08-05
- 状态：已批准
- 版本目标：v1.7.0

## 背景

TokenTicker（ccswitch-usage-widget）目前仅在 Windows 上验证过：字体写死 `Segoe UI`、毛玻璃依赖 DWM Acrylic、自启动和打包均为 PowerShell 脚本。用户在 macOS（Apple Silicon，数据库位于默认路径 `~/.cc-switch/cc-switch.db`）上使用，目标是让程序在 macOS 上「装上就能用」，同时保持 Windows 行为不被破坏。

CC Switch 为跨平台 Tauri 应用，数据库默认位于 `~/.cc-switch/cc-switch.db`，但支持自定义配置目录（云同步场景），因此数据库路径需要自适应。

## 范围

本次适配覆盖：

1. 字体自适应（macOS / Windows / Linux 候选字体 + 回退）
2. macOS 毛玻璃（可选依赖 pyobjc，无则降级半透明）
3. macOS 无边框置顶窗口交互（NSPanel 化）
4. 数据库路径自适应（手动指定 → CC Switch settings.json 自定义目录 → 默认路径）
5. macOS 开机自启（LaunchAgent）
6. macOS 打包 .app（PyInstaller）
7. CI 增加 macOS 作业

不涉及：功能特性新增、UI 重构、Windows 脚本改动。

## 架构

新增 `platform_compat.py` 模块，集中所有平台差异。`ccswitch_widget.py` 只通过适配层调用平台能力，Windows 行为不变。

```
ccswitch_widget.py       主文件（改动：字体/DB 路径改从适配层读取，窗口初始化走适配层）
platform_compat.py       新增：平台检测 + 字体选择 + 毛玻璃 + 窗口行为 + DB 探测
setup_autostart.sh       新增：macOS LaunchAgent 安装/卸载
publish_mac.sh           新增：macOS PyInstaller 打包 + sha256
tests/                   新增 platform_compat 测试
.github/workflows/ci.yml 增加 macos-latest 作业
```

## 详细设计

### 1. 字体自适应

`platform_compat` 提供 `select_font()`，返回 `(family, fallback_family)`：

- 平台候选列表：
  - macOS: `PingFang SC` → `SF Pro Text` → `Helvetica Neue` → 系统默认
  - Windows: `Segoe UI`（原样）
  - Linux: `Noto Sans CJK SC` → `WenQuanYi Micro Hei` → 系统默认
- 用 `tkinter.font.families()` 探测可用性，缺失自动回退。
- 全局 `F` 由 `select_font()` 的结果设置。
- 无 Tk root 时的探测逻辑与有 root 时分离（便于单元测试）。

### 2. macOS 毛玻璃（可选依赖）

- `try_mac_frost(root)`：通过 pyobjc（`pyobjc-framework-Cocoa`）创建 `NSVisualEffectView`，`material = NSVisualEffectMaterialHudWindow`，`blendingMode = behindWindow`，作为窗口 contentView 的背景，同时把窗口背景设为透明。
- 依赖策略：**可选**。`requirements.txt` 中注释标注 macOS 可选依赖；代码 `try: import Cocoa` 失败即降级。
- 降级链：macOS 毛玻璃 → Windows Acrylic（原 `try_acrylic`）→ `-alpha` 半透明（现有逻辑）。各分支互不影响。

### 3. macOS 无边框窗口交互

- macOS 上 `overrideredirect(True)` 窗口默认不接收键盘焦点，右键菜单无法弹出。
- 适配：macOS 下用 pyobjc 将底层 NSWindow 转为 borderless `NSPanel`：
  - `styleMask = NSWindowStyleMaskBorderless`
  - `level = NSFloatingWindowLevel`
  - `collectionBehavior = NSWindowCollectionBehaviorCanJoinAllSpaces`
  - 显式 `makeKeyAndOrderFront` 保证可交互。
- 无 pyobjc 时保持现有 overrideredirect 行为（可见但交互受限，与当前一致）。
- 拖动（bind_all 拖拽）在 macOS 上复用现有实现。

### 4. 数据库路径自适应

`platform_compat.resolve_db_path(cfg)` 探测顺序：

1. 配置 `db_path` 非空 → 使用（无条件优先，即使文件暂不存在）
2. 解析 CC Switch 的 `~/.cc-switch/settings.json`，若含自定义配置目录且目录下有 `cc-switch.db` → 使用
3. 默认 `~/.cc-switch/cc-switch.db`
4. 均未命中 → 返回默认路径（启动报错逻辑不变，报错文案附上探测到的路径清单）

设置窗口新增「数据库路径」输入框 + 「浏览…」按钮（`tkinter.filedialog.askopenfilename`），保存时写入 `cfg["db_path"]`。

### 5. macOS 开机自启

`setup_autostart.sh`：

- 默认模式：写入 `~/Library/LaunchAgents/com.tokenticker.widget.plist`，`ProgramArguments` 指向打包后的 `.app`（若存在）或 `pythonw` + 脚本绝对路径，`RunAtLoad = true`
- `--uninstall`：移除 plist 并 `launchctl unload`（如已加载）
- 幂等：重复运行提示已安装

Windows `setup_autostart.ps1` 不改动。

### 6. macOS 打包

`publish_mac.sh`：

- `pyinstaller --onefile --windowed --name TokenTicker --collect-all customtkinter --osx-bundle-identifier com.tokenticker.widget ccswitch_widget.py`
- 输出 `dist/TokenTicker.app`（或 onefile），生成 `dist/TokenTicker.app.sha256`
- 仅本地打包与校验，不推送、不创建 Release（与 `publish.ps1` 语义一致）

### 7. 测试与 CI

新增测试：

- `tests/test_platform_compat.py`：
  - 字体候选列表按平台返回正确值、无 Tk 环境不崩溃
  - DB 探测：手动指定优先、settings.json 自定义目录解析、默认路径回退
  - macOS 毛玻璃/窗口函数在非 macOS 上安全返回（不调用 pyobjc）
- 现有测试全部保持通过

CI（`.github/workflows/ci.yml`）：

- 新增 `macos-latest` 作业：unittest + `py_compile` + PyInstaller 打包冒烟（无头环境仅验证构建成功）
- Windows 作业保持不变

## 风险与回退

| 风险 | 影响 | 缓解 |
|---|---|---|
| macOS 无边框窗口交互不可行（NSPanel 方案） | 右键菜单/设置无法使用 | 无 pyobjc 时保持现状；方案失败则文档记录，退回 overrideredirect |
| pyobjc 在打包 .app 中体积增大 | 安装包变大 | 可接受；毛玻璃为可选能力 |
| CC Switch settings.json 结构变化 | DB 探测失效 | 探测容错（任何解析异常都跳过该候选） |
| Segoe UI 图标字符（▲▼█●└）在 PingFang 缺字形 | 显示豆腐块 | 选型时以 PingFang SC 为主，测试中人工确认 |

回退：v1.6.3 已打 tag；Windows 路径无行为变更，可随时回退。

## 验证方式

1. 本机 macOS：`python ccswitch_widget.py` 正常显示、刷新、右键菜单、设置、拖动
2. 无 pyobjc 环境：毛玻璃降级为半透明，其余功能正常
3. 数据库路径：临时改 settings.json 自定义目录后重启，数据仍能读取
4. `python -m unittest discover -s tests -v` 全绿
5. CI：macOS + Windows 双作业通过
