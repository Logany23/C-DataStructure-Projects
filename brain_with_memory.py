import argparse
import csv
import json
import math
import os
import sqlite3
import urllib.error
import urllib.request
import uuid
from collections import deque
from datetime import datetime
from typing import Deque, List, Tuple


class BrainWithMemory:
    def __init__(
        self,
        llm_base_url: str = "http://localhost:11434",
        llm_model: str = "qwen2.5-coder",
        embed_model: str = "nomic-embed-text",
        memory_db_path: str = "./memory_db.sqlite3",
        top_k: int = 5,
        history_turns: int = 4,
        max_user_chars: int = 2000,
    ) -> None:
        self.llm_base_url = llm_base_url.rstrip("/")
        self.llm_model = llm_model
        self.embed_model = embed_model
        self.top_k = top_k
        self.memory_db_path = memory_db_path
        self.max_user_chars = max_user_chars
        self.history: Deque[Tuple[str, str]] = deque(maxlen=max(1, history_turns))

        self.conn = sqlite3.connect(self.memory_db_path)
        self._init_db()

    def _init_db(self) -> None:
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS memories (
                id TEXT PRIMARY KEY,
                ts REAL NOT NULL,
                user_text TEXT NOT NULL,
                assistant_text TEXT NOT NULL,
                memory_text TEXT NOT NULL,
                embedding_json TEXT NOT NULL
            )
            """
        )
        self.conn.commit()

    def _system_prompt(self) -> str:
        base = (
            "你是一个带长期记忆的助手。"
            "请优先利用“记忆宫殿”中的历史信息回答问题，"
            "并保持回答准确、简洁。"
        )
        if os.getenv("KAOYAN_MODE", "").lower() in ("1", "true", "yes"):
            try:
                from kaoyan_persona import KAOYAN_SYSTEM_PROMPT

                return base + "\n\n" + KAOYAN_SYSTEM_PROMPT.strip()
            except ImportError:
                pass
        return base

    def _post_json(self, url: str, payload: dict) -> dict:
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"HTTP {e.code} {url}: {detail}") from e
        except urllib.error.URLError as e:
            raise RuntimeError(f"无法连接 Ollama: {e}") from e

    def _embed(self, text: str) -> List[float]:
        payload = {"model": self.embed_model, "prompt": text}
        data = self._post_json(f"{self.llm_base_url}/api/embeddings", payload)
        emb = data.get("embedding")
        if not isinstance(emb, list) or not emb:
            raise RuntimeError("embedding 返回异常")
        return [float(x) for x in emb]

    @staticmethod
    def _cosine_similarity(a: List[float], b: List[float]) -> float:
        if len(a) != len(b) or not a:
            return -1.0
        dot = sum(x * y for x, y in zip(a, b))
        na = math.sqrt(sum(x * x for x in a))
        nb = math.sqrt(sum(y * y for y in b))
        if na == 0.0 or nb == 0.0:
            return -1.0
        return dot / (na * nb)

    def retrieve_memory(self, query: str) -> List[str]:
        query_embedding = self._embed(query)
        cur = self.conn.execute(
            "SELECT memory_text, embedding_json FROM memories ORDER BY ts DESC LIMIT 500"
        )
        scored: List[Tuple[float, str]] = []
        for memory_text, embedding_json in cur.fetchall():
            mem_emb = json.loads(embedding_json)
            sim = self._cosine_similarity(query_embedding, mem_emb)
            scored.append((sim, memory_text))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [text for score, text in scored[: self.top_k] if score > 0]

    def list_recent_memories(self, limit: int = 5) -> List[Tuple[float, str, str]]:
        safe_limit = max(1, min(limit, 50))
        cur = self.conn.execute(
            "SELECT ts, user_text, assistant_text FROM memories ORDER BY ts DESC LIMIT ?",
            (safe_limit,),
        )
        return cur.fetchall()

    def clear_memories(self) -> int:
        cur = self.conn.execute("SELECT COUNT(*) FROM memories")
        total = int(cur.fetchone()[0])
        self.conn.execute("DELETE FROM memories")
        self.conn.commit()
        return total

    def export_memories_csv(self, out_path: str) -> int:
        cur = self.conn.execute(
            "SELECT ts, user_text, assistant_text, memory_text FROM memories ORDER BY ts ASC"
        )
        rows = cur.fetchall()
        with open(out_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["ts", "iso_time", "user_text", "assistant_text", "memory_text"])
            for ts, user_text, assistant_text, memory_text in rows:
                writer.writerow([ts, datetime.fromtimestamp(ts).isoformat(), user_text, assistant_text, memory_text])
        return len(rows)

    def search_memories(self, keyword: str, limit: int = 10) -> List[Tuple[float, str, str]]:
        kw = keyword.strip()
        if not kw:
            return []
        safe_limit = max(1, min(limit, 100))
        pattern = f"%{kw}%"
        cur = self.conn.execute(
            """
            SELECT ts, user_text, assistant_text
            FROM memories
            WHERE user_text LIKE ? OR assistant_text LIKE ? OR memory_text LIKE ?
            ORDER BY ts DESC
            LIMIT ?
            """,
            (pattern, pattern, pattern, safe_limit),
        )
        return cur.fetchall()

    def save_memory(self, user_text: str, assistant_text: str) -> bool:
        try:
            from family_agent.memory_policy import load_policy, should_write_memory

            ok, _reason = should_write_memory(user_text, assistant_text, load_policy())
            if not ok:
                return False
        except ImportError:
            pass

        now_ts = datetime.now().timestamp()
        memory_text = (
            f"[{datetime.now().isoformat()}] "
            f"User: {user_text}\nAssistant: {assistant_text}"
        )
        embedding = self._embed(memory_text)
        self.conn.execute(
            """
            INSERT INTO memories (id, ts, user_text, assistant_text, memory_text, embedding_json)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid.uuid4()),
                now_ts,
                user_text,
                assistant_text,
                memory_text,
                json.dumps(embedding),
            ),
        )
        self.conn.commit()
        return True

    def list_memories_with_id(self, limit: int = 500, offset: int = 0) -> List[Tuple]:
        limit = max(1, min(limit, 2000))
        offset = max(0, offset)
        cur = self.conn.execute(
            """
            SELECT id, ts, user_text, assistant_text
            FROM memories ORDER BY ts DESC LIMIT ? OFFSET ?
            """,
            (limit, offset),
        )
        return cur.fetchall()

    def update_memory_by_id(self, mem_id: str, user_text: str, assistant_text: str) -> None:
        row = self.conn.execute("SELECT ts FROM memories WHERE id=?", (mem_id,)).fetchone()
        if not row:
            raise ValueError("记录不存在")
        ts = float(row[0])
        memory_text = (
            f"[{datetime.fromtimestamp(ts).isoformat()}] "
            f"User: {user_text}\nAssistant: {assistant_text}"
        )
        embedding = self._embed(memory_text)
        self.conn.execute(
            """
            UPDATE memories SET user_text=?, assistant_text=?, memory_text=?, embedding_json=?
            WHERE id=?
            """,
            (user_text, assistant_text, memory_text, json.dumps(embedding), mem_id),
        )
        self.conn.commit()

    def delete_memory_by_id(self, mem_id: str) -> None:
        self.conn.execute("DELETE FROM memories WHERE id=?", (mem_id,))
        self.conn.commit()

    def ask(self, user_text: str) -> str:
        if len(user_text) > self.max_user_chars:
            raise RuntimeError(
                f"输入过长（{len(user_text)} 字符），请控制在 {self.max_user_chars} 字符以内。"
            )

        memories = self.retrieve_memory(user_text)
        memory_block = "\n\n".join(memories) if memories else "暂无相关记忆。"
        history_block = "\n".join(
            [f"User: {u}\nAssistant: {a}" for u, a in self.history]
        )
        if not history_block:
            history_block = "暂无短期对话历史。"

        system_prompt = self._system_prompt()
        user_prompt = (
            f"【记忆宫殿检索结果】\n{memory_block}\n\n"
            f"【短期对话历史】\n{history_block}\n\n"
            f"【用户当前问题】\n{user_text}"
        )

        payload = {
            "model": self.llm_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.4,
            "stream": False,
        }
        chat = self._post_json(f"{self.llm_base_url}/v1/chat/completions", payload)
        answer = (
            chat.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
            .strip()
        )
        if not answer:
            raise RuntimeError("chat 返回空内容")
        self.history.append((user_text, answer))
        self.save_memory(user_text, answer)  # 返回值忽略，策略拦截时静默不落库
        return answer

    def self_test(self) -> None:
        print("[SelfTest] 1/3 embedding...")
        emb = self._embed("self test")
        print(f"[SelfTest] embedding 维度: {len(emb)}")

        print("[SelfTest] 2/3 chat...")
        reply = self.ask("请只回复: self-test-ok")
        print(f"[SelfTest] chat 返回: {reply[:80]}")

        print("[SelfTest] 3/3 memory retrieve...")
        memories = self.retrieve_memory("self-test-ok")
        print(f"[SelfTest] 命中记忆条数: {len(memories)}")
        print("[SelfTest] 完成")


def main() -> None:
    parser = argparse.ArgumentParser(description="Brain with local memory on Ollama")
    parser.add_argument("--self-test", action="store_true", help="run self test and exit")
    parser.add_argument("--history-turns", type=int, default=4, help="short-term history turns")
    parser.add_argument("--max-user-chars", type=int, default=2000, help="max chars per user input")
    args = parser.parse_args()

    llm_base = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    llm_model = os.getenv("OLLAMA_MODEL", "qwen2.5-coder")
    embed_model = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")
    memory_db_path = os.getenv("MEMORY_DB_PATH", "./memory_db.sqlite3")

    brain = BrainWithMemory(
        llm_base_url=llm_base,
        llm_model=llm_model,
        embed_model=embed_model,
        memory_db_path=memory_db_path,
        history_turns=args.history_turns,
        max_user_chars=args.max_user_chars,
    )

    if args.self_test:
        brain.self_test()
        return

    print("Brain with Memory 已启动，输入 exit 退出。")
    print("命令: /memory top [N] | /memory search <关键词> [N] | /memory clear | /memory export [file.csv]")
    while True:
        user_text = input("\n你: ").strip()
        if not user_text:
            continue
        if user_text.lower() in {"exit", "quit"}:
            print("已退出。")
            break
        if user_text.startswith("/memory"):
            parts = user_text.split()
            sub = parts[1] if len(parts) > 1 else ""
            try:
                if sub == "top":
                    limit = int(parts[2]) if len(parts) > 2 else 5
                    items = brain.list_recent_memories(limit=limit)
                    if not items:
                        print("\nMemory: 暂无记忆。")
                        continue
                    print("\nMemory Top:")
                    for ts, u, a in items:
                        iso = datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
                        print(f"- [{iso}] U: {u[:60]} | A: {a[:60]}")
                elif sub == "clear":
                    deleted = brain.clear_memories()
                    print(f"\nMemory: 已清空 {deleted} 条。")
                elif sub == "export":
                    out_path = parts[2] if len(parts) > 2 else "memory_export.csv"
                    count = brain.export_memories_csv(out_path)
                    print(f"\nMemory: 已导出 {count} 条到 {out_path}")
                elif sub == "search":
                    if len(parts) < 3:
                        print("\n用法: /memory search <关键词> [N]")
                        continue
                    limit = int(parts[3]) if len(parts) > 3 else 10
                    items = brain.search_memories(parts[2], limit=limit)
                    if not items:
                        print("\nMemory: 未命中。")
                        continue
                    print("\nMemory Search:")
                    for ts, u, a in items:
                        iso = datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
                        print(f"- [{iso}] U: {u[:60]} | A: {a[:60]}")
                else:
                    print("\n用法: /memory top [N] | /memory search <关键词> [N] | /memory clear | /memory export [file.csv]")
            except Exception as exc:
                print(f"\nMemory命令错误: {exc}")
            continue

        try:
            reply = brain.ask(user_text)
            print(f"\nBrain: {reply}")
        except Exception as exc:
            print(f"\n错误: {exc}")


if __name__ == "__main__":
    main()
