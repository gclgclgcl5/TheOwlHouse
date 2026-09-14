"""把 branding/app_icon.png 同步为 Android 启动图标资源。

用法（在本目录或任意目录）:
  python apply_icon.py
  python apply_icon.py "D:/path/to/your_icon.png"
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent
RES = ROOT.parent / "src" / "main" / "res"
DEFAULT_SRC = ROOT / "app_icon.png"

# 旧版系统用的 mipmap 尺寸（px）
MIPMAP_SIZES = {
    "mipmap-mdpi": 48,
    "mipmap-hdpi": 72,
    "mipmap-xhdpi": 96,
    "mipmap-xxhdpi": 144,
    "mipmap-xxxhdpi": 192,
}


def main() -> None:
    src = Path(sys.argv[1]).expanduser().resolve() if len(sys.argv) > 1 else DEFAULT_SRC
    if not src.is_file():
        raise SystemExit(
            f"找不到图标文件: {src}\n"
            f"请把 PNG 放到: {DEFAULT_SRC}\n"
            f"或: python apply_icon.py <你的png路径>"
        )

    img = Image.open(src).convert("RGBA")
    # 方形居中裁切，避免拉伸变形
    w, h = img.size
    side = min(w, h)
    left = (w - side) // 2
    top = (h - side) // 2
    img = img.crop((left, top, left + side, top + side))

    drawable = RES / "drawable"
    drawable.mkdir(parents=True, exist_ok=True)
    fg = drawable / "ic_launcher_fg.png"
    # 自适应图标前景建议较大源图
    img.resize((512, 512), Image.Resampling.LANCZOS).save(fg, "PNG")
    print(f"foreground -> {fg}")

    for folder, px in MIPMAP_SIZES.items():
        d = RES / folder
        d.mkdir(parents=True, exist_ok=True)
        scaled = img.resize((px, px), Image.Resampling.LANCZOS)
        for name in ("ic_launcher.png", "ic_launcher_round.png"):
            out = d / name
            scaled.save(out, "PNG")
        print(f"{folder} -> {px}x{px}")

    # 保留一份到 branding，方便下次覆盖
    if src.resolve() != DEFAULT_SRC.resolve():
        shutil.copy2(src, DEFAULT_SRC)
        print(f"copied source -> {DEFAULT_SRC}")

    print("完成。请重新编译安装 App（assembleDebug / 安装 APK）。")


if __name__ == "__main__":
    main()
