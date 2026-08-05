# Changelog

## 1.7.0 - Unreleased

- 跨平台适配：macOS 字体自适应（PingFang SC / SF Pro Text）、毛玻璃（可选 pyobjc，自动降级半透明）、无边框窗口交互（NSPanel）
- 数据库路径自适应：手动指定 → CC Switch 自定义配置目录 → 默认路径
- macOS 开机自启（setup_autostart.sh，LaunchAgent）与打包（publish_mac.sh，PyInstaller .app）
- CI 增加 macOS 验证与打包冒烟作业

## 1.6.3

- Improve minimum text sizing and readability.
- Resolve startup shortcut paths from the checked-out repository instead of a developer-specific directory.
- Replace the one-time repository publishing script with a local test, package, and SHA-256 workflow.
- Add database-query, utility, PowerShell parse, and packaging CI checks.
