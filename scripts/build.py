#!/usr/bin/env python3
"""Rebuild approved sprites without generating, warping, or interpolating artwork."""
import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]


def assemble(root=ROOT):
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    atlas = Image.new("RGBA", (1536, 2288))
    counts = [6, 8, 8, 4, 5, 8, 6, 6, 6, 8, 8]
    if [len(row["frames"]) for row in manifest["rows"]] != counts:
        raise ValueError("Unexpected row/frame counts")
    for row_index, row in enumerate(manifest["rows"]):
        for col, entry in enumerate(row["frames"]):
            path = root / entry["path"]
            if hashlib.sha256(path.read_bytes()).hexdigest() != entry["sha256"]:
                raise ValueError(f"Source checksum mismatch: {entry['path']}")
            with Image.open(path) as source:
                frame = source.convert("RGBA")
            if frame.size != (192, 208) or not frame.getbbox():
                raise ValueError(f"Invalid frame: {entry['path']}")
            atlas.paste(frame, (col * 192, row_index * 208))
    actual = hashlib.sha256(atlas.tobytes()).hexdigest()
    if actual != manifest["expected_rgba_sha256"]:
        raise ValueError("Rebuilt pixels do not match the approved design")
    # Every block is constant on a four-pixel grid. No alpha interpolation.
    grid = atlas.resize((384, 572), Image.Resampling.NEAREST).resize(atlas.size, Image.Resampling.NEAREST)
    if grid.tobytes() != atlas.tobytes() or set(atlas.getchannel("A").getdata()) != {0, 255}:
        raise ValueError("Pixel-grid or transparency invariant failed")
    return atlas, manifest


def build(output, root=ROOT):
    atlas, manifest = assemble(root)
    output.mkdir(parents=True, exist_ok=True)
    path = output / "green-junimo-2.png"
    atlas.save(path)
    for row_index, row in enumerate(manifest["rows"][:9]):
        frames = []
        for col in range(len(row["frames"])):
            sprite = atlas.crop((col * 192, row_index * 208, (col + 1) * 192, (row_index + 1) * 208))
            frame = Image.new("RGBA", (192, 208), "#deded6")
            frame.alpha_composite(sprite)
            frames.append(frame.convert("RGB"))
        frames[0].save(output / f"{row['state']}.gif", save_all=True, append_images=frames[1:],
                       duration=row["preview_durations_ms"], disposal=2, loop=0, optimize=False)
    report = {"ok": True, "size": list(atlas.size), "rgba_sha256": manifest["expected_rgba_sha256"],
              "png_sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "frames": 73,
              "note": "RGBA hash is portable; PNG bytes may differ between encoder versions."}
    (output / "verification.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "build")
    args = parser.parse_args()
    print(json.dumps(build(args.output.resolve()), indent=2))
