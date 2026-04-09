"""记忆库管理界面：查看/编辑/删除记忆，配置禁止记忆规则、语音开关、授权目录扫描（排除微信路径）。"""

from __future__ import annotations

import os
from datetime import datetime

from brain_with_memory import BrainWithMemory


class _StudioDepsError(RuntimeError):
    pass


def _ensure_pyqt6():
    try:
        from PyQt6.QtCore import Qt
        from PyQt6.QtWidgets import (
            QAbstractItemView,
            QApplication,
            QCheckBox,
            QComboBox,
            QDialog,
            QDialogButtonBox,
            QFileDialog,
            QHBoxLayout,
            QLabel,
            QLineEdit,
            QListWidget,
            QMainWindow,
            QMessageBox,
            QPushButton,
            QTabWidget,
            QTableWidget,
            QTableWidgetItem,
            QTextEdit,
            QVBoxLayout,
            QWidget,
        )

        return {
            "Qt": Qt,
            "QApplication": QApplication,
            "QAbstractItemView": QAbstractItemView,
            "QComboBox": QComboBox,
            "QFileDialog": QFileDialog,
            "QCheckBox": QCheckBox,
            "QDialog": QDialog,
            "QDialogButtonBox": QDialogButtonBox,
            "QHBoxLayout": QHBoxLayout,
            "QLabel": QLabel,
            "QLineEdit": QLineEdit,
            "QListWidget": QListWidget,
            "QMainWindow": QMainWindow,
            "QMessageBox": QMessageBox,
            "QPushButton": QPushButton,
            "QTabWidget": QTabWidget,
            "QTableWidget": QTableWidget,
            "QTableWidgetItem": QTableWidgetItem,
            "QTextEdit": QTextEdit,
            "QVBoxLayout": QVBoxLayout,
            "QWidget": QWidget,
        }
    except Exception as exc:
        raise _StudioDepsError("未安装 PyQt6，请先安装: pip install PyQt6") from exc


def launch_memory_studio() -> None:
    deps = _ensure_pyqt6()
    Qt = deps["Qt"]
    QApplication = deps["QApplication"]
    QAbstractItemView = deps["QAbstractItemView"]
    QComboBox = deps["QComboBox"]
    QFileDialog = deps["QFileDialog"]
    QCheckBox = deps["QCheckBox"]
    QDialog = deps["QDialog"]
    QDialogButtonBox = deps["QDialogButtonBox"]
    QHBoxLayout = deps["QHBoxLayout"]
    QLabel = deps["QLabel"]
    QLineEdit = deps["QLineEdit"]
    QListWidget = deps["QListWidget"]
    QMainWindow = deps["QMainWindow"]
    QMessageBox = deps["QMessageBox"]
    QPushButton = deps["QPushButton"]
    QTabWidget = deps["QTabWidget"]
    QTableWidget = deps["QTableWidget"]
    QTableWidgetItem = deps["QTableWidgetItem"]
    QTextEdit = deps["QTextEdit"]
    QVBoxLayout = deps["QVBoxLayout"]
    QWidget = deps["QWidget"]

    from family_agent.memory_policy import load_policy, save_policy, scan_allowed_paths

    class EditDialog(QDialog):
        def __init__(self, user_text: str, assistant_text: str, parent=None) -> None:
            super().__init__(parent)
            self.setWindowTitle("编辑记忆")
            self.resize(640, 480)
            lay = QVBoxLayout(self)
            lay.addWidget(QLabel("User:"))
            self.u = QTextEdit()
            self.u.setPlainText(user_text)
            lay.addWidget(self.u)
            lay.addWidget(QLabel("Assistant:"))
            self.a = QTextEdit()
            self.a.setPlainText(assistant_text)
            lay.addWidget(self.a)
            bb = QDialogButtonBox(
                QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
            )
            bb.accepted.connect(self.accept)
            bb.rejected.connect(self.reject)
            lay.addWidget(bb)

        def values(self) -> tuple[str, str]:
            return self.u.toPlainText().strip(), self.a.toPlainText().strip()

    class MainWindow(QMainWindow):
        def __init__(self) -> None:
            super().__init__()
            self.setWindowTitle("记忆库管理 Memory Studio")
            self.resize(1100, 720)

            self.brain = BrainWithMemory(
                llm_base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
                llm_model=os.getenv("OLLAMA_MODEL", "qwen2.5-coder"),
                embed_model=os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text"),
                memory_db_path=os.getenv("MEMORY_DB_PATH", "./memory_db.sqlite3"),
            )

            central = QWidget()
            self.setCentralWidget(central)
            root = QVBoxLayout(central)

            root.addWidget(
                QLabel(
                    "说明：禁止记忆规则在「策略」页保存后生效；仅影响之后的新增记忆。"
                    "扫描仅遍历你在「授权目录」中填写的路径，并自动跳过含微信相关目录的路径；不读取文件内容。"
                )
            )

            tabs = QTabWidget()
            root.addWidget(tabs)

            # --- Tab: 记忆表 ---
            mem_page = QWidget()
            mem_lay = QVBoxLayout(mem_page)
            self.table = QTableWidget(0, 5)
            self.table.setHorizontalHeaderLabels(["id", "时间", "User 摘要", "Assistant 摘要", "操作"])
            self.table.horizontalHeader().setStretchLastSection(True)
            self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
            self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
            mem_lay.addWidget(self.table)

            row_btns = QHBoxLayout()
            btn_refresh = QPushButton("刷新列表")
            btn_refresh.clicked.connect(self.reload_table)
            row_btns.addWidget(btn_refresh)
            self.count_label = QLabel("")
            row_btns.addWidget(self.count_label)
            row_btns.addStretch()
            mem_lay.addLayout(row_btns)
            tabs.addTab(mem_page, "记忆库")

            # --- Tab: PDF 投喂 ---
            self._pdf_selected_path = ""
            pdf_page = QWidget()
            pdf_lay = QVBoxLayout(pdf_page)
            pdf_lay.addWidget(
                QLabel(
                    "导入 PDF：按科目标签分块写入记忆（前缀【PDF|科目】），主程序对话时可语义检索。"
                    "扫描版/图片 PDF 请先自行 OCR 成可复制文本的 PDF。"
                )
            )
            subj_row = QHBoxLayout()
            subj_row.addWidget(QLabel("科目/分类："))
            self.pdf_subject = QComboBox()
            self.pdf_subject.setEditable(True)
            for s in (
                "数学一",
                "英语一",
                "408-数据结构",
                "408-计组",
                "408-OS",
                "408-计网",
                "政治",
                "通用",
            ):
                self.pdf_subject.addItem(s)
            subj_row.addWidget(self.pdf_subject, stretch=1)
            pdf_lay.addLayout(subj_row)

            btn_pick_pdf = QPushButton("选择 PDF 文件…")
            btn_pick_pdf.clicked.connect(self.pick_pdf_file)
            pdf_lay.addWidget(btn_pick_pdf)
            self.pdf_path_label = QLabel("未选择文件")
            pdf_lay.addWidget(self.pdf_path_label)

            self.pdf_preview = QTextEdit()
            self.pdf_preview.setReadOnly(True)
            self.pdf_preview.setPlaceholderText("选择 PDF 后显示提取文本预览（前约 8000 字）…")
            self.pdf_preview.setMinimumHeight(180)
            pdf_lay.addWidget(self.pdf_preview)

            self.pdf_ai_chk = QCheckBox(
                "导入后调用本地 Ollama 生成「总览解读」并一并入库（需 Ollama 已启动）"
            )
            self.pdf_ai_chk.setChecked(True)
            pdf_lay.addWidget(self.pdf_ai_chk)

            btn_pdf_ingest = QPushButton("导入记忆库（分块 + 可选总览）")
            btn_pdf_ingest.clicked.connect(self.run_pdf_ingest)
            pdf_lay.addWidget(btn_pdf_ingest)
            tabs.addTab(pdf_page, "PDF 投喂")

            # --- Tab: 策略 ---
            pol_page = QWidget()
            pol_lay = QVBoxLayout(pol_page)
            pol_lay.addWidget(
                QLabel("禁止写入记忆的子串（每行一条，匹配 User+Assistant 全文）：")
            )
            self.forbidden_edit = QTextEdit()
            pol_lay.addWidget(self.forbidden_edit)

            pol_lay.addWidget(QLabel("禁止写入记忆的正则（每行一条，可选）："))
            self.regex_edit = QTextEdit()
            pol_lay.addWidget(self.regex_edit)

            self.chk_wechat = QCheckBox("同时禁止记忆中出现「微信 / WeChat / Weixin」字样（慎开：讨论微信时也会被拒存）")
            pol_lay.addWidget(self.chk_wechat)

            btn_pol = QPushButton("保存策略到 memory_policy.json")
            btn_pol.clicked.connect(self.save_policy_clicked)
            pol_lay.addWidget(btn_pol)
            tabs.addTab(pol_page, "策略（禁止记忆）")

            # --- Tab: 语音 ---
            voice_page = QWidget()
            v_lay = QVBoxLayout(voice_page)
            self.voice_chk = QCheckBox("启用语音按钮（播报/转写入口；仍依赖本机是否安装 Kokoro/Whisper）")
            v_lay.addWidget(self.voice_chk)
            btn_v = QPushButton("保存语音开关")
            btn_v.clicked.connect(self.save_voice_clicked)
            v_lay.addWidget(btn_v)
            v_lay.addStretch()
            tabs.addTab(voice_page, "语音开关")

            # --- Tab: 扫描 ---
            scan_page = QWidget()
            s_lay = QVBoxLayout(scan_page)
            s_lay.addWidget(
                QLabel(
                    "授权扫描根目录（每行一个绝对路径）。将写入策略 scan_roots，仅用于下方「开始扫描」。"
                )
            )
            self.scan_roots_edit = QTextEdit()
            self.scan_roots_edit.setPlaceholderText(
                "每行一个文件夹绝对路径，例如：\nE:\\考研资料\nD:\\Books"
            )
            s_lay.addWidget(self.scan_roots_edit)

            s_lay.addWidget(
                QLabel(
                    "给 Agent 的内容：粘贴语雀/笔记/长难句等。可直接「写入记忆库」与主程序共用；"
                    "也可仅复制到剪贴板。"
                )
            )
            self.feed_content_edit = QTextEdit()
            self.feed_content_edit.setPlaceholderText(
                "在此粘贴正文……\n"
                "点「写入记忆库」会存入本地 SQLite（与 Family Agent 对话记忆同一库），并受「策略」页禁止规则约束。"
            )
            self.feed_content_edit.setMinimumHeight(140)
            s_lay.addWidget(self.feed_content_edit)

            feed_row = QHBoxLayout()
            btn_feed_save = QPushButton("写入记忆库（与主程序共用）")
            btn_feed_save.clicked.connect(self.save_feed_to_memory_db)
            btn_feed_copy = QPushButton("仅复制本框到剪贴板")
            btn_feed_copy.clicked.connect(self.copy_feed_content_only)
            btn_feed_merge = QPushButton("合并路径+本框并复制（不自动入库）")
            btn_feed_merge.clicked.connect(self.copy_feed_content_with_paths)
            feed_row.addWidget(btn_feed_save)
            feed_row.addWidget(btn_feed_copy)
            feed_row.addWidget(btn_feed_merge)
            s_lay.addLayout(feed_row)

            btn_scan = QPushButton("开始扫描（排除微信相关路径，仅列出文件路径）")
            btn_scan.clicked.connect(self.run_scan)
            s_lay.addWidget(btn_scan)
            self.scan_list = QListWidget()
            self.scan_list.setSelectionMode(
                QAbstractItemView.SelectionMode.ExtendedSelection
            )
            s_lay.addWidget(self.scan_list)

            scan_row = QHBoxLayout()
            btn_draft = QPushButton("复制对话草稿（选中项；不选则全部；不写入记忆）")
            btn_draft.clicked.connect(self.copy_scan_draft)
            btn_ai = QPushButton("确认后请求本地模型（仅路径名，不读文件；不自动入库）")
            btn_ai.clicked.connect(self.ai_summarize_scan_paths)
            scan_row.addWidget(btn_draft)
            scan_row.addWidget(btn_ai)
            s_lay.addLayout(scan_row)

            self.scan_preview = QTextEdit()
            self.scan_preview.setReadOnly(True)
            self.scan_preview.setPlaceholderText(
                "本地模型基于路径名的建议将显示在此（不会自动写入记忆库，可自行复制到主窗口）"
            )
            self.scan_preview.setMinimumHeight(160)
            s_lay.addWidget(self.scan_preview)
            tabs.addTab(scan_page, "授权目录扫描")

            self.reload_table()
            self.load_policy_ui()

        def load_policy_ui(self) -> None:
            pol = load_policy()
            lines = pol.get("forbidden_memory_substrings") or []
            self.forbidden_edit.setPlainText("\n".join(lines) if isinstance(lines, list) else "")
            rex = pol.get("forbidden_memory_regex") or []
            self.regex_edit.setPlainText("\n".join(rex) if isinstance(rex, list) else "")
            self.chk_wechat.setChecked(bool(pol.get("also_block_wechat_keywords")))
            self.voice_chk.setChecked(bool(pol.get("voice_enabled", True)))
            roots = pol.get("scan_roots") or []
            self.scan_roots_edit.setPlainText("\n".join(roots) if isinstance(roots, list) else "")

        def save_policy_clicked(self) -> None:
            pol = load_policy()
            pol["forbidden_memory_substrings"] = [
                x.strip()
                for x in self.forbidden_edit.toPlainText().splitlines()
                if x.strip()
            ]
            pol["forbidden_memory_regex"] = [
                x.strip()
                for x in self.regex_edit.toPlainText().splitlines()
                if x.strip()
            ]
            pol["also_block_wechat_keywords"] = self.chk_wechat.isChecked()
            roots = [
                x.strip()
                for x in self.scan_roots_edit.toPlainText().splitlines()
                if x.strip()
            ]
            pol["scan_roots"] = roots
            save_policy(pol)
            QMessageBox.information(self, "已保存", "策略已写入 memory_policy.json")

        def save_voice_clicked(self) -> None:
            pol = load_policy()
            pol["voice_enabled"] = self.voice_chk.isChecked()
            save_policy(pol)
            QMessageBox.information(self, "已保存", "语音开关已更新。")

        def run_scan(self) -> None:
            pol = load_policy()
            roots = [
                x.strip()
                for x in self.scan_roots_edit.toPlainText().splitlines()
                if x.strip()
            ]
            pol["scan_roots"] = roots
            save_policy(pol)
            self.scan_list.clear()
            paths = scan_allowed_paths(roots, pol)
            for p in paths:
                self.scan_list.addItem(p)
            QMessageBox.information(
                self,
                "扫描完成",
                f"共 {len(paths)} 条路径（已达上限或目录无效时会变少）。",
            )

        def pick_pdf_file(self) -> None:
            path, _ = QFileDialog.getOpenFileName(
                self,
                "选择 PDF",
                "",
                "PDF 文件 (*.pdf)",
            )
            if not path:
                return
            self._pdf_selected_path = path
            self.pdf_path_label.setText(path)
            try:
                from family_agent.pdf_ingest import extract_pdf_text

                t = extract_pdf_text(path)
                prev = t[:8000]
                if len(t) > 8000:
                    prev += "\n\n…（预览截断，完整文本分块导入）"
                self.pdf_preview.setPlainText(prev)
            except Exception as exc:
                self.pdf_preview.setPlainText(f"预览失败：{exc}")
                self._pdf_selected_path = ""

        def run_pdf_ingest(self) -> None:
            path = getattr(self, "_pdf_selected_path", "") or ""
            if not path:
                QMessageBox.information(self, "提示", "请先点击「选择 PDF 文件」。")
                return
            subj = self.pdf_subject.currentText().strip() or "通用"
            try:
                from family_agent.pdf_ingest import ingest_pdf_to_brain

                r = ingest_pdf_to_brain(
                    self.brain,
                    path,
                    subj,
                    do_ai_overview=self.pdf_ai_chk.isChecked(),
                )
            except Exception as exc:
                QMessageBox.warning(self, "导入失败", str(exc))
                return
            msg = (
                f"文件：{r['filename']}\n"
                f"科目：{r['subject']}\n"
                f"分块共 {r['chunks_total']} 段，成功写入 {r['chunks_saved']} 段。\n"
                f"若写入数少于分块数，请到「策略」页查看是否被禁止规则拦截。\n"
                f"总览解读：{'已写入' if r['overview_saved'] else '未生成或未写入（请确认 Ollama 已启动）'}"
            )
            op = r.get("overview_preview") or ""
            if op:
                msg += f"\n\n总览开头预览：\n{op[:400]}…"
            QMessageBox.information(self, "导入完成", msg)
            self.reload_table()

        def _collect_scan_paths(self) -> list[str]:
            items = self.scan_list.selectedItems()
            if items:
                return [i.text() for i in items]
            out: list[str] = []
            for i in range(self.scan_list.count()):
                it = self.scan_list.item(i)
                if it is not None:
                    out.append(it.text())
            return out

        def copy_scan_draft(self) -> None:
            paths = self._collect_scan_paths()
            if not paths:
                QMessageBox.information(self, "提示", "请先点击「开始扫描」得到列表。")
                return
            draft = (
                "【以下为授权目录扫描得到的文件路径，未读取文件内容。"
                "请根据路径与文件名帮我做资料分类与复习安排建议。】\n\n" + "\n".join(paths)
            )
            QApplication.clipboard().setText(draft)
            QMessageBox.information(
                self,
                "已复制",
                "对话草稿已复制到剪贴板，可粘贴到 Family Agent 主窗口发送。\n"
                "此操作不会写入记忆库。",
            )

        def save_feed_to_memory_db(self) -> None:
            text = self.feed_content_edit.toPlainText().strip()
            if not text:
                QMessageBox.information(self, "提示", "请先在大文本框里粘贴或输入内容。")
                return
            if len(text) > 30000:
                QMessageBox.warning(
                    self,
                    "过长",
                    "单条请勿超过约 3 万字符，请拆成多段，多次点「写入记忆库」。",
                )
                return
            user_tag = "【MemoryStudio 手动录入】"
            from family_agent.memory_policy import load_policy, should_write_memory

            ok, reason = should_write_memory(user_tag, text, load_policy())
            if not ok:
                QMessageBox.warning(
                    self,
                    "未写入记忆库",
                    f"当前策略禁止保存：{reason}\n请到「策略（禁止记忆）」页调整规则。",
                )
                return
            try:
                saved = self.brain.save_memory(user_tag, text)
            except Exception as exc:
                QMessageBox.warning(self, "失败", str(exc))
                return
            if saved:
                QMessageBox.information(
                    self,
                    "已保存",
                    "已写入本地记忆库（与 Family Agent 共用）。主程序对话时会检索到这些内容。",
                )
                self.reload_table()
            else:
                QMessageBox.warning(self, "未写入", "未能保存（可能被策略拦截）。")

        def copy_feed_content_only(self) -> None:
            text = self.feed_content_edit.toPlainText().strip()
            if not text:
                QMessageBox.information(self, "提示", "请先在上方大文本框里粘贴或输入内容。")
                return
            QApplication.clipboard().setText(text)
            QMessageBox.information(
                self,
                "已复制",
                "内容已复制到剪贴板，请到 Family Agent 主窗口粘贴后发送。\n（是否写入记忆由主程序与策略决定）",
            )

        def copy_feed_content_with_paths(self) -> None:
            feed = self.feed_content_edit.toPlainText().strip()
            paths = self._collect_scan_paths()
            parts: list[str] = []
            if feed:
                parts.append("【我补充的内容】\n" + feed)
            if paths:
                parts.append(
                    "【授权扫描得到的文件路径（仅路径字符串，未读文件内容）】\n"
                    + "\n".join(paths)
                )
            if not parts:
                QMessageBox.information(
                    self,
                    "提示",
                    "请至少在大文本框里写内容，或先「开始扫描」得到路径列表。",
                )
                return
            QApplication.clipboard().setText("\n\n".join(parts))
            QMessageBox.information(
                self,
                "已复制",
                "已合并复制到剪贴板，可到 Family Agent 主窗口粘贴发送。",
            )

        def ai_summarize_scan_paths(self) -> None:
            paths = self._collect_scan_paths()
            if not paths:
                QMessageBox.information(self, "提示", "请先扫描并得到路径列表。")
                return
            reply = QMessageBox.question(
                self,
                "确认",
                f"将向本机 Ollama 发送 {len(paths)} 条路径字符串（不读取文件内容、不写入记忆库）。是否继续？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
            show_paths = paths[:400]
            extra = ""
            if len(paths) > 400:
                extra = f"\n\n（共 {len(paths)} 条，此处仅提交前 400 条）"
            user_body = (
                "以下是用户授权目录中扫描到的文件路径（仅路径与文件名，未提供文件内容）。\n"
                "请根据路径与文件名推测可能的学习资料类型，并给出分类与复习优先级建议。"
                "不要编造文件正文。若路径与考研无关可说明。\n\n"
                + "\n".join(show_paths)
                + extra
            )
            try:
                from family_agent.ollama_chat import chat_completion

                out = chat_completion(
                    user_body,
                    system="你是考研学习助手，只根据路径名字符串做推断，不要捏造文件内容。",
                    temperature=0.25,
                )
                self.scan_preview.setPlainText(out)
            except Exception as exc:
                QMessageBox.warning(self, "请求失败", str(exc))

        def reload_table(self) -> None:
            rows = self.brain.list_memories_with_id(limit=500, offset=0)
            self.table.setRowCount(0)
            for r in rows:
                mem_id, ts, ut, at = r
                iso = datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
                row = self.table.rowCount()
                self.table.insertRow(row)
                self.table.setItem(row, 0, QTableWidgetItem(str(mem_id)))
                self.table.setItem(row, 1, QTableWidgetItem(iso))
                self.table.setItem(row, 2, QTableWidgetItem(ut[:120] + ("…" if len(ut) > 120 else "")))
                self.table.setItem(row, 3, QTableWidgetItem(at[:120] + ("…" if len(at) > 120 else "")))

                w = QWidget()
                h = QHBoxLayout(w)
                h.setContentsMargins(2, 2, 2, 2)
                b1 = QPushButton("编辑")
                b2 = QPushButton("删除")
                b1.clicked.connect(lambda _, mid=mem_id: self.edit_row(mid))
                b2.clicked.connect(lambda _, mid=mem_id: self.delete_row(mid))
                h.addWidget(b1)
                h.addWidget(b2)
                self.table.setCellWidget(row, 4, w)

            self.count_label.setText(f"共 {len(rows)} 条（最多显示 500）")

        def edit_row(self, mem_id: str) -> None:
            cur = self.brain.conn.execute(
                "SELECT user_text, assistant_text FROM memories WHERE id=?",
                (mem_id,),
            ).fetchone()
            if not cur:
                QMessageBox.warning(self, "错误", "记录不存在")
                return
            dlg = EditDialog(cur[0], cur[1], self)
            if dlg.exec() != QDialog.DialogCode.Accepted:
                return
            u, a = dlg.values()
            try:
                self.brain.update_memory_by_id(mem_id, u, a)
                self.reload_table()
            except Exception as exc:
                QMessageBox.warning(self, "错误", str(exc))

        def delete_row(self, mem_id: str) -> None:
            reply = QMessageBox.question(
                self,
                "确认",
                "确定删除该条记忆？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
            self.brain.delete_memory_by_id(mem_id)
            self.reload_table()

    app = QApplication([])
    w = MainWindow()
    w.show()
    app.exec()
