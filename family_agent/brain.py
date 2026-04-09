from __future__ import annotations

from brain_with_memory import BrainWithMemory


class FamilyBrain:
    """Brain layer: LLM + long-term memory."""

    def __init__(
        self,
        llm_base_url: str = "http://localhost:11434",
        llm_model: str = "qwen2.5-coder",
        embed_model: str = "nomic-embed-text",
        memory_db_path: str = "./memory_db.sqlite3",
    ) -> None:
        self.core = BrainWithMemory(
            llm_base_url=llm_base_url,
            llm_model=llm_model,
            embed_model=embed_model,
            memory_db_path=memory_db_path,
        )

    def ask(self, text: str) -> str:
        return self.core.ask(text)

    def memory_top(self, n: int = 5):
        return self.core.list_recent_memories(limit=n)

    def memory_search(self, keyword: str, n: int = 10):
        return self.core.search_memories(keyword=keyword, limit=n)

    def memory_clear(self) -> int:
        return self.core.clear_memories()

    def memory_export(self, out_path: str) -> int:
        return self.core.export_memories_csv(out_path=out_path)
