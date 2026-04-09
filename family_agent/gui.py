from __future__ import annotations

import os
import threading
from datetime import datetime

from .brain import FamilyBrain
from .hands import AgentHands
from .memory_policy import load_policy
from .voice import VoiceIO


class _GuiDepsError(RuntimeError):
    pass


def _ensure_pyqt6():
    try:
        from PyQt6.QtCore import Qt, pyqtSignal
        from PyQt6.QtWidgets import (
            QApplication,
            QHBoxLayout,
            QLabel,
            QLineEdit,
            QMainWindow,
            QMessageBox,
            QPushButton,
            QTextEdit,
            QVBoxLayout,
            QWidget,
        )
        return {
            "Qt": Qt,
            "pyqtSignal": pyqtSignal,
            "QApplication": QApplication,
            "QHBoxLayout": QHBoxLayout,
            "QLabel": QLabel,
            "QLineEdit": QLineEdit,
            "QMainWindow": QMainWindow,
            "QMessageBox": QMessageBox,
            "QPushButton": QPushButton,
            "QTextEdit": QTextEdit,
            "QVBoxLayout": QVBoxLayout,
            "QWidget": QWidget,
        }
    except Exception as exc:  # pragma: no cover - runtime environment dependent
        raise _GuiDepsError(
            "未安装 PyQt6，请先安装: pip install PyQt6"
        ) from exc


def launch_gui() -> None:
    deps = _ensure_pyqt6()
    Qt = deps["Qt"]
    pyqtSignal = deps["pyqtSignal"]
    QApplication = deps["QApplication"]
    QHBoxLayout = deps["QHBoxLayout"]
    QLabel = deps["QLabel"]
    QLineEdit = deps["QLineEdit"]
    QMainWindow = deps["QMainWindow"]
    QMessageBox = deps["QMessageBox"]
    QPushButton = deps["QPushButton"]
    QTextEdit = deps["QTextEdit"]
    QVBoxLayout = deps["QVBoxLayout"]
    QWidget = deps["QWidget"]

    class MainWindow(QMainWindow):
        append_text = pyqtSignal(str)
        set_busy = pyqtSignal(bool)

        def __init__(self) -> None:
            super().__init__()
            self.setWindowTitle("Family Agent GUI")
            self.resize(980, 700)

            self.brain = FamilyBrain(
                llm_base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
                llm_model=os.getenv("OLLAMA_MODEL", "qwen2.5-coder"),
                embed_model=os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text"),
                memory_db_path=os.getenv("MEMORY_DB_PATH", "./memory_db.sqlite3"),
            )
            self.hands = AgentHands(cwd=os.getcwd())
            self.voice = VoiceIO()
            self._voice_policy = load_policy().get("voice_enabled", True)

            self.append_text.connect(self._append_log)
            self.set_busy.connect(self._set_busy)

            root = QWidget(self)
            self.setCentralWidget(root)
            vbox = QVBoxLayout(root)

            self.status = QLabel(
                f"语音开关(策略): {'开' if self._voice_policy else '关'} | "
                f"STT库: {'有' if self.voice.stt_available else '无'} | "
                f"TTS库: {'有' if self.voice.tts_available else '无'}"
            )
            vbox.addWidget(self.status)

            self.log = QTextEdit()
            self.log.setReadOnly(True)
            self.log.setPlaceholderText("会话日志 / 命令输出")
            vbox.addWidget(self.log, stretch=1)

            row = QHBoxLayout()
            self.input = QLineEdit()
            self.input.setPlaceholderText("输入自然语言，或 /run /gh /memory 命令")
            self.input.returnPressed.connect(self.on_send)
            row.addWidget(self.input, stretch=1)

            self.btn_send = QPushButton("发送")
            self.btn_send.clicked.connect(self.on_send)
            row.addWidget(self.btn_send)

            self.btn_stt = QPushButton("语音转文字")
            self.btn_stt.clicked.connect(self.on_stt)
            row.addWidget(self.btn_stt)

            self.btn_tts = QPushButton("播报最后回复")
            self.btn_tts.clicked.connect(self.on_tts)
            row.addWidget(self.btn_tts)
            vbox.addLayout(row)

            self.last_reply = ""
            self._set_busy(False)
            self._append_log("系统", "Family Agent GUI 已启动。")

            if os.getenv("KAOYAN_MODE", "").lower() in ("1", "true", "yes"):
                from PyQt6.QtCore import QTimer

                def _kaoyan_startup() -> None:
                    from .kaoyan_profile import load_profile, profile_looks_complete, reminder_text

                    prof = load_profile()
                    self.append_text.emit("考研提醒", reminder_text(prof))
                    if not profile_looks_complete(prof):
                        QMessageBox.information(
                            self,
                            "考研档案",
                            "首次使用请在下方输入框发送一行命令完成建档，例如：\n\n"
                            "/kaoyan setup exam_date=2025-12-21 math=120 eng=75 408=120 weak=计组\n\n"
                            "查看档案：/kaoyan show",
                        )

                QTimer.singleShot(200, _kaoyan_startup)

        def _append_log(self, role: str, msg: str = "") -> None:
            if msg == "":
                line = role
            else:
                ts = datetime.now().strftime("%H:%M:%S")
                line = f"[{ts}] {role}: {msg}"
            self.log.append(line)
            self.log.verticalScrollBar().setValue(self.log.verticalScrollBar().maximum())

        def _set_busy(self, busy: bool) -> None:
            self.btn_send.setEnabled(not busy)
            self.btn_stt.setEnabled(not busy)
            self.btn_tts.setEnabled(not busy)
            self.input.setEnabled(not busy)

        def _run_worker(self, text: str) -> None:
            self.set_busy.emit(True)
            self.append_text.emit("你", text)
            try:
                if text.startswith("/run "):
                    cmd = text[5:].strip()
                    res = self.hands.run_shell(cmd)
                    payload = f"[exit={res.code}]\n{res.stdout}\n{res.stderr}".strip()
                    self.append_text.emit("Hands", payload)
                elif text.startswith("/gh "):
                    gh_args = text[4:].strip()
                    res = self.hands.run_github_cli(gh_args)
                    payload = f"[exit={res.code}]\n{res.stdout}\n{res.stderr}".strip()
                    self.append_text.emit("GitHub", payload)
                elif text.startswith("/kaoyan"):
                    out = self._handle_kaoyan_command(text)
                    self.append_text.emit("考研档案", out)
                elif text.startswith("/memory"):
                    out = self._handle_memory_command(text)
                    self.append_text.emit("Memory", out)
                else:
                    reply = self.brain.ask(text)
                    self.last_reply = reply
                    self.append_text.emit("Agent", reply)
            except Exception as exc:
                self.append_text.emit("错误", str(exc))
            finally:
                self.set_busy.emit(False)

        def _handle_memory_command(self, text: str) -> str:
            parts = text.split()
            sub = parts[1] if len(parts) > 1 else ""
            if sub == "top":
                n = int(parts[2]) if len(parts) > 2 else 5
                rows = self.brain.memory_top(n)
                if not rows:
                    return "暂无记忆。"
                lines = []
                for ts, u, a in rows:
                    iso = datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
                    lines.append(f"- [{iso}] U:{u[:50]} | A:{a[:50]}")
                return "\n".join(lines)
            if sub == "search":
                if len(parts) < 3:
                    return "用法: /memory search <kw> [N]"
                n = int(parts[3]) if len(parts) > 3 else 10
                rows = self.brain.memory_search(parts[2], n)
                if not rows:
                    return "未命中。"
                lines = []
                for ts, u, a in rows:
                    iso = datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
                    lines.append(f"- [{iso}] U:{u[:50]} | A:{a[:50]}")
                return "\n".join(lines)
            if sub == "clear":
                count = self.brain.memory_clear()
                return f"已清空 {count} 条。"
            if sub == "export":
                path = parts[2] if len(parts) > 2 else "memory_export.csv"
                count = self.brain.memory_export(path)
                return f"已导出 {count} 条到 {path}"
            return "用法: /memory top [N] | /memory search <kw> [N] | /memory clear | /memory export [file.csv]"

        def _handle_kaoyan_command(self, text: str) -> str:
            from .kaoyan_profile import (
                format_profile_show,
                load_profile,
                parse_setup_kv,
                profile_looks_complete,
                reminder_text,
                save_profile,
            )

            parts = text.split()
            sub = parts[1] if len(parts) > 1 else ""
            if sub == "show":
                prof = load_profile()
                base = format_profile_show(prof)
                if profile_looks_complete(prof):
                    base = reminder_text(prof) + "\n\n" + base
                return base
            if sub == "setup":
                rest = text[len("/kaoyan setup") :].strip()
                if not rest:
                    return (
                        "用法: /kaoyan setup exam_date=YYYY-MM-DD math=数字 eng=数字 408=数字 weak=文字\n"
                        "示例: /kaoyan setup exam_date=2025-12-21 math=120 eng=75 408=120 weak=计组"
                    )
                kv = parse_setup_kv(rest)
                if not kv:
                    return "未解析到 key=value，请检查格式（键值对用空格分隔）。"
                prof = load_profile()
                prof.update(kv)
                prof["setup_done"] = True
                save_profile(prof)
                return "档案已保存。可发送 /kaoyan show 查看倒计时与档案。"
            return "用法: /kaoyan show | /kaoyan setup exam_date=... math=... eng=... 408=... weak=..."

        def on_send(self) -> None:
            text = self.input.text().strip()
            if not text:
                return
            self.input.clear()
            threading.Thread(target=self._run_worker, args=(text,), daemon=True).start()

        def on_stt(self) -> None:
            if not load_policy().get("voice_enabled", True):
                QMessageBox.information(
                    self,
                    "提示",
                    "语音已在「记忆库管理」中关闭，请打开 run_memory_studio.py 勾选语音开关。",
                )
                return
            if not self.voice.stt_available:
                QMessageBox.information(self, "提示", "未检测到 whisper，暂不可用。")
                return
            QMessageBox.information(
                self,
                "提示",
                "当前版本预留了语音接口。你可在下一步接入录音文件选择并调用 speech_to_text。",
            )

        def on_tts(self) -> None:
            if not load_policy().get("voice_enabled", True):
                QMessageBox.information(
                    self,
                    "提示",
                    "语音已在「记忆库管理」中关闭。",
                )
                return
            if not self.last_reply:
                QMessageBox.information(self, "提示", "还没有可播报的回复。")
                return
            if not self.voice.tts_available:
                QMessageBox.information(self, "提示", "未检测到 kokoro，暂不可用。")
                return
            try:
                out = self.voice.text_to_speech(self.last_reply, out_path="last_reply.wav")
                QMessageBox.information(self, "提示", f"已生成语音文件: {out}")
            except Exception as exc:
                QMessageBox.warning(self, "错误", str(exc))

    app = QApplication([])
    window = MainWindow()
    window.show()
    app.exec()
