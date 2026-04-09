from __future__ import annotations

import argparse
import os
from datetime import datetime

from .brain import FamilyBrain
from .hands import AgentHands
from .kaoyan_profile import (
    format_profile_show,
    load_profile,
    parse_setup_kv,
    profile_looks_complete,
    reminder_text,
    save_profile,
)


def _print_memory_rows(rows):
    if not rows:
        print("Memory: 暂无结果。")
        return
    for ts, u, a in rows:
        iso = datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
        print(f"- [{iso}] U: {u[:60]} | A: {a[:60]}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Family Agent CLI")
    parser.add_argument("--cwd", default=os.getcwd(), help="working directory for hands")
    args = parser.parse_args()

    brain = FamilyBrain(
        llm_base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        llm_model=os.getenv("OLLAMA_MODEL", "qwen2.5-coder"),
        embed_model=os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text"),
        memory_db_path=os.getenv("MEMORY_DB_PATH", "./memory_db.sqlite3"),
    )
    hands = AgentHands(cwd=args.cwd)

    print("Family Agent 已启动。输入 /help 查看命令，exit 退出。")
    if os.getenv("KAOYAN_MODE", "").lower() in ("1", "true", "yes"):
        prof = load_profile()
        print("\n" + reminder_text(prof))
        if not profile_looks_complete(prof):
            print(
                "\n[考研] 首次请建档：/kaoyan setup exam_date=YYYY-MM-DD math=120 eng=75 408=120 weak=计组"
            )
    while True:
        text = input("\n你: ").strip()
        if not text:
            continue
        if text.lower() in {"exit", "quit"}:
            print("已退出。")
            break
        if text == "/help":
            print(
                "命令:\n"
                "- /run <shell_command>\n"
                "- /gh <gh_args>\n"
                "- /memory top [N]\n"
                "- /memory search <kw> [N]\n"
                "- /memory clear\n"
                "- /memory export [file.csv]\n"
                "- /kaoyan show | /kaoyan setup key=value ...\n"
                "- 其他输入会交给大脑回答"
            )
            continue

        try:
            if text.startswith("/kaoyan"):
                parts = text.split()
                sub = parts[1] if len(parts) > 1 else ""
                if sub == "show":
                    prof = load_profile()
                    print(reminder_text(prof))
                    print(format_profile_show(prof))
                elif sub == "setup":
                    rest = text[len("/kaoyan setup") :].strip()
                    if not rest:
                        print(
                            "用法: /kaoyan setup exam_date=YYYY-MM-DD math=数字 eng=数字 408=数字 weak=文字"
                        )
                    else:
                        kv = parse_setup_kv(rest)
                        if not kv:
                            print("未解析到 key=value。")
                        else:
                            prof = load_profile()
                            prof.update(kv)
                            prof["setup_done"] = True
                            save_profile(prof)
                            print("档案已保存。")
                else:
                    print("用法: /kaoyan show | /kaoyan setup ...")
                continue

            if text.startswith("/run "):
                cmd = text[5:].strip()
                res = hands.run_shell(cmd)
                print(f"[exit={res.code}]")
                if res.stdout:
                    print(res.stdout)
                if res.stderr:
                    print(res.stderr)
                continue

            if text.startswith("/gh "):
                gh_args = text[4:].strip()
                res = hands.run_github_cli(gh_args)
                print(f"[exit={res.code}]")
                if res.stdout:
                    print(res.stdout)
                if res.stderr:
                    print(res.stderr)
                continue

            if text.startswith("/memory"):
                parts = text.split()
                sub = parts[1] if len(parts) > 1 else ""
                if sub == "top":
                    n = int(parts[2]) if len(parts) > 2 else 5
                    _print_memory_rows(brain.memory_top(n))
                elif sub == "search":
                    if len(parts) < 3:
                        print("用法: /memory search <kw> [N]")
                        continue
                    n = int(parts[3]) if len(parts) > 3 else 10
                    _print_memory_rows(brain.memory_search(parts[2], n))
                elif sub == "clear":
                    deleted = brain.memory_clear()
                    print(f"Memory: 已清空 {deleted} 条。")
                elif sub == "export":
                    out = parts[2] if len(parts) > 2 else "memory_export.csv"
                    count = brain.memory_export(out)
                    print(f"Memory: 已导出 {count} 条到 {out}")
                else:
                    print("用法: /memory top [N] | /memory search <kw> [N] | /memory clear | /memory export [file.csv]")
                continue

            reply = brain.ask(text)
            print(f"Agent: {reply}")
        except Exception as exc:
            print(f"错误: {exc}")


if __name__ == "__main__":
    main()
