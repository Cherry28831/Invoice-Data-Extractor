# 🧾 Invoice Data Extractor (v2.0.0)

![GitHub release (latest by date)](https://img.shields.io/github/v/release/Cherry28831/Invoice-Data-Extractor)
![MIT License](https://img.shields.io/github/license/Cherry28831/Invoice-Data-Extractor)
![Platform](https://img.shields.io/badge/platform-Windows-blue)
![AI Engine](https://img.shields.io/badge/LLM-Groq%20%7C%20LLaMA%203.1-green)

A **desktop-based AI invoice processing engine** that extracts structured, item-level invoice data from **PDF and JPG invoices** using a **hybrid OCR + LLM pipeline**, and exports it directly to **Excel**.

✔ Tested on **1000+ real-world invoices**
✔ Achieved **~91% field-level accuracy**
✔ Packaged as a **single plug-and-play `.exe`**

---

## 🎯 Problem This Solves

Invoice data extraction is messy because:

* PDFs vary wildly in layout
* Many PDFs are scanned images
* Tables break traditional parsers
* OCR alone is not enough
* Rule-based systems don’t scale

This tool solves that by combining:

* **Deterministic OCR & preprocessing**
* **LLM-based semantic understanding**
* **Structured output enforcement**
* **Excel-ready data flattening**

---

## ✨ What’s New in v2.0.0

This release is a **major backend upgrade**.

### 🔥 Major Improvements

* **Groq API integration**

  * Replaced Gemini with **Groq (LLaMA-3.1-8B-Instant)**
  * Faster inference, lower latency, better consistency

* **Advanced OCR Pipeline**

  * OpenCV preprocessing (denoise, CLAHE, thresholding)
  * High-DPI PDF to image conversion
  * Custom Tesseract OCR configuration

* **Robust PDF Handling**

  * `pdfplumber` text extraction first
  * Automatic OCR fallback if text is missing

* **Flattened Excel Output**

  * Each invoice item becomes **one row**
  * Invoice-level fields repeated per item
  * Suitable for accounting & analytics

* **Append to Existing Excel**

  * New invoices can be appended to existing files
  * No overwriting, no manual merges

---

## 🧠 System Architecture

```
PDF / JPG
   │
   ├─► pdfplumber (text PDFs)
   │
   └─► OpenCV + Tesseract (scanned PDFs / images)
            │
            ▼
     Cleaned invoice text
            │
            ▼
     Groq LLM (LLaMA-3.1-8B)
            │
            ▼
     Structured JSON (validated)
            │
            ▼
     Flattened rows
            │
            ▼
     Excel (.xlsx)
```

---

## 🧠 How the Extraction Works (Step-by-Step)

### 1️⃣ PDF / Image Ingestion

* PDFs are first parsed using `pdfplumber`
* If no usable text is found → OCR pipeline is triggered
* JPG files always go through OCR

### 2️⃣ OCR Enhancement (Key to Accuracy)

Each page/image undergoes:

* Grayscale conversion
* Noise removal
* CLAHE contrast enhancement
* Adaptive thresholding
* Custom Tesseract config for invoice symbols & numbers

This significantly improves OCR quality on:

* Scanned invoices
* Low-contrast documents
* Poorly printed bills

---

### 3️⃣ LLM-Based Data Extraction (Groq)

Extracted text is sent to Groq with a **strict, structured prompt** that enforces:

* Exact text extraction (no hallucination)
* Fixed fields:

  * Company name
  * Invoice number
  * Invoice date
  * FSSAI number
  * Item-level details
* JSON-only response
* Clean numeric values
* Standardized date format

**Model used:**
`llama-3.1-8b-instant`

---

### 4️⃣ Response Cleaning & Validation

* Markdown fences removed
* JSON boundaries detected manually
* Invalid responses discarded
* Safe fallback handling for malformed outputs

---

### 5️⃣ Data Flattening Logic

* Each invoice item becomes **one Excel row**
* Invoice-level fields are repeated per item
* If no items are found → invoice-level row is still created

This makes the output:

* Pivot-friendly
* BI-ready
* Accounting-friendly

---

### 6️⃣ Excel Export (Append-Safe)

* If Excel file exists → data is appended
* Column mismatches are auto-handled
* Weights are converted to **kilograms**
* File is saved using `openpyxl`

---

## 📊 Accuracy & Testing

* ✅ Tested on **1000+ real invoices**
* 📈 Achieved **~91% accuracy**
* Includes:

  * Printed PDFs
  * Scanned PDFs
  * Multi-item invoices
  * Inconsistent layouts

Accuracy measured on:

* Invoice number
* Date
* Item description
* Quantity
* Amount
* HSN codes (when present)

---

## 🧪 Supported Input Formats

| Format        | Method       |
| ------------- | ------------ |
| PDF (text)    | pdfplumber   |
| PDF (scanned) | OCR fallback |
| JPG           | OCR          |

---

## 📤 Output

### Excel File (`.xlsx`)

Each row represents **one invoice item**.

Columns include:

* company_name
* invoice_number
* invoice_date
* fssai_number
* description
* hsn_code
* quantity
* weight (kg)
* rate
* amount

---

## 🚀 Getting Started

### 🔽 Download Executable

👉 **[Download v2.0.0](https://github.com/Cherry28831/Invoice-Data-Extractor/releases/tag/v2.0.0)**

No Python.
No setup.
Just run.

---

### 🔑 Groq API Key (Required)

1. Create a Groq account
2. Generate an API key
3. Paste it when prompted by the app

---

## 🛠 Usage Flow

1. Launch the `.exe`
2. Enter Groq API key
3. Select one or multiple PDF/JPG invoices
4. Choose output Excel file (new or existing)
5. Extraction starts automatically
6. Excel file is generated/appended

---

## 🧪 Build From Source

```bash
git clone https://github.com/Cherry28831/Invoice-Data-Extractor.git
cd Invoice-Data-Extractor
pip install -r requirements.txt
cd backend
pyinstaller invoice-backend.spec
cd ..
npm start 
npm run dist
```

---

## 🌱 Future Roadmap

* Vendor auto-classification
* GST / tax breakup extraction
* CSV & ERP exports
* Multi-language invoices
* Cloud + desktop hybrid mode

---

## 🤝 Contributions

This project is actively evolving.
Contributions, optimizations, and feedback are welcome.
