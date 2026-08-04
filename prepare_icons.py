"""
prepare_icons.py — Convert Industirlity.png → icon.icns (macOS) and icon.ico (Windows).

Run this once before building:
    python prepare_icons.py
"""

import os
import sys
from pathlib import Path
from PIL import Image

ASSETS = Path(__file__).parent / "assets"
SRC    = ASSETS / "icon_master.png"


def make_icns():
    """macOS: create icon.icns from PNG using iconutil."""
    if sys.platform != "darwin":
        print("  [skip] .icns only needed on macOS")
        return

    iconset = ASSETS / "icon.iconset"
    iconset.mkdir(exist_ok=True)

    sizes = [16, 32, 64, 128, 256, 512, 1024]
    src   = Image.open(SRC).convert("RGBA")

    for s in sizes:
        out = iconset / f"icon_{s}x{s}.png"
        src.copy().resize((s, s), Image.LANCZOS).save(out)
        # Retina @2x variant
        out2 = iconset / f"icon_{s//2}x{s//2}@2x.png" if s >= 32 else None
        if out2:
            src.copy().resize((s, s), Image.LANCZOS).save(out2)

    icns_path = ASSETS / "icon.icns"
    os.system(f"iconutil -c icns '{iconset}' -o '{icns_path}'")

    # Cleanup iconset dir
    import shutil
    shutil.rmtree(iconset, ignore_errors=True)

    if icns_path.exists():
        print(f"  ✅ {icns_path}")
    else:
        print(f"  ❌ Failed to create icon.icns — iconutil not found?")


def make_ico():
    """Windows: create icon.ico (multi-resolution) from PNG."""
    ico_path = ASSETS / "icon.ico"
    src      = Image.open(SRC).convert("RGBA")

    sizes = [(16,16), (24,24), (32,32), (48,48), (64,64), (128,128), (256,256)]
    imgs  = [src.copy().resize(s, Image.LANCZOS) for s in sizes]
    imgs[0].save(ico_path, format="ICO", sizes=sizes, append_images=imgs[1:])
    print(f"  ✅ {ico_path}")


if __name__ == "__main__":
    print("Preparing icons from Industirlity.png...")
    if not SRC.exists():
        fallback = ASSETS / "Industirlity.png"
        if fallback.exists():
            SRC = fallback
        else:
            print(f"  ❌ Source not found: {SRC}")
            sys.exit(1)

    print("  → icon.ico  (Windows)")
    make_ico()

    print("  → icon.icns (macOS)")
    make_icns()

    print("Done.")
