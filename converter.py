"""
Image to PDF Conversion Engine
Handles loading, transformation, scaling, page layout, and PDF compilation.
"""

from __future__ import annotations
import os
from dataclasses import dataclass
from typing import Callable, List, Optional, Tuple
from PIL import Image, ImageOps

SUPPORTED_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff", ".tif",
    ".gif", ".ico", ".jfif", ".ppm", ".pgm", ".pbm"
}

STANDARD_PAGE_RATIOS = {
    "A4": 210.0 / 297.0,
    "A3": 297.0 / 420.0,
    "A5": 148.0 / 210.0,
    "Letter": 215.9 / 279.4,
    "Legal": 215.9 / 355.6,
}


@dataclass
class ImageEntry:
    path: str
    rotation: int = 0  # 0, 90, 180, 270 degrees clockwise

    @property
    def filename(self) -> str:
        return os.path.basename(self.path)

    @property
    def file_size(self) -> int:
        try:
            return os.path.getsize(self.path)
        except OSError:
            return 0


def format_file_size(size_in_bytes: int) -> str:
    """Formats file size into human-readable string (KB, MB)."""
    if size_in_bytes < 1024:
        return f"{size_in_bytes} B"
    elif size_in_bytes < 1024 * 1024:
        return f"{size_in_bytes / 1024:.1f} KB"
    else:
        return f"{size_in_bytes / (1024 * 1024):.2f} MB"


def get_image_info(path: str) -> Optional[Tuple[int, int]]:
    """Returns (width, height) of image without reading the whole file into memory."""
    try:
        with Image.open(path) as img:
            return img.size
    except Exception:
        return None


def prepare_single_image(
    entry: ImageEntry,
    page_size: str = "original",
    orientation: str = "auto",
    margin_pct: float = 0.0,
    grayscale: bool = False,
    fit_mode: str = "fit"
) -> Image.Image:
    """
    Opens, transforms, and places an image onto the requested PDF page canvas.
    Returns a PIL Image in 'RGB' mode ready to be saved into a PDF.
    """
    with Image.open(entry.path) as raw_img:
        # Handle EXIF orientation metadata automatically
        try:
            img = ImageOps.exif_transpose(raw_img)
        except Exception:
            img = raw_img.copy()
        else:
            if img is None:
                img = raw_img.copy()

        # Apply manual rotation if requested
        if entry.rotation % 360 != 0:
            # Pillow rotate counter-clockwise for positive degrees, so negative for clockwise
            img = img.rotate(-entry.rotation, expand=True)

        # Handle transparency & color modes: convert to clean RGB with white background
        if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
            img_rgba = img.convert("RGBA")
            bg = Image.new("RGB", img_rgba.size, (255, 255, 255))
            bg.paste(img_rgba, mask=img_rgba.split()[3])
            img = bg
        elif img.mode != "RGB":
            img = img.convert("RGB")

        # Convert to Grayscale if requested
        if grayscale:
            img = ImageOps.grayscale(img).convert("RGB")

        w, h = img.size

        # Mode 1: Match original image size
        if page_size.lower() == "original":
            if margin_pct <= 0:
                return img
            # Add margin
            mx = max(1, int(w * (margin_pct / 100.0)))
            my = max(1, int(h * (margin_pct / 100.0)))
            canvas = Image.new("RGB", (w + 2 * mx, h + 2 * my), (255, 255, 255))
            canvas.paste(img, (mx, my))
            return canvas

        # Mode 2: Standard page sizes (A4, Letter, etc.)
        base_ratio = STANDARD_PAGE_RATIOS.get(page_size, STANDARD_PAGE_RATIOS["A4"])
        
        # Determine page orientation
        if orientation == "auto":
            is_landscape = w > h
        elif orientation == "landscape":
            is_landscape = True
        else:
            is_landscape = False

        if is_landscape:
            target_ratio = 1.0 / base_ratio if base_ratio < 1.0 else base_ratio
        else:
            target_ratio = base_ratio if base_ratio < 1.0 else 1.0 / base_ratio

        # Create canvas matching target aspect ratio without degrading image resolution
        m_frac = min(0.4, max(0.0, margin_pct / 100.0))
        avail_ratio = target_ratio  # inner available area maintains page ratio

        # Determine inner dimensions to enclose the image at 1:1 scale
        if fit_mode == "fill":
            # Stretch or crop
            inner_w = w
            inner_h = int(w / avail_ratio)
            img_fitted = img.resize((inner_w, inner_h), Image.Resampling.BILINEAR)
        else:
            # Fit: maintain aspect ratio, center on canvas
            if (w / h) > avail_ratio:
                inner_w = w
                inner_h = int(w / avail_ratio)
            else:
                inner_h = h
                inner_w = int(h * avail_ratio)
            img_fitted = img

        if m_frac > 0:
            scale_margin = 1.0 / (1.0 - 2.0 * m_frac)
            canvas_w = int(inner_w * scale_margin)
            canvas_h = int(inner_h * scale_margin)
        else:
            canvas_w = inner_w
            canvas_h = inner_h

        canvas = Image.new("RGB", (canvas_w, canvas_h), (255, 255, 255))
        offset_x = (canvas_w - img_fitted.width) // 2
        offset_y = (canvas_h - img_fitted.height) // 2
        canvas.paste(img_fitted, (offset_x, offset_y))
        return canvas


def convert_images_to_pdf(
    entries: List[ImageEntry],
    output_path: str,
    page_size: str = "original",
    orientation: str = "auto",
    margin_pct: float = 0.0,
    grayscale: bool = False,
    quality: int = 90,
    progress_callback: Optional[Callable[[int, int, str], None]] = None,
    should_cancel: Optional[Callable[[], bool]] = None
) -> Tuple[bool, str]:
    """
    Converts ordered list of image entries into a single multi-page PDF.
    
    Returns:
        (success: bool, message: str)
    """
    if not entries:
        return False, "No images selected."

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    processed_pages: List[Image.Image] = []
    total = len(entries)

    try:
        for idx, entry in enumerate(entries):
            if should_cancel and should_cancel():
                return False, "Conversion cancelled by user."

            if progress_callback:
                progress_callback(idx + 1, total, f"Processing page {idx + 1} of {total}: {entry.filename}")

            page = prepare_single_image(
                entry,
                page_size=page_size,
                orientation=orientation,
                margin_pct=margin_pct,
                grayscale=grayscale
            )
            processed_pages.append(page)

        if not processed_pages:
            return False, "No pages could be processed."

        if progress_callback:
            progress_callback(total, total, "Assembling and saving PDF...")

        first_page = processed_pages[0]
        other_pages = processed_pages[1:] if len(processed_pages) > 1 else []

        # Save to PDF
        first_page.save(
            output_path,
            "PDF",
            save_all=True,
            append_images=other_pages,
            resolution=100.0,
            quality=max(10, min(100, quality))
        )

        return True, f"Successfully created PDF with {total} pages at:\n{output_path}"

    except Exception as e:
        return False, f"Error creating PDF: {str(e)}"
    finally:
        # Clean up images from memory
        for page in processed_pages:
            try:
                page.close()
            except Exception:
                pass
