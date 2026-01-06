import os
import pdfplumber
from pdf2image import convert_from_path
import pytesseract
import requests
import pandas as pd
import json
import sys
from PIL import Image, ImageEnhance, ImageFilter
import cv2
import numpy as np


# ===================== Enhanced OCR Functions =====================
def preprocess_image(image):
    """Enhanced image preprocessing for better OCR"""
    # Convert PIL to OpenCV format
    img_array = np.array(image)
    
    # Convert to grayscale
    gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
    
    # Apply denoising
    denoised = cv2.fastNlMeansDenoising(gray)
    
    # Enhance contrast using CLAHE
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    enhanced = clahe.apply(denoised)
    
    # Apply Gaussian blur to reduce noise
    blurred = cv2.GaussianBlur(enhanced, (1, 1), 0)
    
    # Threshold to get better black and white image
    _, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    # Convert back to PIL Image
    return Image.fromarray(thresh)


def extract_text_from_image_enhanced(pdf_path):
    """Enhanced OCR with preprocessing"""
    text = ""
    try:
        # Convert PDF to images with higher DPI
        images = convert_from_path(pdf_path, dpi=300)
        
        for image in images:
            # Preprocess image for better OCR
            processed_image = preprocess_image(image)
            
            # Use custom OCR config for better results
            custom_config = r'--oem 3 --psm 6 -c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz.,/-:()₹$@#%&*+=[]{}|\\;\"<>?~`!^_'
            
            # Extract text with enhanced settings
            page_text = pytesseract.image_to_string(processed_image, config=custom_config)
            text += page_text + "\n"
            
    except Exception as e:
        print(f"Error extracting text from image: {e}")
    return text


def extract_full_text(pdf_path):
    text = ""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
    except Exception as e:
        print(f"Error extracting text with pdfplumber: {e}")
    return text


def extract_text_from_pdf(pdf_path):
    """Try pdfplumber first, then enhanced OCR"""
    text = extract_full_text(pdf_path)
    if not text.strip():
        print("No text found with pdfplumber. Using enhanced OCR...")
        text = extract_text_from_image_enhanced(pdf_path)
    return text


# ===================== Groq API Processing Function =====================
def process_with_groq(text, api_key):
    """Process text using Groq API via requests"""
    
    url = "https://api.groq.com/openai/v1/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    enhanced_prompt = f"""
You are an expert invoice data extraction AI. Extract structured data from the following invoice text with high accuracy.

EXTRACT THESE FIELDS:
1. **company_name**: Issuing company name (exact text)
2. **invoice_number**: Invoice/bill number (alphanumeric)
3. **invoice_date**: Date in DD/MM/YYYY format
4. **fssai_number**: FSSAI license number (if present)
5. **items**: Array of products with:
   - **description**: Product name/description
   - **hsn_code**: HSN/SAC code (numbers only)
   - **quantity**: Numeric quantity only
   - **weight**: Weight with unit (kg/qtl/MT/gms/tons)
   - **rate**: Price per unit with currency (₹X/unit)
   - **amount**: Total amount with currency

RULES:
- Return ONLY valid JSON array format
- Use "N/A" for missing fields
- Extract exact text, don't infer
- For multiple items, create separate objects
- Ensure all numeric values are clean
- Standardize dates to DD/MM/YYYY
- Include currency symbols in amounts

INVOICE TEXT:
{text}

Return as JSON array:
"""
    
    payload = {
        "messages": [
            {
                "role": "user",
                "content": enhanced_prompt
            }
        ],
        "model": "llama-3.1-8b-instant",
        "temperature": 0.3,
        "max_tokens": 3000
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        
        if response.status_code == 200:
            result = response.json()
            content = result['choices'][0]['message']['content']
            print(f"Groq API Response: {content}")
            return content
        else:
            error_msg = f"Groq API Error {response.status_code}: {response.text}"
            print(error_msg)
            return error_msg
            
    except UnicodeEncodeError as e:
        # Handle Unicode encoding issues
        print(f"Unicode encoding error: {e}")
        # Remove problematic characters and retry
        clean_text = text.encode('ascii', 'ignore').decode('ascii')
        clean_prompt = enhanced_prompt.replace(text, clean_text).replace('₹', 'Rs.')
        
        clean_payload = {
            "messages": [
                {
                    "role": "user",
                    "content": clean_prompt
                }
            ],
            "model": "llama-3.1-8b-instant",
            "temperature": 0.3,
            "max_tokens": 3000
        }
        
        try:
            response = requests.post(url, headers=headers, json=clean_payload, timeout=60)
            if response.status_code == 200:
                result = response.json()
                content = result['choices'][0]['message']['content']
                print(f"Groq API Response (cleaned): {content}")
                return content
            else:
                return f"Groq API Error {response.status_code}: {response.text}"
        except Exception as retry_e:
            return f"Error processing with Groq API (retry): {retry_e}"
            
    except Exception as e:
        error_msg = f"Error processing with Groq API: {e}"
        print(error_msg)
        return error_msg


# ===================== Convert Weight Function =====================
def convert_weight_to_kg(weight_str):
    """Convert weight from qtl or tons to kg."""
    weight_str = weight_str.replace(",", "")  # Remove commas from the number
    weight_parts = weight_str.split()  # Split into value and unit

    try:
        weight_value = float(weight_parts[0])  # Convert the numerical part to float
    except ValueError:
        return None  # Handle unexpected formats safely

    weight_unit = (
        weight_parts[1].lower() if len(weight_parts) > 1 else "kg"
    )  # Default to kg if no unit found

    if weight_unit == "qtl":
        return weight_value * 100  # Convert qtl to kg
    elif weight_unit in ["ton", "tons"]:
        return weight_value * 1000  # Convert tons to kg
    elif weight_unit == "kg":
        return weight_value  # No conversion needed
    else:
        return weight_value  # If unit is unknown, return the value as is


# ===================== Process Multiple PDFs Function =====================
def process_multiple_pdfs(pdf_paths, api_key, output_folder, filename):
    # Ensure the output folder exists
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
        print(f"Created output folder: {output_folder}")

    all_rows = []  # Store all flattened rows from all files

    for pdf_path in pdf_paths:
        print(f"Processing PDF: {pdf_path}")

        text = extract_text_from_pdf(pdf_path)
        if not text.strip():
            print(f"No text extracted from {pdf_path}")
            continue

        result = process_with_groq(text, api_key)
        if not result or "Error" in result:
            print(f"Error processing {pdf_path} with Groq API")
            continue

        try:
            # Clean the response and extract JSON
            cleaned_result = result.strip().replace('```json', '').replace('```', '')
            
            # Find JSON array boundaries
            json_start = cleaned_result.find('[')
            json_end = cleaned_result.rfind(']') + 1
            
            if json_start != -1 and json_end != -1:
                json_str = cleaned_result[json_start:json_end]
                extracted_data = json.loads(json_str)
                
                # Process each invoice in the response
                for invoice_idx, invoice in enumerate(extracted_data):
                    print(f"Processing invoice {invoice_idx + 1}/{len(extracted_data)} from {pdf_path}")
                    
                    if 'items' in invoice and invoice['items']:
                        print(f"Found {len(invoice['items'])} items in invoice {invoice.get('invoice_number', 'N/A')}")
                        # Create a row for each item
                        for item_idx, item in enumerate(invoice['items']):
                            row = {
                                'company_name': invoice.get('company_name', 'N/A'),
                                'invoice_number': invoice.get('invoice_number', 'N/A'),
                                'invoice_date': invoice.get('invoice_date', 'N/A'),
                                'fssai_number': invoice.get('fssai_number', 'N/A'),
                                'description': item.get('description', 'N/A'),
                                'hsn_code': item.get('hsn_code', 'N/A'),
                                'quantity': item.get('quantity', 'N/A'),
                                'weight': item.get('weight', 'N/A'),
                                'rate': item.get('rate', 'N/A'),
                                'amount': item.get('amount', 'N/A')
                            }
                            all_rows.append(row)
                            print(f"  Item {item_idx + 1}: {item.get('description', 'N/A')} - Total rows now: {len(all_rows)}")
                    else:
                        print(f"No items found in invoice {invoice.get('invoice_number', 'N/A')}, adding invoice-only row")
                        # If no items, add invoice-level data only
                        row = {
                            'company_name': invoice.get('company_name', 'N/A'),
                            'invoice_number': invoice.get('invoice_number', 'N/A'),
                            'invoice_date': invoice.get('invoice_date', 'N/A'),
                            'fssai_number': invoice.get('fssai_number', 'N/A'),
                            'description': 'N/A',
                            'hsn_code': 'N/A',
                            'quantity': 'N/A',
                            'weight': 'N/A',
                            'rate': 'N/A',
                            'amount': 'N/A'
                        }
                        all_rows.append(row)
                        print(f"  Added invoice-only row - Total rows now: {len(all_rows)}")
            else:
                print(f"No valid JSON found in response for {pdf_path}")
                continue
                
        except Exception as e:
            print(f"Error parsing Groq API response for {pdf_path}: {e}")
            continue

    print(f"Total rows collected: {len(all_rows)}")
    
    if not all_rows:
        print("No data extracted from any files")
        return "No data extracted"

    # Convert to Excel with append functionality
    excel_path = convert_json_to_excel_direct(all_rows, output_folder, filename)
    return excel_path if excel_path else "Error saving Excel file"


# ===================== Convert Data to Excel =====================
def convert_json_to_excel_direct(data_rows, output_folder, filename="combined_invoice_data.xlsx"):
    excel_path = os.path.join(output_folder, filename)
    
    if not data_rows:
        print("No data to save.")
        return None

    print(f"Converting {len(data_rows)} rows to Excel")
    new_df = pd.DataFrame(data_rows)
    print(f"DataFrame created with shape: {new_df.shape}")
    
    # Convert weights
    if "weight" in new_df.columns:
        new_df["weight"] = new_df["weight"].apply(lambda x: convert_weight_to_kg(str(x)) if x != 'N/A' else x)

    # Always append to existing file or create new one
    try:
        if os.path.exists(excel_path):
            print(f"Excel file exists, reading existing data...")
            existing_df = pd.read_excel(excel_path, engine="openpyxl")
            print(f"Existing data shape: {existing_df.shape}")
            
            # Ensure columns match
            for col in new_df.columns:
                if col not in existing_df.columns:
                    existing_df[col] = 'N/A'
            for col in existing_df.columns:
                if col not in new_df.columns:
                    new_df[col] = 'N/A'
            
            # Reorder columns to match
            new_df = new_df[existing_df.columns]
            
            combined_df = pd.concat([existing_df, new_df], ignore_index=True)
            print(f"Combined data shape: {combined_df.shape}")
        else:
            print(f"Creating new Excel file")
            combined_df = new_df

        # Save to Excel
        combined_df.to_excel(excel_path, index=False, engine="openpyxl")
        print(f"Excel file saved successfully with {len(combined_df)} total rows")
        return excel_path
        
    except Exception as e:
        print(f"Error in Excel operations: {e}")
        # Fallback: save new data only
        try:
            new_df.to_excel(excel_path, index=False, engine="openpyxl")
            print(f"Fallback: Saved new data only with {len(new_df)} rows")
            return excel_path
        except Exception as e2:
            print(f"Fallback also failed: {e2}")
            return None


# ===================== Main Execution (For Electron) =====================
if len(sys.argv) < 5:
    print(
        "Usage: backend.py <pdf_path1> <pdf_path2> ... <api_key> <output_folder> <filename>"
    )
    sys.exit(1)

pdf_paths = sys.argv[1:-3]  # All PDF paths
api_key = sys.argv[-3]
output_folder = sys.argv[-2]
filename = sys.argv[-1]

output_path = process_multiple_pdfs(pdf_paths, api_key, output_folder, filename)
print(f"Processed PDFs: {output_path}")
