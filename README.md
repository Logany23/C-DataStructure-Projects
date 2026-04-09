# C-DataStructure-Projects

基于**哈夫曼编码**的 C 语言文件压缩/解压练习，侧重数据结构与位级 I/O。

**项目背景**：为什么要写这个压缩器？  
**技术栈**：C 语言、哈夫曼编码、位操作。

**待办事项（To-Do List）**：

1. 项目初始化  
2. 实现哈夫曼树构建  
3. 实现文件位读取与压缩  
4. 实现解压功能  

仓库内另含本地 **Family Agent（全家桶）**：通过 [Ollama](https://ollama.com/)（默认 `qwen2.5-coder` + `nomic-embed-text`）、SQLite 向量记忆、可选考研定向人格、PyQt6 桌面端与记忆库管理，并支持 PDF 文本导入（需 `pymupdf`）。详见 [`FAMILY_AGENT_README.md`](FAMILY_AGENT_README.md)。

## 构建与运行（C 压缩工具）

在仓库根目录使用支持 C99 的编译器编译 `main.c`、`huffman.c` 等源文件并链接生成可执行文件（具体命令依你的环境而定）。

## Family Agent（Python 3.12+）

```text
python run_family_agent.py          # CLI
python run_family_agent_gui.py      # GUI
python run_memory_studio.py         # 记忆库 / PDF 投喂
```

依赖与说明见 `FAMILY_AGENT_README.md`；PDF 功能另见 `requirements-pdf.txt`。
