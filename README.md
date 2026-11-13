# 📄 Image to PDF Studio

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![GUI: PyQt5](https://img.shields.io/badge/GUI-PyQt5-green.svg)](https://pypi.org/project/PyQt5/)
[![Platform: Windows](https://img.shields.io/badge/Platform-Windows-0078D6.svg)](https://www.microsoft.com/windows)

A modern, fast, and intuitive desktop application built in Python and PyQt5 to convert, reorder, and optimize image documents into high-quality PDFs.

Available both as a standalone Windows executable (`.exe`) and as an open-source Python application.

---

## ✨ Features

- **Intuitive Visual Reordering:**
  - **Drag-and-Drop:** Directly drag page cards up or down to reorder pages in real-time.
  - **Dual View Modes:** Switch between **⊞ Grid Cards View** (gallery layout) and **☰ Detailed List View**.
  - **Reorder Controls:** Dedicated `⏫ Top`, `⬆️ Up`, `⬇️ Down`, `⏬ Bottom`, and sort menu (A–Z, Z–A, Size, Reverse).
- **🌙 Dark & ☀️ Light Mode:**
  - Built-in theme engine with a modern palette for comfortable day or night editing.
- **Interactive Page Inspector (Previewer):**
  - Full-featured modal preview with Zoom In/Out, Fit Window, Actual 1:1 Size.
  - Page navigation (**◀ Previous** and **Next ▶**).
  - In-place 90° clockwise rotation.
- **Page Geometry & Sizing:**
  - Preserves original image dimensions (1:1 ratio, 0% crop/loss).
  - Standard paper formats: A4, US Letter, US Legal, A3, and A5.
  - Orientation: Auto (adapts per image aspect ratio), Portrait, or Landscape.
  - Margins: None (Full Bleed), Small (2%), Normal (5%), Wide (10%).
- **Compression & Quality Controls:**
  - Interactive JPEG quality slider (20% – 100%).
  - Color mode: Full Color (RGB) or Grayscale (Black & White).
- **Asynchronous Processing:**
  - Non-blocking conversion with an active progress bar and live page status.
  - Auto-open PDF or reveal in Windows Explorer upon completion.
- **Privacy & Security:**
  - **100% Offline & Local**: Your images never leave your computer.

---

## 📁 Supported Formats

Supports all standard image formats:
- **PNG** (`.png`)
- **JPEG / JPG / JFIF** (`.jpg`, `.jpeg`, `.jfif`)
- **WEBP** (`.webp`)
- **BMP** (`.bmp`)
- **TIFF** (`.tiff`, `.tif`)
- **GIF** (`.gif`)
- **ICO** (`.ico`)

*(Transparent images in PNG/WEBP/GIF are automatically composited onto a clean white background).*

---

## 🚀 Quick Start

### 1. Download Pre-built Windows Executable
You can download the standalone `.exe` directly from the [GitHub Releases](https://github.com/m4cherif/image-to-pdf-converter/releases) page. No Python installation required!

### 2. Run from Source Code

Clone the repository and install dependencies:

```bash
# Clone the repository
git clone https://github.com/m4cherif/image-to-pdf-converter.git
cd image-to-pdf-converter

# Install dependencies
pip install -r requirements.txt

# Run the application
python main.py
```

### 3. Run Unit Tests

```bash
python test_converter.py
```

### 4. Build Windows Executable Locally

```bash
python build_exe.py
```

---

## 📂 Project Architecture

```
image-to-pdf-converter/
├── .github/
│   └── workflows/
│       └── build.yml          # GitHub Actions CI build & release workflow
├── converter.py               # Core image processing & PDF layout engine
├── gui.py                     # PyQt5 graphical user interface & theme engine
├── main.py                    # Application entry point with High-DPI support
├── build_exe.py               # PyInstaller automated packaging script
├── test_converter.py          # Unit tests suite
├── requirements.txt           # Python package dependencies
├── icon.ico                   # Multi-resolution application icon
├── LICENSE                    # MIT License
└── README.md                  # Project documentation
```

---

## 📜 License

This project is licensed under the [MIT License](LICENSE) - feel free to use, modify, and distribute it freely.
