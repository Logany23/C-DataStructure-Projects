"""记忆库管理界面入口。"""

from family_agent.memory_studio import _StudioDepsError, launch_memory_studio


def main() -> None:
    try:
        launch_memory_studio()
    except _StudioDepsError as exc:
        print(str(exc))


if __name__ == "__main__":
    main()
