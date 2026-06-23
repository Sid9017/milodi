"""PyInstaller 打包入口：转发到 milodi.cli.main。"""

from milodi.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
