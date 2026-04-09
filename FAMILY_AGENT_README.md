# Family Agent (全家桶版)

你要的四层结构已经落地：

- 大脑：Ollama (`qwen2.5-coder`)
- 记忆：本地 Memory Palace（SQLite + 向量检索）
- 手脚：Shell 与 GitHub CLI 执行器
- 交互：CLI 主入口（可继续接 PyQt6/Whisper/Kokoro）

## 快速启动

```bash
python run_family_agent.py
```

GUI 版（Jarvis 风格桌面入口）：

```bash
python run_family_agent_gui.py
```

记忆库管理（查看/编辑/删除记忆，禁止记忆规则、语音开关、授权目录扫描）：

```bash
python run_memory_studio.py
```

桌面已可复制 `launch_memory_studio.bat` 为 `MemoryStudio.bat` 双击启动。

**PDF 投喂**：记忆库管理内「PDF 投喂」标签可选科目、导入 PDF（文本层），分块写入记忆并可选生成总览。需安装：

```bash
"%LOCALAPPDATA%\Programs\Python\Python312\python.exe" -m pip install pymupdf
```

扫描版/纯图片 PDF 需先 OCR；导入受「策略」禁止规则约束。

GUI / 记忆库管理需要 PyQt6。已用 **官方 Python 3.12** 安装；桌面 `.bat` 会优先使用  
`%LOCALAPPDATA%\Programs\Python\Python312\python.exe`，避免 MSYS 自带 Python 找不到 PyQt6。

若仍提示缺少，可在该解释器下执行：

```bash
"%LOCALAPPDATA%\Programs\Python\Python312\python.exe" -m pip install PyQt6
```

## 命令

- `/run <shell_command>`：执行本地命令
- `/gh <gh_args>`：执行 GitHub CLI，如 `/gh repo view`
- `/memory top [N]`
- `/memory search <kw> [N]`
- `/memory clear`
- `/memory export [file.csv]`
- `/kaoyan show`：查看本地考研档案与倒计时提示
- `/kaoyan setup exam_date=YYYY-MM-DD math=120 eng=75 408=120 weak=计组`：写入档案（仅存本机）
- 其他自然语言：交给大脑回答并自动记忆

## 环境变量（可选）

- `OLLAMA_BASE_URL`（默认 `http://localhost:11434`）
- `OLLAMA_MODEL`（默认 `qwen2.5-coder`）
- `OLLAMA_EMBED_MODEL`（默认 `nomic-embed-text`）
- `MEMORY_DB_PATH`（默认 `./memory_db.sqlite3`）
- `KAOYAN_MODE=1`：启用「计算机考研」定向人格（数学一、英语一、408），与长期记忆叠加。桌面快捷方式启动的 `.bat` 已默认开启。

## 后续可扩展

- PyQt6 UI（聊天窗口 + 语音按钮）
- Whisper 实时语音输入
- Kokoro 语音播报
- 工具权限分级和审计日志
