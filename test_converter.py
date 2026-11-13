"""
Unit tests for converter.py
"""

import os
import unittest
from PIL import Image, ImageDraw
from converter import (
    ImageEntry,
    prepare_single_image,
    convert_images_to_pdf,
    format_file_size,
    get_image_info
)

class TestConverter(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.test_dir = os.path.join(os.path.dirname(__file__), "test_assets")
        os.makedirs(cls.test_dir, exist_ok=True)

        # Create sample images in different formats and modes
        cls.img_rgb_path = os.path.join(cls.test_dir, "test_rgb.jpg")
        img_rgb = Image.new("RGB", (300, 200), (255, 100, 50))
        img_rgb.save(cls_rgb := cls.img_rgb_path, "JPEG")

        cls.img_rgba_path = os.path.join(cls.test_dir, "test_rgba.png")
        img_rgba = Image.new("RGBA", (200, 400), (50, 150, 250, 128))
        img_rgba.save(cls.img_rgba_path, "PNG")

        cls.img_webp_path = os.path.join(cls.test_dir, "test_webp.webp")
        img_webp = Image.new("RGB", (250, 250), (120, 200, 80))
        img_webp.save(cls.img_webp_path, "WEBP")

    @classmethod
    def tearDownClass(cls):
        for f in os.listdir(cls.test_dir):
            try:
                os.remove(os.path.join(cls.test_dir, f))
            except Exception:
                pass
        try:
            os.rmdir(cls.test_dir)
        except Exception:
            pass

    def test_file_size_and_dimensions(self):
        self.assertEqual(format_file_size(500), "500 B")
        self.assertTrue(format_file_size(2048).endswith("KB"))
        self.assertTrue(format_file_size(2 * 1024 * 1024).endswith("MB"))

        dims = get_image_info(self.img_rgb_path)
        self.assertEqual(dims, (300, 200))

    def test_prepare_single_image_modes(self):
        entry_rgba = ImageEntry(path=self.img_rgba_path)
        out = prepare_single_image(entry_rgba, page_size="original")
        self.assertEqual(out.mode, "RGB")
        self.assertEqual(out.size, (200, 400))

        # Test rotation
        entry_rotated = ImageEntry(path=self.img_rgb_path, rotation=90)
        out_rot = prepare_single_image(entry_rotated, page_size="original")
        self.assertEqual(out_rot.size, (200, 300))

        # Test grayscale
        out_gray = prepare_single_image(entry_rgba, grayscale=True)
        self.assertEqual(out_gray.mode, "RGB")

    def test_convert_to_pdf_multi_page_and_order(self):
        output_pdf = os.path.join(self.test_dir, "output.pdf")
        
        # Test original order
        entries = [
            ImageEntry(path=self.img_rgb_path),
            ImageEntry(path=self.img_rgba_path),
            ImageEntry(path=self.img_webp_path),
        ]
        
        progress_events = []
        def progress_cb(cur, tot, msg):
            progress_events.append((cur, tot))

        success, msg = convert_images_to_pdf(
            entries=entries,
            output_path=output_pdf,
            page_size="A4",
            orientation="auto",
            margin_pct=5.0,
            progress_callback=progress_cb
        )

        self.assertTrue(success, f"Conversion failed: {msg}")
        self.assertTrue(os.path.exists(output_pdf))
        self.assertGreater(os.path.getsize(output_pdf), 1000)
        self.assertEqual(len(progress_events), 4) # 3 pages + final save

        # Clean up output PDF
        if os.path.exists(output_pdf):
            os.remove(output_pdf)

if __name__ == "__main__":
    unittest.main()
