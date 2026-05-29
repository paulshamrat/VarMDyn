#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from PIL import Image

VARIANTS = ["01_WT", "02_L119R", "03_D193H", "04_G202E", "05_Q219K", "06_C291Y"]
DISPLAY_LABELS = {
    "01_WT": "WT",
    "02_L119R": "L119R",
    "03_D193H": "D193H",
    "04_G202E": "G202E",
    "05_Q219K": "Q219K",
    "06_C291Y": "C291Y",
}


def crop_white(img: Image.Image, pad: int = 36) -> Image.Image:
    arr = np.array(img.convert("RGB"))
    mask = np.any(arr < 245, axis=2)
    if not mask.any():
        return img
    ys, xs = np.where(mask)
    y0, y1 = ys.min(), ys.max() + 1
    x0, x1 = xs.min(), xs.max() + 1
    y0 = max(0, y0 - pad)
    x0 = max(0, x0 - pad)
    y1 = min(arr.shape[0], y1 + pad)
    x1 = min(arr.shape[1], x1 + pad)
    return img.crop((x0, y0, x1, y1))


def open_variant_image(folder: Path, variant: str, suffix: str) -> Image.Image:
    paths = [
        folder / f"{variant}_network_residues.png",
        folder / f"pathway_{variant}_{suffix}.png",
    ]
    for p in paths:
        if p.exists():
            return Image.open(p)
    raise FileNotFoundError(
        f"Could not find render image for variant {variant} in {folder} "
        f"(checked patterns: {[p.name for p in paths]})"
    )


def main() -> None:
    import os
    data_root = Path(os.environ.get("VARMDYN_DATA_ROOT", ROOT / "data")).expanduser()
    runs_root = Path(os.environ.get("VARMDYN_RUN_ROOT", ROOT / "runs")).expanduser()

    apo_dir = Path(os.environ.get("VARMDYN_NETWORK_APO_RENDER_DIR", data_root / "render/apo")).expanduser()
    holo_dir = Path(os.environ.get("VARMDYN_NETWORK_HOLO_RENDER_DIR", data_root / "render/holo")).expanduser()

    out_dir = apo_dir.parent
    out_dir.mkdir(parents=True, exist_ok=True)
    out_png = out_dir / "network_apo_holo_comparison.png"
    out_jpg = out_dir / "network_apo_holo_comparison.jpg"

    fig, axes = plt.subplots(4, 3, figsize=(11.2, 13.2), dpi=300)

    for i, v in enumerate(VARIANTS):
        r, c = divmod(i, 3)
        apo_img = open_variant_image(apo_dir, v, "apo")
        holo_img = open_variant_image(holo_dir, v, "holo")

        axes[r, c].imshow(crop_white(apo_img))
        axes[r, c].set_title(DISPLAY_LABELS.get(v, v), fontsize=11, pad=3)
        axes[r, c].axis("off")

        axes[r + 2, c].imshow(crop_white(holo_img))
        axes[r + 2, c].set_title(DISPLAY_LABELS.get(v, v), fontsize=11, pad=3)
        axes[r + 2, c].axis("off")

    fig.text(0.02, 0.975, "A  CDKL5-only (apo)", fontsize=12, fontweight="bold", va="top")
    fig.text(0.02, 0.49, "B  CDKL5 ATP/Mg-bound (holo)", fontsize=12, fontweight="bold", va="top")
    fig.text(0.57, 0.992, "Green: conserved | Blue: WT-lost | Red: variant-gained", fontsize=10, va="top")

    plt.subplots_adjust(left=0.02, right=0.995, top=0.965, bottom=0.02, wspace=0.04, hspace=0.06)
    fig.savefig(out_png, dpi=300)
    fig.savefig(out_jpg, dpi=300)
    plt.close(fig)
    print(f"[OK] {out_png}")
    print(f"[OK] {out_jpg}")


if __name__ == "__main__":
    # Ensure ROOT is set correctly relative to workflows/mdan/network/.
    ROOT = Path(__file__).resolve().parents[4]
    main()
