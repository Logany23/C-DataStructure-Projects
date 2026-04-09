"""记忆策略：禁止写入的关键词、语音开关、授权扫描目录（排除微信路径）。"""

from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, List, Tuple

DEFAULT_POLICY: Dict[str, Any] = {
    "voice_enabled": True,
    "forbidden_memory_substrings": [],
    "forbidden_memory_regex": [],
    "also_block_wechat_keywords": False,
    "wechat_path_keywords": [
        "WeChat Files",
        "WeChat",
        "Tencent\\WeChat",
        "Weixin",
        "微信",
    ],
    "scan_roots": [],
    "scan_max_files": 3000,
}


def policy_path() -> str:
    return os.getenv("MEMORY_POLICY_PATH", os.path.join(os.getcwd(), "memory_policy.json"))


def load_policy() -> Dict[str, Any]:
    p = policy_path()
    if not os.path.isfile(p):
        return dict(DEFAULT_POLICY)
    with open(p, encoding="utf-8") as f:
        data = json.load(f)
    out = dict(DEFAULT_POLICY)
    if isinstance(data, dict):
        out.update(data)
    return out


def save_policy(data: Dict[str, Any]) -> None:
    merged = dict(DEFAULT_POLICY)
    merged.update(data)
    with open(policy_path(), "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)


def should_write_memory(user_text: str, assistant_text: str, policy: Dict[str, Any] | None = None) -> Tuple[bool, str]:
    """
    返回 (是否允许写入, 原因说明)。
    """
    if policy is None:
        policy = load_policy()
    combined = f"{user_text}\n{assistant_text}"

    for s in policy.get("forbidden_memory_substrings", []):
        if isinstance(s, str) and s and s in combined:
            return False, f"命中禁止子串: {s[:40]}"

    for pattern in policy.get("forbidden_memory_regex", []):
        if not isinstance(pattern, str) or not pattern.strip():
            continue
        try:
            if re.search(pattern, combined):
                return False, f"命中禁止正则: {pattern[:40]}"
        except re.error:
            continue

    if policy.get("also_block_wechat_keywords"):
        for kw in ("微信", "WeChat", "Weixin"):
            if kw in combined:
                return False, f"策略已开启：禁止记忆含「{kw}」的内容"

    return True, ""


def scan_allowed_paths(roots: List[str], policy: Dict[str, Any] | None = None) -> List[str]:
    """
    仅在用户填写的 scan_roots 下遍历文件路径；路径任意段命中 wechat 关键词则跳过。
    不读取文件内容，仅枚举路径。
    """
    if policy is None:
        policy = load_policy()
    roots = roots or policy.get("scan_roots") or []
    keywords = [k for k in policy.get("wechat_path_keywords", []) if isinstance(k, str) and k]
    max_files = int(policy.get("scan_max_files", 3000))
    out: List[str] = []
    count = 0

    def path_excluded(p: str) -> bool:
        pl = p.replace("/", "\\").lower()
        for kw in keywords:
            if kw.lower() in pl:
                return True
        return False

    for root in roots:
        root = (root or "").strip().strip('"')
        if not root or not os.path.isdir(root):
            continue
        if path_excluded(root):
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            if path_excluded(dirpath):
                dirnames[:] = []
                continue
            dirnames[:] = [
                d
                for d in dirnames
                if not path_excluded(os.path.join(dirpath, d))
            ]
            for fn in filenames:
                if count >= max_files:
                    return out
                fp = os.path.join(dirpath, fn)
                if path_excluded(fp):
                    continue
                out.append(fp)
                count += 1
    return out
