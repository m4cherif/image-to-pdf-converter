"""
Professional GUI Application for Image to PDF Converter using PyQt5.
Features modern UI/UX, Dark/Light theme toggle, Grid Cards / List views,
drag-and-drop page ordering, thumbnail caching, full-featured previewer,
and real-time settings feedback.
"""

from __future__ import annotations
import os
import sys
import subprocess
from typing import List, Optional, Tuple

from PyQt5.QtCore import (
    Qt, QSize, QThread, pyqtSignal, QPoint, QRect, QRectF
)
from PyQt5.QtGui import (
    QIcon, QPixmap, QImage, QFont, QColor, QPainter, QBrush, QPen,
    QPainterPath, QLinearGradient, QFontMetrics
)
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QListWidget, QListWidgetItem, QFileDialog,
    QComboBox, QSpinBox, QCheckBox, QProgressBar, QMessageBox,
    QGroupBox, QSplitter, QFrame, QMenu, QDialog, QScrollArea,
    QStyle, QAbstractItemView, QStackedWidget, QSlider, QStyledItemDelegate
)

from PIL import Image
from converter import (
    ImageEntry,
    SUPPORTED_EXTENSIONS,
    STANDARD_PAGE_RATIOS,
    convert_images_to_pdf,
    format_file_size,
    get_image_info
)


# ==============================================================================
# Theme Definitions
# ==============================================================================

class Theme:
    LIGHT = {
        "name": "light",
        "bg_main": "#f8fafc",
        "card_bg": "#ffffff",
        "card_hover": "#f1f5f9",
        "card_selected": "#eff6ff",
        "card_border": "#e2e8f0",
        "card_border_selected": "#2563eb",
        "text_primary": "#0f172a",
        "text_secondary": "#475569",
        "text_muted": "#94a3b8",
        "accent": "#2563eb",
        "accent_hover": "#1d4ed8",
        "accent_light": "#dbeafe",
        "accent_text": "#1e40af",
        "danger": "#dc2626",
        "danger_hover": "#b91c1c",
        "danger_light": "#fee2e2",
        "success": "#16a34a",
        "pill_bg": "#f1f5f9",
        "pill_border": "#cbd5e1",
        "scrollbar": "#cbd5e1"
    }

    DARK = {
        "name": "dark",
        "bg_main": "#0f172a",
        "card_bg": "#1e293b",
        "card_hover": "#334155",
        "card_selected": "#1e3a8a",
        "card_border": "#334155",
        "card_border_selected": "#3b82f6",
        "text_primary": "#f8fafc",
        "text_secondary": "#cbd5e1",
        "text_muted": "#64748b",
        "accent": "#3b82f6",
        "accent_hover": "#2563eb",
        "accent_light": "#1e293b",
        "accent_text": "#93c5fd",
        "danger": "#ef4444",
        "danger_hover": "#dc2626",
        "danger_light": "#451a1a",
        "success": "#22c55e",
        "pill_bg": "#334155",
        "pill_border": "#475569",
        "scrollbar": "#475569"
    }


def get_stylesheet(theme: dict) -> str:
    return f"""
        QMainWindow, QWidget#centralWidget {{
            background-color: {theme["bg_main"]};
            color: {theme["text_primary"]};
            font-family: "Segoe UI", -apple-system, system-ui, sans-serif;
        }}

        QScrollBar:vertical {{
            background: transparent;
            width: 8px;
            margin: 0px;
        }}
        QScrollBar::handle:vertical {{
            background: {theme["scrollbar"]};
            min-height: 30px;
            border-radius: 4px;
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0px;
        }}

        QToolTip {{
            background-color: {theme["card_bg"]};
            color: {theme["text_primary"]};
            border: 1px solid {theme["card_border"]};
            border-radius: 6px;
            padding: 5px 8px;
            font-size: 12px;
        }}
    """


# ==============================================================================
# Custom Card & List Item Delegate
# ==============================================================================

class ImageItemDelegate(QStyledItemDelegate):
    """
    Renders high-performance custom visual cards for each image,
    displaying thumbnails, dynamic page badges, dimensions, file size,
    and rotation indicators with crisp antialiased geometry.
    """
    def __init__(self, main_win: MainWindow):
        super().__init__(main_win)
        self.main_win = main_win

    def sizeHint(self, option, index):
        if self.main_win.view_mode == "grid":
            return QSize(155, 195)
        else:
            return QSize(option.rect.width(), 80)

    def paint(self, painter: QPainter, option, index):
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)

        theme = self.main_win.current_theme
        entry: ImageEntry = index.data(Qt.UserRole)
        if not entry:
            painter.restore()
            return

        page_num = index.row() + 1
        rect = option.rect.adjusted(3, 3, -3, -3)
        is_selected = option.state & QStyle.State_Selected
        is_hovered = option.state & QStyle.State_MouseOver

        # 1. Background Card
        card_path = QPainterPath()
        card_path.addRoundedRect(QRectF(rect), 8, 8)

        if is_selected:
            bg_color = QColor(theme["card_selected"])
            border_color = QColor(theme["card_border_selected"])
            border_width = 1.8
        elif is_hovered:
            bg_color = QColor(theme["card_hover"])
            border_color = QColor(theme["card_border_selected"]).lighter(120)
            border_width = 1.0
        else:
            bg_color = QColor(theme["card_bg"])
            border_color = QColor(theme["card_border"])
            border_width = 1.0

        painter.fillPath(card_path, QBrush(bg_color))
        pen = QPen(border_color, border_width)
        painter.setPen(pen)
        painter.drawPath(card_path)

        pixmap = self.main_win.get_thumbnail_pixmap(entry)

        if self.main_win.view_mode == "grid":
            self._paint_grid_card(painter, rect, entry, page_num, pixmap, theme, is_selected)
        else:
            self._paint_list_card(painter, rect, entry, page_num, pixmap, theme, is_selected)

        painter.restore()

    def _paint_grid_card(self, painter: QPainter, rect: QRect, entry: ImageEntry,
                          page_num: int, pixmap: QPixmap, theme: dict, is_selected: bool):
        # 1. Page Badge (Top-Left)
        badge_rect = QRectF(rect.x() + 8, rect.y() + 8, 28, 20)
        badge_path = QPainterPath()
        badge_path.addRoundedRect(badge_rect, 4, 4)
        painter.fillPath(badge_path, QBrush(QColor(theme["accent"])))

        painter.setPen(QColor("#ffffff"))
        f_badge = QFont("Segoe UI", 9, QFont.Bold)
        painter.setFont(f_badge)
        painter.drawText(badge_rect, Qt.AlignCenter, str(page_num))

        # 2. Rotation badge if applicable
        if entry.rotation % 360 != 0:
            rot_rect = QRectF(rect.right() - 48, rect.y() + 8, 40, 20)
            rot_path = QPainterPath()
            rot_path.addRoundedRect(rot_rect, 4, 4)
            painter.fillPath(rot_path, QBrush(QColor("#f59e0b")))
            painter.setPen(QColor("#ffffff"))
            f_rot = QFont("Segoe UI", 8, QFont.Bold)
            painter.setFont(f_rot)
            painter.drawText(rot_rect, Qt.AlignCenter, f"{entry.rotation}°")

        # 3. Centered Thumbnail Area
        thumb_area = QRect(rect.x() + 10, rect.y() + 34, rect.width() - 20, 105)
        # Subtle frame for thumbnail
        t_frame = QPainterPath()
        t_frame.addRoundedRect(QRectF(thumb_area), 6, 6)
        painter.fillPath(t_frame, QBrush(QColor(theme["bg_main"])))
        painter.setPen(QPen(QColor(theme["card_border"]), 1))
        painter.drawPath(t_frame)

        if not pixmap.isNull():
            scaled = pixmap.scaled(
                thumb_area.width() - 8,
                thumb_area.height() - 8,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            tx = thumb_area.x() + (thumb_area.width() - scaled.width()) // 2
            ty = thumb_area.y() + (thumb_area.height() - scaled.height()) // 2
            painter.drawPixmap(tx, ty, scaled)

        # 4. Image Title (Bottom)
        painter.setPen(QColor(theme["text_primary"]))
        f_title = QFont("Segoe UI", 9, QFont.DemiBold)
        painter.setFont(f_title)
        title_rect = QRect(rect.x() + 8, rect.bottom() - 44, rect.width() - 16, 20)
        metrics = QFontMetrics(f_title)
        elided = metrics.elidedText(entry.filename, Qt.ElideMiddle, title_rect.width())
        painter.drawText(title_rect, Qt.AlignVCenter | Qt.AlignLeft, elided)

        # 5. Metadata (File Size)
        painter.setPen(QColor(theme["text_muted"]))
        f_meta = QFont("Segoe UI", 8)
        painter.setFont(f_meta)
        meta_rect = QRect(rect.x() + 8, rect.bottom() - 24, rect.width() - 16, 18)
        painter.drawText(meta_rect, Qt.AlignVCenter | Qt.AlignLeft, format_file_size(entry.file_size))

    def _paint_list_card(self, painter: QPainter, rect: QRect, entry: ImageEntry,
                          page_num: int, pixmap: QPixmap, theme: dict, is_selected: bool):
        # 1. Page Number Pill
        badge_w, badge_h = 56, 28
        badge_x = rect.x() + 12
        badge_y = rect.y() + (rect.height() - badge_h) // 2
        badge_rect = QRectF(badge_x, badge_y, badge_w, badge_h)
        badge_path = QPainterPath()
        badge_path.addRoundedRect(badge_rect, 6, 6)

        if is_selected:
            painter.fillPath(badge_path, QBrush(QColor(theme["accent"])))
            painter.setPen(QColor("#ffffff"))
        else:
            painter.fillPath(badge_path, QBrush(QColor(theme["pill_bg"])))
            painter.setPen(QColor(theme["text_secondary"]))

        painter.setFont(QFont("Segoe UI", 9, QFont.Bold))
        painter.drawText(badge_rect, Qt.AlignCenter, f"#{page_num:02d}")

        # 2. Thumbnail
        thumb_box = QRect(rect.x() + 80, rect.y() + 8, 62, 58)
        t_frame = QPainterPath()
        t_frame.addRoundedRect(QRectF(thumb_box), 6, 6)
        painter.fillPath(t_frame, QBrush(QColor(theme["bg_main"])))
        painter.setPen(QPen(QColor(theme["card_border"]), 1))
        painter.drawPath(t_frame)

        if not pixmap.isNull():
            scaled = pixmap.scaled(
                thumb_box.width() - 4,
                thumb_box.height() - 4,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            tx = thumb_box.x() + (thumb_box.width() - scaled.width()) // 2
            ty = thumb_box.y() + (thumb_box.height() - scaled.height()) // 2
            painter.drawPixmap(tx, ty, scaled)

        # 3. Filename
        text_x = thumb_box.right() + 16
        avail_w = rect.right() - text_x - 110
        f_name = QFont("Segoe UI", 10, QFont.Bold)
        painter.setFont(f_name)
        painter.setPen(QColor(theme["text_primary"]))
        metrics = QFontMetrics(f_name)
        elided = metrics.elidedText(entry.filename, Qt.ElideMiddle, max(100, avail_w))
        painter.drawText(text_x, rect.y() + 28, elided)

        # 4. Metadata Pills
        dims = get_image_info(entry.path)
        dim_str = f"{dims[0]} × {dims[1]}" if dims else "Image"
        size_str = format_file_size(entry.file_size)
        ext_str = os.path.splitext(entry.filename)[1].upper().replace(".", "")

        chips = [dim_str, size_str, ext_str]
        if entry.rotation % 360 != 0:
            chips.append(f"⟳ {entry.rotation}°")

        chip_x = text_x
        chip_y = rect.y() + 42
        painter.setFont(QFont("Segoe UI", 8, QFont.DemiBold))

        for chip_text in chips:
            chip_metrics = QFontMetrics(painter.font())
            tw = chip_metrics.horizontalAdvance(chip_text)
            c_rect = QRectF(chip_x, chip_y, tw + 14, 20)
            c_path = QPainterPath()
            c_path.addRoundedRect(c_rect, 4, 4)

            if "⟳" in chip_text:
                painter.fillPath(c_path, QBrush(QColor("#f59e0b")))
                painter.setPen(QColor("#ffffff"))
            else:
                painter.fillPath(c_path, QBrush(QColor(theme["pill_bg"])))
                painter.setPen(QColor(theme["text_secondary"]))

            painter.drawText(c_rect, Qt.AlignCenter, chip_text)
            chip_x += int(tw + 20)

        # 5. Drag Handle (Far Right)
        handle_x = rect.right() - 28
        handle_y = rect.y() + (rect.height() // 2) - 8
        painter.setFont(QFont("Segoe UI", 12))
        painter.setPen(QColor(theme["text_muted"]))
        painter.drawText(handle_x, handle_y + 12, "⠿")


# ==============================================================================
# Custom Interactive List / Grid Widget
# ==============================================================================

class ImageListWidget(QListWidget):
    order_changed = pyqtSignal()
    files_dropped = pyqtSignal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setDragDropMode(QAbstractItemView.InternalMove)
        self.setDefaultDropAction(Qt.MoveAction)
        self.setAcceptDrops(True)
        self.setSpacing(6)
        self.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setResizeMode(QListWidget.Adjust)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            file_paths = []
            for url in event.mimeData().urls():
                p = url.toLocalFile()
                if os.path.exists(p):
                    file_paths.append(p)
            if file_paths:
                self.files_dropped.emit(file_paths)
            event.acceptProposedAction()
        else:
            super().dropEvent(event)
            self.order_changed.emit()


# ==============================================================================
# Worker Conversion Thread
# ==============================================================================

class WorkerConversionThread(QThread):
    progress = pyqtSignal(int, int, str)
    finished = pyqtSignal(bool, str)

    def __init__(
        self,
        entries: List[ImageEntry],
        output_path: str,
        page_size: str,
        orientation: str,
        margin_pct: float,
        grayscale: bool,
        quality: int
    ):
        super().__init__()
        self.entries = entries
        self.output_path = output_path
        self.page_size = page_size
        self.orientation = orientation
        self.margin_pct = margin_pct
        self.grayscale = grayscale
        self.quality = quality
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True

    def run(self):
        def cb(cur, tot, msg):
            self.progress.emit(cur, tot, msg)

        success, msg = convert_images_to_pdf(
            entries=self.entries,
            output_path=self.output_path,
            page_size=self.page_size,
            orientation=self.orientation,
            margin_pct=self.margin_pct,
            grayscale=self.grayscale,
            quality=self.quality,
            progress_callback=cb,
            should_cancel=lambda: self._is_cancelled
        )
        self.finished.emit(success, msg)


# ==============================================================================
# High-End Image Preview Dialog (Zoom, Navigate, Rotate)
# ==============================================================================

class ImagePreviewDialog(QDialog):
    """
    Full-featured visual previewer:
    Zoom In/Out, Fit to Window, Actual Size, Rotate 90°, and Next/Prev Page navigation.
    """
    def __init__(self, main_win: MainWindow, initial_index: int):
        super().__init__(main_win)
        self.main_win = main_win
        self.current_index = initial_index
        self.zoom_factor = 1.0
        self.base_pixmap: Optional[QPixmap] = None

        self.setWindowTitle("Document Page Inspector")
        self.resize(850, 700)
        self.setMinimumSize(600, 500)
        theme = self.main_win.current_theme
        self.setStyleSheet(f"background-color: {theme['bg_main']}; color: {theme['text_primary']};")

        self._setup_ui()
        self._load_current_page()

    def _setup_ui(self):
        theme = self.main_win.current_theme
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        # 1. Top Inspector Header Bar
        top_bar = QHBoxLayout()
        self.lbl_title = QLabel(self)
        self.lbl_title.setStyleSheet("font-size: 15px; font-weight: 700;")
        top_bar.addWidget(self.lbl_title)

        top_bar.addStretch()

        self.lbl_page_count = QLabel(self)
        self.lbl_page_count.setStyleSheet(f"font-size: 13px; color: {theme['text_secondary']}; font-weight: 600;")
        top_bar.addWidget(self.lbl_page_count)

        layout.addLayout(top_bar)

        # 2. Controls Toolbar
        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)

        btn_style = f"""
            QPushButton {{
                background-color: {theme['card_bg']};
                color: {theme['text_primary']};
                border: 1px solid {theme['card_border']};
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 12px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: {theme['card_hover']};
                border-color: {theme['accent']};
            }}
            QPushButton:disabled {{
                color: {theme['text_muted']};
                border-color: {theme['card_border']};
            }}
        """

        self.btn_prev = QPushButton("◀ Previous", self)
        self.btn_prev.setStyleSheet(btn_style)
        self.btn_prev.clicked.connect(self._on_prev)
        toolbar.addWidget(self.btn_prev)

        self.btn_next = QPushButton("Next ▶", self)
        self.btn_next.setStyleSheet(btn_style)
        self.btn_next.clicked.connect(self._on_next)
        toolbar.addWidget(self.btn_next)

        toolbar.addSpacing(16)

        btn_zoom_in = QPushButton("🔍+ Zoom In", self)
        btn_zoom_in.setStyleSheet(btn_style)
        btn_zoom_in.clicked.connect(self._zoom_in)
        toolbar.addWidget(btn_zoom_in)

        btn_zoom_out = QPushButton("🔍- Zoom Out", self)
        btn_zoom_out.setStyleSheet(btn_style)
        btn_zoom_out.clicked.connect(self._zoom_out)
        toolbar.addWidget(btn_zoom_out)

        btn_fit = QPushButton("⛶ Fit Window", self)
        btn_fit.setStyleSheet(btn_style)
        btn_fit.clicked.connect(self._fit_window)
        toolbar.addWidget(btn_fit)

        btn_actual = QPushButton("1:1 Actual", self)
        btn_actual.setStyleSheet(btn_style)
        btn_actual.clicked.connect(self._actual_size)
        toolbar.addWidget(btn_actual)

        toolbar.addSpacing(16)

        btn_rot = QPushButton("🔄 Rotate 90°", self)
        btn_rot.setStyleSheet(btn_style)
        btn_rot.clicked.connect(self._rotate_current)
        toolbar.addWidget(btn_rot)

        toolbar.addStretch()

        self.lbl_zoom = QLabel("100%", self)
        self.lbl_zoom.setStyleSheet(f"font-size: 12px; color: {theme['text_secondary']};")
        toolbar.addWidget(self.lbl_zoom)

        layout.addLayout(toolbar)

        # 3. Scrollable Viewer
        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setAlignment(Qt.AlignCenter)
        self.scroll_area.setStyleSheet(f"""
            QScrollArea {{
                background-color: {theme['bg_main']};
                border: 1px solid {theme['card_border']};
                border-radius: 8px;
            }}
        """)

        self.lbl_canvas = QLabel(self.scroll_area)
        self.lbl_canvas.setAlignment(Qt.AlignCenter)
        self.scroll_area.setWidget(self.lbl_canvas)
        layout.addWidget(self.scroll_area)

        # Bottom info & close
        bottom_bar = QHBoxLayout()
        self.lbl_meta = QLabel(self)
        self.lbl_meta.setStyleSheet(f"font-size: 12px; color: {theme['text_muted']};")
        bottom_bar.addWidget(self.lbl_meta)

        bottom_bar.addStretch()

        btn_close = QPushButton("Done", self)
        btn_close.setFixedHeight(34)
        btn_close.setStyleSheet(f"""
            QPushButton {{
                background-color: {theme['accent']};
                color: #ffffff;
                font-weight: bold;
                border-radius: 6px;
                padding: 6px 22px;
                border: none;
            }}
            QPushButton:hover {{ background-color: {theme['accent_hover']}; }}
        """)
        btn_close.clicked.connect(self.accept)
        bottom_bar.addWidget(btn_close)

        layout.addLayout(bottom_bar)

    def _load_current_page(self):
        entries = self.main_win.image_entries
        total = len(entries)
        if not (0 <= self.current_index < total):
            return

        entry = entries[self.current_index]
        self.lbl_title.setText(f"📄 {entry.filename}")
        self.lbl_page_count.setText(f"Page {self.current_index + 1} of {total}")
        self.btn_prev.setEnabled(self.current_index > 0)
        self.btn_next.setEnabled(self.current_index < total - 1)

        dims = get_image_info(entry.path)
        dim_str = f"{dims[0]} × {dims[1]} px" if dims else "Unknown"
        self.lbl_meta.setText(f"File Size: {format_file_size(entry.file_size)}  •  Dimensions: {dim_str}  •  Rotation: {entry.rotation}°")

        # Load image into pixmap
        try:
            with Image.open(entry.path) as img:
                if entry.rotation % 360 != 0:
                    img = img.rotate(-entry.rotation, expand=True)
                if img.mode not in ("RGB", "RGBA"):
                    img = img.convert("RGB")

                # Cap max size for preview display
                max_edge = 3000
                if max(img.size) > max_edge:
                    img.thumbnail((max_edge, max_edge), Image.Resampling.BILINEAR)

                data = img.tobytes("raw", img.mode)
                qformat = QImage.Format_RGBA8888 if img.mode == "RGBA" else QImage.Format_RGB888
                qimg = QImage(data, img.width, img.height, img.width * len(img.getbands()), qformat)
                self.base_pixmap = QPixmap.fromImage(qimg)
        except Exception as e:
            self.lbl_canvas.setText(f"Unable to load image:\n{e}")
            return

        self._fit_window()

    def _update_pixmap_display(self):
        if not self.base_pixmap or self.base_pixmap.isNull():
            return
        target_w = int(self.base_pixmap.width() * self.zoom_factor)
        target_h = int(self.base_pixmap.height() * self.zoom_factor)
        scaled = self.base_pixmap.scaled(
            max(10, target_w),
            max(10, target_h),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )
        self.lbl_canvas.setPixmap(scaled)
        self.lbl_zoom.setText(f"{int(self.zoom_factor * 100)}%")

    def _zoom_in(self):
        self.zoom_factor = min(4.0, self.zoom_factor * 1.25)
        self._update_pixmap_display()

    def _zoom_out(self):
        self.zoom_factor = max(0.1, self.zoom_factor / 1.25)
        self._update_pixmap_display()

    def _actual_size(self):
        self.zoom_factor = 1.0
        self._update_pixmap_display()

    def _fit_window(self):
        if not self.base_pixmap or self.base_pixmap.isNull():
            return
        avail_w = max(50, self.scroll_area.viewport().width() - 30)
        avail_h = max(50, self.scroll_area.viewport().height() - 30)
        scale_w = avail_w / self.base_pixmap.width()
        scale_h = avail_h / self.base_pixmap.height()
        self.zoom_factor = min(1.0, min(scale_w, scale_h))
        self._update_pixmap_display()

    def _rotate_current(self):
        entry = self.main_win.image_entries[self.current_index]
        entry.rotation = (entry.rotation + 90) % 360
        self.main_win.invalidate_thumbnail(entry)
        self.main_win.refresh_ui()
        self._load_current_page()

    def _on_prev(self):
        if self.current_index > 0:
            self.current_index -= 1
            self._load_current_page()

    def _on_next(self):
        if self.current_index < len(self.main_win.image_entries) - 1:
            self.current_index += 1
            self._load_current_page()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Left:
            self._on_prev()
        elif event.key() == Qt.Key_Right:
            self._on_next()
        elif event.key() in (Qt.Key_Plus, Qt.Key_Equal):
            self._zoom_in()
        elif event.key() == Qt.Key_Minus:
            self._zoom_out()
        elif event.key() == Qt.Key_Escape:
            self.accept()
        else:
            super().keyPressEvent(event)


# ==============================================================================
# Main Application Window
# ==============================================================================

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Image to PDF Studio")
        self.resize(1180, 760)
        self.setMinimumSize(920, 600)

        # Set application icon
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        # State
        self.current_theme = Theme.LIGHT
        self.view_mode = "grid"  # 'grid' or 'list'
        self.image_entries: List[ImageEntry] = []
        self.thumbnail_cache = {}
        self.worker_thread: Optional[WorkerConversionThread] = None

        self._setup_ui()
        self._apply_theme()
        self.refresh_ui()

    # ---------------- UI Construction ----------------
    def _setup_ui(self):
        self.central_widget = QWidget(self)
        self.central_widget.setObjectName("centralWidget")
        self.setCentralWidget(self.central_widget)

        main_layout = QVBoxLayout(self.central_widget)
        main_layout.setContentsMargins(18, 16, 18, 16)
        main_layout.setSpacing(14)

        # 1. Sleek Navigation Header
        header_layout = QHBoxLayout()
        header_layout.setSpacing(12)

        # Logo / Title
        logo_box = QVBoxLayout()
        logo_box.setSpacing(2)

        title_row = QHBoxLayout()
        self.lbl_app_title = QLabel("📄 Image to PDF Studio", self)
        self.lbl_app_title.setStyleSheet("font-size: 21px; font-weight: 800; letter-spacing: -0.5px;")
        title_row.addWidget(self.lbl_app_title)

        self.badge_pages = QLabel("0 Pages", self)
        self.badge_pages.setStyleSheet("""
            background-color: #2563eb;
            color: #ffffff;
            font-size: 11px;
            font-weight: 700;
            border-radius: 10px;
            padding: 3px 10px;
        """)
        title_row.addWidget(self.badge_pages)
        title_row.addStretch()
        logo_box.addLayout(title_row)

        self.lbl_subtitle = QLabel("Convert, reorder, and optimize image documents for printing and sharing", self)
        self.lbl_subtitle.setStyleSheet("font-size: 12px; color: #64748b;")
        logo_box.addWidget(self.lbl_subtitle)

        header_layout.addLayout(logo_box)
        header_layout.addStretch()

        # Header Action Buttons
        self.btn_add_files_header = QPushButton("➕ Add Images...", self)
        self.btn_add_files_header.setCursor(Qt.PointingHandCursor)
        self.btn_add_files_header.clicked.connect(self._on_add_files)
        header_layout.addWidget(self.btn_add_files_header)

        self.btn_add_folder_header = QPushButton("📁 Add Folder...", self)
        self.btn_add_folder_header.setCursor(Qt.PointingHandCursor)
        self.btn_add_folder_header.clicked.connect(self._on_add_folder)
        header_layout.addWidget(self.btn_add_folder_header)

        self.btn_theme_toggle = QPushButton("🌙 Dark", self)
        self.btn_theme_toggle.setCursor(Qt.PointingHandCursor)
        self.btn_theme_toggle.setToolTip("Toggle Dark/Light Theme")
        self.btn_theme_toggle.clicked.connect(self._toggle_theme)
        header_layout.addWidget(self.btn_theme_toggle)

        main_layout.addLayout(header_layout)

        # 2. Body Splitter (Left: Workspace / Dropzone / List, Right: Studio Settings)
        self.splitter = QSplitter(Qt.Horizontal, self)
        self.splitter.setChildrenCollapsible(False)

        # ---------------- LEFT PANEL ----------------
        left_container = QWidget(self)
        left_layout = QVBoxLayout(left_container)
        left_layout.setContentsMargins(0, 0, 10, 0)
        left_layout.setSpacing(10)

        # Sub-header toolbar for view toggles & ordering
        self.tool_row = QHBoxLayout()
        self.tool_row.setSpacing(6)

        # View Mode Toggle (Grid Cards vs Detailed List)
        self.btn_view_grid = QPushButton("⊞ Grid", self)
        self.btn_view_grid.setCheckable(True)
        self.btn_view_grid.setChecked(True)
        self.btn_view_grid.clicked.connect(lambda: self._set_view_mode("grid"))
        self.tool_row.addWidget(self.btn_view_grid)

        self.btn_view_list = QPushButton("☰ List", self)
        self.btn_view_list.setCheckable(True)
        self.btn_view_list.setChecked(False)
        self.btn_view_list.clicked.connect(lambda: self._set_view_mode("list"))
        self.tool_row.addWidget(self.btn_view_list)

        self.tool_row.addSpacing(12)

        # Reorder actions
        self.btn_move_up = QPushButton("⬆️ Up", self)
        self.btn_move_up.setToolTip("Move selected page up (Alt+Up)")
        self.btn_move_up.clicked.connect(self._on_move_up)
        self.tool_row.addWidget(self.btn_move_up)

        self.btn_move_down = QPushButton("⬇️ Down", self)
        self.btn_move_down.setToolTip("Move selected page down (Alt+Down)")
        self.btn_move_down.clicked.connect(self._on_move_down)
        self.tool_row.addWidget(self.btn_move_down)

        self.btn_move_top = QPushButton("⏫ Top", self)
        self.btn_move_top.clicked.connect(self._on_move_top)
        self.tool_row.addWidget(self.btn_move_top)

        self.btn_move_bottom = QPushButton("⏬ Bottom", self)
        self.btn_move_bottom.clicked.connect(self._on_move_bottom)
        self.tool_row.addWidget(self.btn_move_bottom)

        self.tool_row.addSpacing(12)

        self.btn_rotate = QPushButton("🔄 Rotate", self)
        self.btn_rotate.setToolTip("Rotate selected images 90° clockwise")
        self.btn_rotate.clicked.connect(self._on_rotate_selected)
        self.tool_row.addWidget(self.btn_rotate)

        self.btn_sort = QPushButton("🔃 Sort ▼", self)
        self.btn_sort.clicked.connect(self._show_sort_menu)
        self.tool_row.addWidget(self.btn_sort)

        self.btn_preview = QPushButton("👁️ Preview", self)
        self.btn_preview.clicked.connect(self._on_preview_selected)
        self.tool_row.addWidget(self.btn_preview)

        self.tool_row.addStretch()

        self.btn_remove = QPushButton("🗑️ Remove", self)
        self.btn_remove.clicked.connect(self._on_remove_selected)
        self.tool_row.addWidget(self.btn_remove)

        self.btn_clear = QPushButton("🧹 Clear All", self)
        self.btn_clear.clicked.connect(self._on_clear_all)
        self.tool_row.addWidget(self.btn_clear)

        left_layout.addLayout(self.tool_row)

        # Stacked Center Area (Page 0: Empty Drop Zone, Page 1: Active Image List)
        self.stack = QStackedWidget(self)

        # Empty State Dropzone Widget
        self.empty_widget = QWidget(self)
        empty_layout = QVBoxLayout(self.empty_widget)
        empty_layout.setAlignment(Qt.AlignCenter)
        empty_layout.setContentsMargins(40, 40, 40, 40)
        empty_layout.setSpacing(16)

        self.drop_card = QFrame(self.empty_widget)
        self.drop_card.setMinimumSize(480, 360)
        drop_inner_layout = QVBoxLayout(self.drop_card)
        drop_inner_layout.setAlignment(Qt.AlignCenter)
        drop_inner_layout.setSpacing(14)

        icon_lbl = QLabel("📥", self.drop_card)
        icon_lbl.setStyleSheet("font-size: 56px;")
        icon_lbl.setAlignment(Qt.AlignCenter)
        drop_inner_layout.addWidget(icon_lbl)

        title_drop = QLabel("Drag & Drop Images Here", self.drop_card)
        title_drop.setStyleSheet("font-size: 20px; font-weight: 700;")
        title_drop.setAlignment(Qt.AlignCenter)
        drop_inner_layout.addWidget(title_drop)

        sub_drop = QLabel("Supports PNG, JPG, WEBP, TIFF, BMP, GIF & more\nor click below to browse from your device", self.drop_card)
        sub_drop.setStyleSheet("font-size: 13px; color: #64748b; line-height: 1.4;")
        sub_drop.setAlignment(Qt.AlignCenter)
        drop_inner_layout.addWidget(sub_drop)

        btn_row_drop = QHBoxLayout()
        btn_row_drop.setAlignment(Qt.AlignCenter)
        btn_row_drop.setSpacing(10)

        self.btn_browse_empty = QPushButton("➕ Browse Images...", self.drop_card)
        self.btn_browse_empty.setFixedHeight(40)
        self.btn_browse_empty.setCursor(Qt.PointingHandCursor)
        self.btn_browse_empty.clicked.connect(self._on_add_files)
        btn_row_drop.addWidget(self.btn_browse_empty)

        self.btn_folder_empty = QPushButton("📁 Add Folder...", self.drop_card)
        self.btn_folder_empty.setFixedHeight(40)
        self.btn_folder_empty.setCursor(Qt.PointingHandCursor)
        self.btn_folder_empty.clicked.connect(self._on_add_folder)
        btn_row_drop.addWidget(self.btn_folder_empty)

        drop_inner_layout.addLayout(btn_row_drop)

        pills_lbl = QLabel("⚡ Visual Drag Reorder  •  📐 Fit to A4 / Letter  •  🔒 100% Offline & Private", self.drop_card)
        pills_lbl.setStyleSheet("font-size: 11px; color: #94a3b8; font-weight: 600; margin-top: 10px;")
        pills_lbl.setAlignment(Qt.AlignCenter)
        drop_inner_layout.addWidget(pills_lbl)

        empty_layout.addWidget(self.drop_card)
        self.stack.addWidget(self.empty_widget)

        # Active Image List Widget
        self.list_widget = ImageListWidget(self)
        self.delegate = ImageItemDelegate(self)
        self.list_widget.setItemDelegate(self.delegate)
        self.list_widget.order_changed.connect(self._sync_list_to_entries)
        self.list_widget.files_dropped.connect(self._add_paths)
        self.list_widget.itemDoubleClicked.connect(self._on_preview_selected)
        self.stack.addWidget(self.list_widget)

        left_layout.addWidget(self.stack)

        self.lbl_left_tip = QLabel("💡 Tip: Drag items to reorder pages. Double click or press Preview to inspect.", self)
        self.lbl_left_tip.setStyleSheet("font-size: 11px; color: #64748b; font-style: italic;")
        left_layout.addWidget(self.lbl_left_tip)

        self.splitter.addWidget(left_container)

        # ---------------- RIGHT PANEL (Studio Controls) ----------------
        right_container = QWidget(self)
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(10, 0, 0, 0)
        right_layout.setSpacing(12)

        # Header for Right Panel
        panel_title = QLabel("⚙️ PDF Generation Settings", self)
        panel_title.setStyleSheet("font-size: 15px; font-weight: 700; margin-bottom: 2px;")
        right_layout.addWidget(panel_title)

        # Card 1: Page Layout
        self.card_layout = QGroupBox("📐 Page Geometry & Sizing", self)
        c1_layout = QVBoxLayout(self.card_layout)
        c1_layout.setSpacing(10)

        # Page Size
        r_size = QHBoxLayout()
        r_size.addWidget(QLabel("Page Size:", self))
        self.combo_page_size = QComboBox(self)
        self.combo_page_size.addItems([
            "Original (Preserve 1:1 Image Size)",
            "A4 Standard (210 × 297 mm)",
            "US Letter (8.5 × 11 in)",
            "US Legal (8.5 × 14 in)",
            "A3 Large (297 × 420 mm)",
            "A5 Compact (148 × 210 mm)"
        ])
        r_size.addWidget(self.combo_page_size, stretch=1)
        c1_layout.addLayout(r_size)

        # Orientation
        r_orient = QHBoxLayout()
        r_orient.addWidget(QLabel("Orientation:", self))
        self.combo_orient = QComboBox(self)
        self.combo_orient.addItems([
            "Auto (Match each image aspect)",
            "Portrait",
            "Landscape"
        ])
        r_orient.addWidget(self.combo_orient, stretch=1)
        c1_layout.addLayout(r_orient)

        # Margins
        r_margin = QHBoxLayout()
        r_margin.addWidget(QLabel("Page Margins:", self))
        self.combo_margin = QComboBox(self)
        self.combo_margin.addItems([
            "None (0% - Full Bleed)",
            "Small (2%)",
            "Normal (5%)",
            "Wide (10%)"
        ])
        r_margin.addWidget(self.combo_margin, stretch=1)
        c1_layout.addLayout(r_margin)

        right_layout.addWidget(self.card_layout)

        # Card 2: Quality & Appearance
        self.card_quality = QGroupBox("🎨 Quality & Compression", self)
        c2_layout = QVBoxLayout(self.card_quality)
        c2_layout.setSpacing(10)

        # Slider for Quality
        q_head = QHBoxLayout()
        q_head.addWidget(QLabel("JPEG Quality:", self))
        self.lbl_quality_val = QLabel("90% • High Quality", self)
        self.lbl_quality_val.setStyleSheet("font-weight: 700; color: #2563eb;")
        q_head.addStretch()
        q_head.addWidget(self.lbl_quality_val)
        c2_layout.addLayout(q_head)

        self.slider_quality = QSlider(Qt.Horizontal, self)
        self.slider_quality.setRange(20, 100)
        self.slider_quality.setValue(90)
        self.slider_quality.setSingleStep(5)
        self.slider_quality.valueChanged.connect(self._on_quality_changed)
        c2_layout.addWidget(self.slider_quality)

        # Color Mode
        r_color = QHBoxLayout()
        r_color.addWidget(QLabel("Color Profile:", self))
        self.combo_color = QComboBox(self)
        self.combo_color.addItems([
            "Full Color (RGB)",
            "Grayscale (Black & White)"
        ])
        r_color.addWidget(self.combo_color, stretch=1)
        c2_layout.addLayout(r_color)

        right_layout.addWidget(self.card_quality)

        # Card 3: Document Summary
        self.card_summary = QGroupBox("📊 Document Summary", self)
        c3_layout = QVBoxLayout(self.card_summary)
        c3_layout.setSpacing(6)

        self.lbl_sum_pages = QLabel("Total Pages: 0", self)
        self.lbl_sum_size = QLabel("Source Images Size: 0 MB", self)
        self.lbl_sum_format = QLabel("Output Mode: Multi-Page PDF", self)
        for lbl in (self.lbl_sum_pages, self.lbl_sum_size, self.lbl_sum_format):
            lbl.setStyleSheet("font-size: 12px; color: #64748b;")
            c3_layout.addWidget(lbl)

        right_layout.addWidget(self.card_summary)

        # Card 4: Post-Actions
        self.card_post = QGroupBox("⚡ Options on Completion", self)
        c4_layout = QVBoxLayout(self.card_post)
        c4_layout.setSpacing(8)

        self.chk_open_pdf = QCheckBox("Open PDF document immediately", self)
        self.chk_open_pdf.setChecked(True)
        c4_layout.addWidget(self.chk_open_pdf)

        self.chk_open_folder = QCheckBox("Show in Windows File Explorer", self)
        self.chk_open_folder.setChecked(False)
        c4_layout.addWidget(self.chk_open_folder)

        right_layout.addWidget(self.card_post)

        right_layout.addStretch()

        # Conversion Section & Progress
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setVisible(False)
        right_layout.addWidget(self.progress_bar)

        self.lbl_status = QLabel("Add images to begin", self)
        self.lbl_status.setAlignment(Qt.AlignCenter)
        right_layout.addWidget(self.lbl_status)

        self.btn_convert = QPushButton("⚡ Generate PDF", self)
        self.btn_convert.setFixedHeight(50)
        self.btn_convert.setCursor(Qt.PointingHandCursor)
        self.btn_convert.clicked.connect(self._on_convert_clicked)
        right_layout.addWidget(self.btn_convert)

        self.splitter.addWidget(right_container)
        self.splitter.setStretchFactor(0, 3)
        self.splitter.setStretchFactor(1, 2)

        main_layout.addWidget(self.splitter)

    # ---------------- Theme Engine ----------------
    def _toggle_theme(self):
        if self.current_theme == Theme.LIGHT:
            self.current_theme = Theme.DARK
            self.btn_theme_toggle.setText("☀️ Light")
        else:
            self.current_theme = Theme.LIGHT
            self.btn_theme_toggle.setText("🌙 Dark")
        self._apply_theme()
        self.list_widget.viewport().update()

    def _apply_theme(self):
        t = self.current_theme
        self.setStyleSheet(get_stylesheet(t))

        # Dropzone Card styling
        self.drop_card.setStyleSheet(f"""
            QFrame {{
                background-color: {t['card_bg']};
                border: 2px dashed {t['card_border']};
                border-radius: 16px;
            }}
            QFrame:hover {{
                border-color: {t['accent']};
            }}
        """)

        # Primary Buttons
        primary_btn = f"""
            QPushButton {{
                background-color: {t['accent']};
                color: #ffffff;
                font-weight: 700;
                font-size: 13px;
                border-radius: 8px;
                padding: 8px 16px;
                border: none;
            }}
            QPushButton:hover {{ background-color: {t['accent_hover']}; }}
            QPushButton:disabled {{
                background-color: {t['pill_bg']};
                color: {t['text_muted']};
            }}
        """
        self.btn_add_files_header.setStyleSheet(primary_btn)
        self.btn_browse_empty.setStyleSheet(primary_btn)

        # Secondary Buttons
        secondary_btn = f"""
            QPushButton {{
                background-color: {t['card_bg']};
                color: {t['text_primary']};
                font-weight: 600;
                font-size: 13px;
                border-radius: 8px;
                padding: 7px 14px;
                border: 1px solid {t['card_border']};
            }}
            QPushButton:hover {{
                background-color: {t['card_hover']};
                border-color: {t['accent']};
            }}
        """
        self.btn_add_folder_header.setStyleSheet(secondary_btn)
        self.btn_folder_empty.setStyleSheet(secondary_btn)
        self.btn_theme_toggle.setStyleSheet(secondary_btn)

        # Tool buttons in list bar
        tool_btn = f"""
            QPushButton {{
                background-color: {t['card_bg']};
                color: {t['text_primary']};
                font-size: 12px;
                font-weight: 600;
                border-radius: 6px;
                padding: 6px 10px;
                border: 1px solid {t['card_border']};
            }}
            QPushButton:hover {{
                background-color: {t['card_hover']};
                border-color: {t['accent']};
                color: {t['accent']};
            }}
            QPushButton:checked {{
                background-color: {t['accent_light']};
                border-color: {t['accent']};
                color: {t['accent_text']};
            }}
            QPushButton:disabled {{
                color: {t['text_muted']};
                border-color: {t['card_border']};
            }}
        """
        for b in (self.btn_view_grid, self.btn_view_list, self.btn_move_up, self.btn_move_down,
                  self.btn_move_top, self.btn_move_bottom, self.btn_rotate, self.btn_sort, self.btn_preview):
            b.setStyleSheet(tool_btn)

        danger_btn = f"""
            QPushButton {{
                background-color: {t['card_bg']};
                color: {t['danger']};
                font-size: 12px;
                font-weight: 600;
                border-radius: 6px;
                padding: 6px 12px;
                border: 1px solid {t['card_border']};
            }}
            QPushButton:hover {{
                background-color: {t['danger_light']};
                border-color: {t['danger']};
            }}
            QPushButton:disabled {{
                color: {t['text_muted']};
                border-color: {t['card_border']};
            }}
        """
        self.btn_remove.setStyleSheet(danger_btn)
        self.btn_clear.setStyleSheet(secondary_btn)

        # List Widget styling
        self.list_widget.setStyleSheet(f"""
            QListWidget {{
                background-color: {t['bg_main']};
                border: none;
                outline: none;
            }}
        """)

        # Group boxes
        group_style = f"""
            QGroupBox {{
                background-color: {t['card_bg']};
                border: 1px solid {t['card_border']};
                border-radius: 10px;
                font-size: 13px;
                font-weight: 700;
                color: {t['text_primary']};
                margin-top: 10px;
                padding-top: 14px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 8px;
                color: {t['text_primary']};
            }}
        """
        for g in (self.card_layout, self.card_quality, self.card_summary, self.card_post):
            g.setStyleSheet(group_style)

        # Combos
        combo_style = f"""
            QComboBox {{
                background-color: {t['card_bg']};
                border: 1px solid {t['card_border']};
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 12px;
                color: {t['text_primary']};
            }}
            QComboBox:hover {{ border-color: {t['accent']}; }}
            QComboBox::drop-down {{ border: none; width: 20px; }}
            QComboBox QAbstractItemView {{
                background-color: {t['card_bg']};
                border: 1px solid {t['card_border']};
                selection-background-color: {t['card_selected']};
                selection-color: {t['accent']};
                color: {t['text_primary']};
                padding: 4px;
            }}
        """
        for c in (self.combo_page_size, self.combo_orient, self.combo_margin, self.combo_color):
            c.setStyleSheet(combo_style)

        # Sliders
        self.slider_quality.setStyleSheet(f"""
            QSlider::groove:horizontal {{
                border-radius: 3px;
                height: 6px;
                background-color: {t['pill_bg']};
            }}
            QSlider::sub-page:horizontal {{
                background-color: {t['accent']};
                border-radius: 3px;
            }}
            QSlider::handle:horizontal {{
                background-color: #ffffff;
                border: 2px solid {t['accent']};
                width: 16px;
                height: 16px;
                margin-top: -5px;
                margin-bottom: -5px;
                border-radius: 8px;
            }}
        """)

        # Big Conversion Button
        self.btn_convert.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {t['accent']}, stop:1 #4f46e5);
                color: #ffffff;
                font-size: 15px;
                font-weight: 800;
                letter-spacing: 0.5px;
                border-radius: 10px;
                border: none;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {t['accent_hover']}, stop:1 #4338ca);
            }}
            QPushButton:disabled {{
                background: {t['pill_bg']};
                color: {t['text_muted']};
            }}
        """)

        # Progress bar
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                border: 1px solid {t['card_border']};
                border-radius: 6px;
                text-align: center;
                height: 22px;
                background-color: {t['pill_bg']};
                font-size: 11px;
                font-weight: 700;
                color: {t['text_primary']};
            }}
            QProgressBar::chunk {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {t['accent']}, stop:1 #6366f1);
                border-radius: 5px;
            }}
        """)

        # Splitter handle
        self.splitter.setStyleSheet(f"""
            QSplitter::handle {{
                background-color: {t['card_border']};
                width: 2px;
            }}
        """)

    def _set_view_mode(self, mode: str):
        self.view_mode = mode
        if mode == "grid":
            self.btn_view_grid.setChecked(True)
            self.btn_view_list.setChecked(False)
            self.list_widget.setViewMode(QListWidget.IconMode)
            self.list_widget.setGridSize(QSize(160, 200))
        else:
            self.btn_view_grid.setChecked(False)
            self.btn_view_list.setChecked(True)
            self.list_widget.setViewMode(QListWidget.ListMode)
            self.list_widget.setGridSize(QSize())
        self.list_widget.viewport().update()

    def _on_quality_changed(self, val: int):
        if val >= 95:
            desc = "Maximum (Near Lossless)"
        elif val >= 85:
            desc = "High Quality (Recommended)"
        elif val >= 65:
            desc = "Balanced Compression"
        else:
            desc = "Compact (Smallest File)"
        self.lbl_quality_val.setText(f"{val}% • {desc}")

    # ---------------- File Management ----------------
    def _on_add_files(self):
        filters = (
            "All Image Formats (*.png *.jpg *.jpeg *.webp *.bmp *.tiff *.tif *.gif *.ico *.jfif);;"
            "PNG Images (*.png);;"
            "JPEG Images (*.jpg *.jpeg *.jfif);;"
            "WEBP Images (*.webp);;"
            "BMP Images (*.bmp);;"
            "TIFF Images (*.tiff *.tif);;"
            "All Files (*.*)"
        )
        files, _ = QFileDialog.getOpenFileNames(self, "Select Images to Convert", "", filters)
        if files:
            self._add_paths(files)

    def _on_add_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Folder Containing Images")
        if folder:
            found = []
            for root, _, files in os.walk(folder):
                for f in sorted(files):
                    if os.path.splitext(f)[1].lower() in SUPPORTED_EXTENSIONS:
                        found.append(os.path.join(root, f))
            if found:
                self._add_paths(found)
            else:
                QMessageBox.information(self, "No Images Found", f"No supported image files found in:\n{folder}")

    def _add_paths(self, paths: List[str]):
        new_entries = []
        for p in paths:
            norm_p = os.path.abspath(p)
            if os.path.isdir(norm_p):
                for root, _, files in os.walk(norm_p):
                    for f in sorted(files):
                        if os.path.splitext(f)[1].lower() in SUPPORTED_EXTENSIONS:
                            new_entries.append(ImageEntry(path=os.path.join(root, f)))
            elif os.path.isfile(norm_p):
                if os.path.splitext(norm_p)[1].lower() in SUPPORTED_EXTENSIONS:
                    new_entries.append(ImageEntry(path=norm_p))

        if new_entries:
            self.image_entries.extend(new_entries)
            self._rebuild_list_items()
            self.refresh_ui()

    def get_thumbnail_pixmap(self, entry: ImageEntry) -> QPixmap:
        cache_key = (entry.path, entry.rotation)
        if cache_key in self.thumbnail_cache:
            return self.thumbnail_cache[cache_key]

        try:
            with Image.open(entry.path) as img:
                if entry.rotation % 360 != 0:
                    img = img.rotate(-entry.rotation, expand=True)
                if img.mode not in ("RGB", "RGBA"):
                    img = img.convert("RGB")

                img.thumbnail((160, 160), Image.Resampling.BILINEAR)
                data = img.tobytes("raw", img.mode)
                qformat = QImage.Format_RGBA8888 if img.mode == "RGBA" else QImage.Format_RGB888
                qimg = QImage(data, img.width, img.height, img.width * len(img.getbands()), qformat)
                pix = QPixmap.fromImage(qimg)
                self.thumbnail_cache[cache_key] = pix
                return pix
        except Exception:
            pix = QPixmap(100, 100)
            pix.fill(QColor("#94a3b8"))
            return pix

    def invalidate_thumbnail(self, entry: ImageEntry):
        keys_to_del = [k for k in self.thumbnail_cache if k[0] == entry.path]
        for k in keys_to_del:
            del self.thumbnail_cache[k]

    def _rebuild_list_items(self):
        selected_indexes = [self.list_widget.row(item) for item in self.list_widget.selectedItems()]
        self.list_widget.clear()

        for entry in self.image_entries:
            item = QListWidgetItem()
            item.setData(Qt.UserRole, entry)
            self.list_widget.addItem(item)

        for idx in selected_indexes:
            if idx < self.list_widget.count():
                self.list_widget.item(idx).setSelected(True)

    def _sync_list_to_entries(self):
        new_entries = []
        for i in range(self.list_widget.count()):
            entry = self.list_widget.item(i).data(Qt.UserRole)
            if entry:
                new_entries.append(entry)
        self.image_entries = new_entries
        self.refresh_ui()

    def refresh_ui(self):
        count = len(self.image_entries)
        total_size = sum(e.file_size for e in self.image_entries)
        size_str = format_file_size(total_size)

        # Switch between Empty State and List
        if count == 0:
            self.stack.setCurrentIndex(0)
            self.badge_pages.setText("0 Pages")
            self.btn_convert.setText("⚡ Generate PDF")
            self.btn_convert.setEnabled(False)
            self.lbl_status.setText("Drop images into the canvas above to begin")
        else:
            self.stack.setCurrentIndex(1)
            self.badge_pages.setText(f"{count} Pages")
            self.btn_convert.setText(f"⚡ Generate PDF ({count} Pages)")
            self.btn_convert.setEnabled(True)
            self.lbl_status.setText(f"Ready to assemble {count} pages ({size_str})")

        has_items = count > 0
        has_sel = len(self.list_widget.selectedItems()) > 0

        self.btn_move_up.setEnabled(has_sel)
        self.btn_move_down.setEnabled(has_sel)
        self.btn_move_top.setEnabled(has_sel)
        self.btn_move_bottom.setEnabled(has_sel)
        self.btn_rotate.setEnabled(has_sel)
        self.btn_preview.setEnabled(has_sel)
        self.btn_remove.setEnabled(has_sel)
        self.btn_sort.setEnabled(has_items)
        self.btn_clear.setEnabled(has_items)

        # Update summary card
        self.lbl_sum_pages.setText(f"Total Pages: {count}")
        self.lbl_sum_size.setText(f"Source Images Size: {size_str}")

        self.list_widget.viewport().update()

    # ---------------- Ordering Operations ----------------
    def _on_move_up(self):
        rows = sorted([self.list_widget.row(item) for item in self.list_widget.selectedItems()])
        if not rows or rows[0] == 0:
            return
        for r in rows:
            self.image_entries[r - 1], self.image_entries[r] = (
                self.image_entries[r],
                self.image_entries[r - 1],
            )
        self._rebuild_list_items()
        for r in rows:
            self.list_widget.item(r - 1).setSelected(True)
        self.refresh_ui()

    def _on_move_down(self):
        rows = sorted([self.list_widget.row(item) for item in self.list_widget.selectedItems()], reverse=True)
        if not rows or rows[0] == len(self.image_entries) - 1:
            return
        for r in rows:
            self.image_entries[r + 1], self.image_entries[r] = (
                self.image_entries[r],
                self.image_entries[r + 1],
            )
        self._rebuild_list_items()
        for r in rows:
            self.list_widget.item(r + 1).setSelected(True)
        self.refresh_ui()

    def _on_move_top(self):
        rows = sorted([self.list_widget.row(item) for item in self.list_widget.selectedItems()])
        if not rows or rows[0] == 0:
            return
        selected = [self.image_entries[r] for r in rows]
        remaining = [e for i, e in enumerate(self.image_entries) if i not in rows]
        self.image_entries = selected + remaining
        self._rebuild_list_items()
        for i in range(len(selected)):
            self.list_widget.item(i).setSelected(True)
        self.refresh_ui()

    def _on_move_bottom(self):
        rows = sorted([self.list_widget.row(item) for item in self.list_widget.selectedItems()])
        if not rows or rows[-1] == len(self.image_entries) - 1:
            return
        selected = [self.image_entries[r] for r in rows]
        remaining = [e for i, e in enumerate(self.image_entries) if i not in rows]
        self.image_entries = remaining + selected
        self._rebuild_list_items()
        start = len(remaining)
        for i in range(start, start + len(selected)):
            self.list_widget.item(i).setSelected(True)
        self.refresh_ui()

    def _on_rotate_selected(self):
        items = self.list_widget.selectedItems()
        if not items:
            return
        for it in items:
            entry = it.data(Qt.UserRole)
            if entry:
                entry.rotation = (entry.rotation + 90) % 360
                self.invalidate_thumbnail(entry)
        self.list_widget.viewport().update()

    def _on_remove_selected(self):
        rows = sorted([self.list_widget.row(item) for item in self.list_widget.selectedItems()], reverse=True)
        if not rows:
            return
        for r in rows:
            del self.image_entries[r]
        self._rebuild_list_items()
        self.refresh_ui()

    def _on_clear_all(self):
        if not self.image_entries:
            return
        reply = QMessageBox.question(
            self,
            "Clear Document Canvas",
            "Are you sure you want to remove all images from the current project?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.image_entries.clear()
            self.thumbnail_cache.clear()
            self._rebuild_list_items()
            self.refresh_ui()

    def _show_sort_menu(self):
        t = self.current_theme
        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{
                background-color: {t['card_bg']};
                border: 1px solid {t['card_border']};
                border-radius: 8px;
                padding: 6px;
            }}
            QMenu::item {{
                padding: 7px 22px;
                font-size: 13px;
                color: {t['text_primary']};
                border-radius: 4px;
            }}
            QMenu::item:selected {{
                background-color: {t['card_hover']};
                color: {t['accent']};
            }}
        """)

        act_name_asc = menu.addAction("Sort by Name (A → Z)")
        act_name_desc = menu.addAction("Sort by Name (Z → A)")
        menu.addSeparator()
        act_size_asc = menu.addAction("Sort by File Size (Small → Large)")
        act_size_desc = menu.addAction("Sort by File Size (Large → Small)")
        menu.addSeparator()
        act_reverse = menu.addAction("Reverse Current Page Order")

        action = menu.exec_(self.btn_sort.mapToGlobal(QPoint(0, self.btn_sort.height())))
        if action == act_name_asc:
            self.image_entries.sort(key=lambda e: e.filename.lower())
        elif action == act_name_desc:
            self.image_entries.sort(key=lambda e: e.filename.lower(), reverse=True)
        elif action == act_size_asc:
            self.image_entries.sort(key=lambda e: e.file_size)
        elif action == act_size_desc:
            self.image_entries.sort(key=lambda e: e.file_size, reverse=True)
        elif action == act_reverse:
            self.image_entries.reverse()

        if action:
            self._rebuild_list_items()
            self.refresh_ui()

    def _on_preview_selected(self):
        items = self.list_widget.selectedItems()
        if not items:
            idx = 0 if self.image_entries else -1
        else:
            idx = self.list_widget.row(items[0])

        if idx >= 0:
            dlg = ImagePreviewDialog(self, idx)
            dlg.exec_()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Delete:
            self._on_remove_selected()
        elif event.modifiers() & Qt.AltModifier and event.key() == Qt.Key_Up:
            self._on_move_up()
        elif event.modifiers() & Qt.AltModifier and event.key() == Qt.Key_Down:
            self._on_move_down()
        else:
            super().keyPressEvent(event)

    # ---------------- PDF Conversion ----------------
    def _on_convert_clicked(self):
        if not self.image_entries:
            QMessageBox.warning(self, "No Images", "Please add images before converting.")
            return

        first_dir = os.path.dirname(self.image_entries[0].path)
        default_name = os.path.splitext(self.image_entries[0].filename)[0] + ".pdf"
        default_path = os.path.join(first_dir, default_name)

        save_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Assembled PDF Document",
            default_path,
            "PDF Document (*.pdf);;All Files (*.*)"
        )
        if not save_path:
            return

        if not save_path.lower().endswith(".pdf"):
            save_path += ".pdf"

        # Map options
        size_map = {
            0: "original",
            1: "A4",
            2: "Letter",
            3: "Legal",
            4: "A3",
            5: "A5"
        }
        page_size = size_map.get(self.combo_page_size.currentIndex(), "original")

        orient_map = {0: "auto", 1: "portrait", 2: "landscape"}
        orientation = orient_map.get(self.combo_orient.currentIndex(), "auto")

        margin_map = {0: 0.0, 1: 2.0, 2: 5.0, 3: 10.0}
        margin_pct = margin_map.get(self.combo_margin.currentIndex(), 0.0)

        quality = self.slider_quality.value()
        grayscale = (self.combo_color.currentIndex() == 1)

        # UI state
        self._set_conversion_ui_active(True)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(True)

        self.worker_thread = WorkerConversionThread(
            entries=list(self.image_entries),
            output_path=save_path,
            page_size=page_size,
            orientation=orientation,
            margin_pct=margin_pct,
            grayscale=grayscale,
            quality=quality
        )
        self.worker_thread.progress.connect(self._on_conversion_progress)
        self.worker_thread.finished.connect(lambda s, m: self._on_conversion_finished(s, m, save_path))
        self.worker_thread.start()

    def _set_conversion_ui_active(self, converting: bool):
        self.btn_convert.setEnabled(not converting)
        self.btn_add_files_header.setEnabled(not converting)
        self.btn_add_folder_header.setEnabled(not converting)
        self.btn_clear.setEnabled(not converting)
        self.btn_remove.setEnabled(not converting)
        if converting:
            self.btn_convert.setText("⏳ Processing Pages...")
        else:
            self.refresh_ui()

    def _on_conversion_progress(self, current: int, total: int, message: str):
        pct = int((current / max(1, total)) * 100)
        self.progress_bar.setValue(pct)
        self.lbl_status.setText(message)

    def _on_conversion_finished(self, success: bool, message: str, pdf_path: str):
        self._set_conversion_ui_active(False)
        self.progress_bar.setVisible(False)

        if success:
            self.lbl_status.setText("PDF compiled successfully!")

            if self.chk_open_pdf.isChecked():
                try:
                    os.startfile(pdf_path)
                except Exception as e:
                    print(f"Error launching PDF: {e}")

            if self.chk_open_folder.isChecked():
                try:
                    subprocess.run(["explorer", f"/select,{os.path.normpath(pdf_path)}"])
                except Exception as e:
                    print(f"Error opening folder: {e}")

            # Modern Completion Dialog
            t = self.current_theme
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("PDF Document Ready")
            msg_box.setText(f"🎉 <b>Successfully created PDF!</b>")
            msg_box.setInformativeText(
                f"<b>File:</b> {os.path.basename(pdf_path)}<br>"
                f"<b>Total Pages:</b> {len(self.image_entries)}<br>"
                f"<b>Location:</b> {pdf_path}"
            )
            msg_box.setIcon(QMessageBox.Information)

            btn_open = msg_box.addButton("Open PDF", QMessageBox.ActionRole)
            btn_folder = msg_box.addButton("Show in Folder", QMessageBox.ActionRole)
            msg_box.addButton("Close", QMessageBox.RejectRole)

            msg_box.exec_()
            clicked = msg_box.clickedButton()
            if clicked == btn_open:
                try:
                    os.startfile(pdf_path)
                except Exception:
                    pass
            elif clicked == btn_folder:
                try:
                    subprocess.run(["explorer", f"/select,{os.path.normpath(pdf_path)}"])
                except Exception:
                    pass
        else:
            self.lbl_status.setText("Conversion failed")
            QMessageBox.critical(self, "Conversion Error", message)
