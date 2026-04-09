"""PDF 文本提取、分块写入记忆库，可选调用本地模型生成科目总览。"""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List

if TYPE_CHECKING:
    from brain_with_memory import BrainWithMemory


def extract_pdf_text(path: str) -> str:
    path = str(Path(path).expanduser().resolve())
    if not Path(path).is_file():
        raise FileNotFoundError(path)

    try:
        import fitz  # PyMuPDF

        doc = fitz.open(path)
        try:
            parts: List[str] = []
            for page in doc:
                parts.append(page.get_text() or "")
            text = "\n\n".join(parts)
        finally:
            doc.close()
        if text.strip():
            return text
    except ImportError:
        pass
    except Exception:
        pass

    try:
        from pypdf import PdfReader

        reader = PdfReader(path)
        parts = [p.extract_text() or "" for p in reader.pages]
        return "\n\n".join(parts)
    except ImportError as e:
        raise RuntimeError(
            "无法读取 PDF：请先安装 pip install pymupdf（推荐）或 pip install pypdf"
        ) from e


def chunk_text(text: str, max_len: int = 1600, overlap: int = 120) -> List[str]:
    text = re.sub(r"\s+", " ", text.replace("\r", " ")).strip()
    if not text:
        return []
    chunks: List[str] = []
    i = 0
    n = len(text)
    while i < n:
        end = min(i + max_len, n)
        chunks.append(text[i:end].strip())
        if end >= n:
            break
        i = end - overlap
        if i < 0:
            i = end
    return [c for c in chunks if c]


def _sanitize_subject(s: str) -> str:
    s = (s or "").strip()
    s = re.sub(r"[\[\]【】|]", "", s)
    return s[:32] if s else "未分类"


def ingest_pdf_to_brain(
    brain: "BrainWithMemory",
    pdf_path: str,
    subject: str,
    *,
    do_ai_overview: bool = True,
    chunk_max_len: int = 1600,
) -> Dict[str, Any]:
    """
    将 PDF 分块写入记忆：User 行带 【PDF|科目】文件名 片段 i/n，Assistant 为正文片段。
    可选再写入一条 【PDF总览|科目】 模型解读。
    """
    subject = _sanitize_subject(subject)
    name = Path(pdf_path).name
    raw = extract_pdf_text(pdf_path)
    if not raw.strip():
        raise RuntimeError("提取结果为空（可能是加密或纯图片 PDF）。")

    chunks = chunk_text(raw, max_len=chunk_max_len)
    if not chunks:
        raise RuntimeError("分块后为空。")

    n = len(chunks)
    saved_chunks = 0
    for idx, ch in enumerate(chunks):
        ut = f"【PDF|{subject}】{name} 片段 {idx + 1}/{n}"
        if brain.save_memory(ut, ch):
            saved_chunks += 1

    overview_saved = False
    overview_text = ""
    if do_ai_overview:
        try:
            from family_agent.ollama_chat import chat_completion

            head = raw[:6000]
            prompt = (
                f"你是考研学习助手。下面是一份 PDF《{name}》提取出的开头文本（科目标签：{subject}）。\n"
                "请用中文输出：\n"
                "1）文档主题与结构（小标题级）\n"
                "2）按「数学一/英语一/408 各科」能归类的则归类要点，否则写「通用」\n"
                "3）用户后续追问时你可如何引用本文档\n"
                "不要编造正文中没有的内容。\n\n"
                f"---\n{head}\n---"
            )
            overview_text = chat_completion(
                prompt,
                system="只做解读与归类，不捏造原文细节。",
                temperature=0.25,
            )
            tag = f"【PDF总览|{subject}】{name}"
            overview_saved = brain.save_memory(tag, overview_text)
        except Exception:
            overview_text = ""
            overview_saved = False

    return {
        "filename": name,
        "subject": subject,
        "chunks_total": n,
        "chunks_saved": saved_chunks,
        "overview_saved": overview_saved,
        "overview_preview": overview_text[:500] if overview_text else "",
    }
