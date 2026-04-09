import sys
import traceback

from family_agent.gui import _GuiDepsError, launch_gui


def main() -> None:
    try:
        launch_gui()
    except _GuiDepsError as exc:
        print(str(exc))
        print("可选：先用 CLI 版本 -> python run_family_agent.py")
        print()
        input("按回车键关闭窗口…")
        sys.exit(1)
    except Exception:
        traceback.print_exc()
        print()
        input("启动失败：请把上方报错截图或复制给助手。按回车关闭…")
        sys.exit(1)


if __name__ == "__main__":
    main()
