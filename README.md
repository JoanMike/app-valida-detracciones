# SUNAT Detractions Validator

![License](https://img.shields.io/badge/license-PolyForm%20NC%201.0.0-blue)
![Python](https://img.shields.io/badge/python-3.10%2B-blue?logo=python&logoColor=white)
![Platform](https://img.shields.io/badge/platform-Windows-0078D6?logo=windows&logoColor=white)

> Desktop application that validates SUNAT-issued detraction deposit certificate PDFs against their file names.

## Overview

This tool automatically checks that the file names of detraction PDFs match the information contained inside each document:

1. **Supplier name**: validates that the supplier name in the file name matches the "Nombre/Razón Social del Proveedor" field in the PDF.
2. **Voucher number**: validates that the voucher number in the file name matches the "Número de Comprobante" field in the PDF.

<div align="center">
	<img width="678" height="476" alt="detracciones_validator" src="https://github.com/user-attachments/assets/d7ca0a75-853f-491c-9aa5-77a14d173791" />
</div>

## Features

- Intuitive graphical interface.
- Batch processing of multiple PDF files in the background (the UI never freezes).
- Real-time progress bar.
- Visual results with colors (green = OK, red = error).
- Flexible name comparison (ignores accents, punctuation, and company suffixes).
- Right-click context menu to open the file or its location.
- Double-click or Enter key to open the PDF directly.
- Customizable special equivalences (`equivalencias.json`).
- Event and error logging in `validador.log`.

## Tech Stack

- **Python 3.10+** with [pdfplumber](https://github.com/jsvine/pdfplumber) for PDF text extraction and `tkinter` for the GUI (bundled with Python).
- Tests with [pytest](https://docs.pytest.org/) (development only).

## Requirements

- Python 3.10 or higher.
- Windows 10/11.

## Installation

1. Clone or download the repository:

```bash
git clone https://github.com/JoanMike/appValidaDetracciones.git
cd appValidaDetracciones
```

2. Create a virtual environment (recommended):

```bash
python -m venv venv
venv\Scripts\activate
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

## Configuration

For cases where automatic validation is not possible (heavily abbreviated names), special equivalences can be added to the `equivalencias.json` file (next to the script), without touching the code:

```json
{
    "CONSULT. INTEG. DE MKT Y COMUNIC. NOVACOM": "CONSULTORA INTEGRAL DE MARKETING Y"
}
```

- **Key**: name in the file name (normalized to uppercase).
- **Value**: text that must appear in the PDF to consider the file valid.

If the file does not exist or is invalid, the application works normally without equivalences (this is logged in `validador.log`).

## Usage

1. Run the application:

```bash
python validar_detracciones.py
```

2. Click **"Seleccionar Carpeta"** and choose the folder containing the detraction PDFs.

3. Click **"Validar Archivos"** to start the validation.

4. Review the results:
   - **Green**: the file passed validation.
   - **Red**: the file has mismatches.
   - In the validation columns: **✓** valid, **✗** mismatch, **—** the data could not be extracted from the PDF.

5. Additional options:
   - **Double-click or Enter**: opens the PDF with the default program.
   - **Right-click → Abrir archivo**: opens the PDF.
   - **Right-click → Abrir ubicación**: opens File Explorer at the file's location.

### Expected file name format

PDF files must follow this format:

```text
{RUC}_{NOMBRE_PROVEEDOR} {NUMERO_COMPROBANTE} DETRACCION.pdf
```

**Example:**

```text
1900259454_OMNI LOGISTICS (PERU) E001-00009926 DETRACCION.pdf
```

Where:

- `1900259454` = reference number / RUC
- `OMNI LOGISTICS (PERU)` = supplier name
- `E001-00009926` = voucher number
- `DETRACCION` = identifier suffix

### Flexible validations

The application performs smart comparisons:

| Name in file | Name in PDF | Result |
|--------------|-------------|--------|
| KUEHNE NAGEL | KUEHNE + NAGEL S.A. | ✓ Valid |
| ESTUDIO MUNIZ | ESTUDIO MUÑIZ S.R.L. | ✓ Valid |
| MERCADO PAGO PERU | MERCADOPAGO PERU S.R.L. | ✓ Valid |
| TIENDAS POR DPTO RIPLEY | TIENDAS POR DEPARTAMENTO RIPLEY S.A. | ✓ Valid |

When comparison is by significant words, the majority (≥60%) of the long words in the file name must appear in the PDF. A single generic word in common (e.g. "SERVICIOS") is no longer enough to consider a file valid.

### Running the tests

The validation logic (normalization and comparison of names and vouchers) has unit tests with pytest:

```bash
pip install -r requirements-dev.txt
python -m pytest tests/
```

## Project Structure

```text
appValidaDetracciones/
├── validar_detracciones.py    # Main application
├── equivalencias.json         # Special name equivalences (editable)
├── requirements.txt           # Production dependencies
├── requirements-dev.txt       # Development dependencies (tests)
├── tests/                     # Unit tests
├── README.md                  # This file
├── LICENSE                    # Terms of use
├── .gitignore                 # Files ignored by Git
├── validador.log              # Event log (generated, not versioned)
└── venv/                      # Virtual environment (not included in Git)
```

## License

Distributed under the **PolyForm Noncommercial License 1.0.0** — free for
noncommercial use only. See [LICENSE](LICENSE) for the full license text.

Copyright (c) 2026 Jose Miguel Maldonado Garcia

## Author

**Jose Miguel Maldonado Garcia** — [@JoanMike](https://github.com/JoanMike)
