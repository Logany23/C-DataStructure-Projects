"""调用本地 Ollama OpenAI 兼容接口（仅标准库）。"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request


def chat_completion(
    user_content: str,
    *,
    model: str | None = None,
    base_url: str | None = None,
    temperature: float = 0.3,
    system: str | None = None,
    timeout: int = 180,
) -> str:
    base = (base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")).rstrip("/")
    model = model or os.getenv("OLLAMA_MODEL", "qwen2.5-coder")
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": user_content})
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "stream": False,
    }
    req = urllib.request.Request(
        f"{base}/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"Ollama HTTP {e.code}: {detail}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"无法连接 Ollama: {e}") from e
    try:
        return (
            data.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
            .strip()
        )
    except (IndexError, KeyError, TypeError) as e:
        raise RuntimeError(f"响应格式异常: {data!r}") from e
