from __future__ import annotations

import datetime
import sqlite3
import sys
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.modules.setdefault("customtkinter", MagicMock())
# 仅在真实 tkinter 不可用时 mock：若本机有 tkinter（如 brew python3.12），
# 保留真实模块，否则同进程加载 tests.test_platform_compat 时其
# `import tkinter.font` 会因 sys.modules 污染而失败。
try:
    import tkinter.font  # noqa: F401
except ImportError:
    sys.modules["tkinter"] = MagicMock()
import ccswitch_widget as widget


class WidgetTests(unittest.TestCase):
    def test_token_formatting_and_cost_thresholds(self) -> None:
        self.assertEqual(widget.fmt_tok(1_250), "1.2K")
        self.assertEqual(widget.fmt_tok(2_000_000), "2.00M")
        theme = widget.THEMES["Mocha"]
        self.assertEqual(widget.cost_color(19.99, theme), theme["green"])
        self.assertEqual(widget.cost_color(20, theme), theme["yellow"])
        self.assertEqual(widget.cost_color(50, theme), theme["red"])

    def test_query_reads_cc_switch_database_without_writing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database = Path(temp_dir) / "cc-switch.db"
            # sqlite3.Connection's context manager commits/rolls back but does
            # not close the handle. Windows refuses to delete the temporary
            # database while that handle is still open.
            with closing(sqlite3.connect(database)) as connection:
                connection.executescript(
                    """
                    CREATE TABLE proxy_request_logs (
                        created_at INTEGER, app_type TEXT, model TEXT,
                        total_cost_usd TEXT, input_tokens INTEGER,
                        output_tokens INTEGER, cache_read_tokens INTEGER,
                        cache_creation_tokens INTEGER, provider_id INTEGER
                    );
                    CREATE TABLE providers (
                        id INTEGER, app_type TEXT, name TEXT, is_current INTEGER
                    );
                    """
                )
                now = int(datetime.datetime.now().timestamp())
                connection.execute(
                    "INSERT INTO providers VALUES (1, 'claude', 'Local', 1)"
                )
                connection.execute(
                    "INSERT INTO proxy_request_logs VALUES (?, 'claude', 'model-a', '0.5', 10, 20, 30, 40, 1)",
                    (now,),
                )
                connection.commit()

            with patch.object(widget, "DB", str(database)):
                result = widget.query("24h")

            self.assertEqual(result["today"], (0.5, 100))
            self.assertEqual(result["providers"], [("claude", "Local")])
            self.assertEqual(result["latest"], ("Local", "model-a"))
            with closing(sqlite3.connect(database)) as connection:
                self.assertEqual(connection.execute("PRAGMA integrity_check").fetchone()[0], "ok")


class RuntimeResolutionTests(unittest.TestCase):
    def test_resolve_runtime_updates_db_and_font(self):
        with patch.object(widget.pc, "resolve_db_path", return_value="/tmp/x/cc-switch.db"), \
             patch.object(widget.pc, "resolve_font", return_value="PingFang SC"):
            widget.resolve_runtime(MagicMock(), {"db_path": "/tmp/x/cc-switch.db"})
        self.assertEqual(widget.DB, "/tmp/x/cc-switch.db")
        self.assertEqual(widget.F, "PingFang SC")

    def test_resolve_runtime_keeps_default_font_when_unresolvable(self):
        with patch.object(widget.pc, "resolve_db_path", return_value="/tmp/y/cc-switch.db"), \
             patch.object(widget.pc, "resolve_font", return_value=None):
            widget.resolve_runtime(MagicMock(), {})
        self.assertEqual(widget.F, "Segoe UI")


if __name__ == "__main__":
    unittest.main()
