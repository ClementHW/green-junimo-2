import importlib.util
import shutil
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("build", ROOT / "scripts/build.py")
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


class ReproductionTests(unittest.TestCase):
    def test_matches_approved_pixels(self):
        atlas, _ = builder.assemble()
        self.assertEqual(atlas.size, (1536, 2288))

    def test_thinking_preserves_source_gif(self):
        from PIL import Image
        atlas, manifest = builder.assemble()
        with Image.open(ROOT / "assets/reference/thinking-original.gif") as gif:
            for col, index in enumerate([0, 0, 1, 2, 2, 3]):
                gif.seek(index)
                expected = Image.new("RGBA", (192, 208))
                expected.alpha_composite(gif.convert("RGBA").resize((128, 128), Image.Resampling.NEAREST), (32, 72))
                actual = atlas.crop((col * 192, 1456, (col + 1) * 192, 1664))
                self.assertEqual(actual.tobytes(), expected.tobytes())
        self.assertEqual(sum(manifest["rows"][7]["preview_durations_ms"]), 600)

    def test_rejects_modified_source(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            shutil.copy(ROOT / "manifest.json", root)
            shutil.copytree(ROOT / "assets/frames", root / "assets/frames")
            frame = next((root / "assets/frames").rglob("*.png"))
            frame.write_bytes(frame.read_bytes() + b"changed")
            with self.assertRaisesRegex(ValueError, "checksum"):
                builder.assemble(root)


if __name__ == "__main__":
    unittest.main()
