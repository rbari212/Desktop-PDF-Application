<<<<<<< HEAD
# Desktop-PDF-Application
Application to merge, split, extract pdf
=======
# PDF Merge Application

PDF Merge Application is a cross-platform desktop utility for common PDF workflows. It uses `PySide6` for the interface and embedded PDF preview, and `pypdf` for all document manipulation. Every workflow uses an explicit save step, so the application never overwrites files automatically.

## Features

- Merge multiple PDFs with drag-and-drop reordering
- Split a PDF into individual pages or range-based parts
- Rotate all pages or selected page ranges
- Extract specific pages into a new PDF
- Apply password protection to a PDF
- Optimize PDFs by removing metadata and compressing streams when possible
- Embedded PDF preview using `QPdfDocument` and `QPdfView`
- Drag-and-drop PDF loading across tabs

## Project Structure

```text
project_root/
    src/
        main.py
        ui/
            main_window.py
            merge_tab.py
            split_tab.py
            rotate_tab.py
            extract_tab.py
            password_tab.py
            compress_tab.py
        pdf_tools/
            merge.py
            split.py
            rotate.py
            extract.py
            password.py
            compress.py
        widgets/
            pdf_viewer.py
            file_list_widget.py
    requirements.txt
    README.md
```

## Prerequisites

- Python 3.10 or newer
- Windows, macOS, or Linux

## 1. Create a Virtual Environment

### Windows PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
```

## 2. Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

## 3. Run the Application

From the project root:

```bash
python src/main.py
```

## 4. Package as a Windows EXE with PyInstaller

Install PyInstaller into the same virtual environment:

```bash
pip install pyinstaller
```

Build the Windows executable from the project root:

```powershell
pyinstaller --noconfirm --clean --windowed --name "PDF Merge Application" --hidden-import PySide6.QtPdf --hidden-import PySide6.QtPdfWidgets src/main.py
```

After the build completes:

- The executable will be in `dist/PDF Merge Application/`
- The main executable file will be `dist/PDF Merge Application/PDF Merge Application.exe`

If you want a single-file executable, use:

```powershell
pyinstaller --noconfirm --clean --onefile --windowed --name "PDF Merge Application" --hidden-import PySide6.QtPdf --hidden-import PySide6.QtPdfWidgets src/main.py
```

## 5. Package as a macOS .app Bundle

Install PyInstaller if it is not already installed:

```bash
pip install pyinstaller
```

Build the `.app` bundle from the project root:

```bash
pyinstaller --noconfirm --clean --windowed --name "PDF Merge Application" --hidden-import PySide6.QtPdf --hidden-import PySide6.QtPdfWidgets src/main.py
```

After the build completes:

- The app bundle will be at `dist/PDF Merge Application.app`

If Gatekeeper warns about launching an unsigned app, sign or notarize the bundle using your Apple Developer workflow before distributing it.

## Notes
Command to start using, make sure to save in the same directory
```powershell
cd ""C:\Users\rizvi\Projects\PDF Merge Application"
py -m venv .venv
.\.venv\Scripts\Activate.ps1
py -m pip install -r requirements.txt
.\.venv\Scripts\python.exe .\src\main.py
```
- The password workflow prefers AES encryption when the optional crypto backend used by `pypdf` is available. If it is not available, the app falls back to `pypdf`'s default compatible encryption so the feature still works with the required dependency set.
- Compression is lossless for content streams. Actual file size reduction depends on the structure of the source PDF.
- Some malformed or heavily secured PDFs may preview or process differently depending on the source document.
>>>>>>> 7fd4283 (Desktop PDF Application)


