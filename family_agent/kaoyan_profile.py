"""考研档案（本地 JSON）：目标、日期、薄弱项；不含任何自动上传。"""

from __future__ import annotations

import json
import os
from datetime import date, datetime
from typing import Any, Dict, Optional

PROFILE_FILENAME = "kaoyan_profile.json"


def profile_path() -> str:
    return os.getenv("KAOYAN_PROFILE_PATH", os.path.join(os.getcwd(), PROFILE_FILENAME))


def load_profile() -> Dict[str, Any]:
    p = profile_path()
    if not os.path.isfile(p):
        return {}
    with open(p, encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, dict) else {}


def save_profile(data: Dict[str, Any]) -> None:
    p = profile_path()
    with open(p, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def parse_setup_kv(text_after_subcommand: str) -> Dict[str, str]:
    """解析 exam_date=2025-12-21 math=120 weak=计组 形式。"""
    out: Dict[str, str] = {}
    for part in text_after_subcommand.split():
        if "=" in part:
            k, v = part.split("=", 1)
            k, v = k.strip(), v.strip()
            if k:
                out[k] = v
    return out


def days_until_exam(profile: Dict[str, Any]) -> Optional[int]:
    exam = profile.get("exam_date")
    if not exam or not isinstance(exam, str):
        return None
    try:
        d = date.fromisoformat(exam.strip())
        return (d - date.today()).days
    except ValueError:
        return None


def profile_looks_complete(profile: Dict[str, Any]) -> bool:
    if not profile:
        return False
    if profile.get("setup_done") is True:
        return True
    return bool(profile.get("exam_date"))


def reminder_text(profile: Dict[str, Any]) -> str:
    lines: list[str] = []
    du = days_until_exam(profile)
    if du is not None:
        lines.append(f"【倒计时】距离档案中的初试日还有约 {du} 天。")
    else:
        lines.append(
            "【档案】尚未填写 exam_date。请发送："
            "/kaoyan setup exam_date=YYYY-MM-DD math=目标分 eng=目标分 408=目标分 weak=薄弱项"
        )

    hour = datetime.now().hour
    if hour < 12:
        lines.append("【时段建议】上午：英语单词/长难句 + 数学一个小专题。")
    elif hour < 18:
        lines.append("【时段建议】下午：408 单科轮换 + 错题回顾。")
    else:
        lines.append("【时段建议】晚间：数学限时练或阅读精读 + 当日复盘。")

    return "\n".join(lines)


def format_profile_show(profile: Dict[str, Any]) -> str:
    if not profile:
        return "档案为空。使用 /kaoyan setup exam_date=... 填写。"
    lines = [f"{k}: {v}" for k, v in sorted(profile.items())]
    return "\n".join(lines)
