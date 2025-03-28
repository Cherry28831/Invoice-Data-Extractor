import os
import pdfplumber
from pdf2image import convert_from_path
import pytesseract
import google.generativeai as genai
import pandas as pd
import json
import sys


# ===================== PDF Text Extraction Functions =====================
def extract_text_from_image(pdf_path):
    text = ""
    try:
        images = convert_from_path(pdf_path)
        for image in images:
            text += pytesseract.image_to_string(image) + "\n"
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
    text = extract_full_text(pdf_path)
    if not text.strip():
        print("No text found with pdfplumber. Switching to OCR...")
        text = extract_text_from_image(pdf_path)
    return text


# ===================== Gemini API Processing Function =====================
def process_with_gemini(text, api_key):
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-1.5-flash")

    prompt = f"""
    You are an expert in extracting structured data from invoices, even when the text is messy or unstructured. Extract the following details from the text below:

    1. **Goods Description**: The name or description of the product. Extract the exact wording used in the text.
    2. **HSN/SAC Code**: The HSN or SAC code for the product. Extract the numerical code as mentioned.
    3. **Quantity**: The quantity of the product. Extract only the numerical value. If the quantity is unclear or contains inconsistencies (e.g., spaces or mixed formats), extract the first numerical value as the quantity and ignore the rest.
    4. **Weight**: The weight of the product, including the unit (kg, qtl, tons). Retain the unit as mentioned in the invoice. If no weight is mentioned, set it to "N/A".
    5. **Rate**: The rate per single unit(e.g., per bag, per pack, or per unit). Ensure it is a monetary value (e.g., ₹, $, etc.), not a weight or quantity. Do not extract the total amount for the quantity. This is the cost for one unit of the item.
    6. **Amount**: The total amount for the product. This is the total cost for all units of the item. Ensure it is a monetary value. Do not extract the final/total amount of the entire invoice.
    7. **Company Name**: The name of the company issuing the invoice. Extract the exact name as mentioned.
    8. **Invoice Number**: The invoice number. Extract the exact alphanumeric code.
    9. **FSSAI Number**: The FSSAI number (if applicable). Extract the exact number. If two FSSAI numbers are present, take only the buyer's FSSAI number.
    10. **Date of Invoice**: The date of the invoice in DD/MM/YYYY format. Extract the date exactly as mentioned.

    **Rules**:
    - If a field is missing or unclear, set it to "N/A". Do not infer or guess values.
    - Retain the exact wording, units, and formatting as mentioned in the text.
    - If multiple products are listed, extract the details for each product separately.
    - If the text contains irrelevant information or noise, ignore it and focus only on the relevant details.
    - Ensure that the extracted data is accurate and matches the text exactly.

    **Text**:
    {text}

    Return the result as a list of JSON objects, one for each product in the invoice.
    """
    try:
        response = model.generate_content(prompt)
        print(f"API Response: {response.text}")  # Debug log
        return response.text
    except Exception as e:
        print(f"Error processing with API: {e}")  # Debug log
        return f"Error processing with API: {e}"


# ===================== Convert Weight Function =====================
def convert_weight_to_kg(weight_str):
    """
    Convert weight from qtl or tons to kg.
    - If the unit is 'qtl' (or any variation like 'Qtl', 'QTL'), multiply the weight by 100 to convert to kg.
    - If the unit is 'ton' (or any variation like 'TON', 'tons'), multiply the weight by 1000 to convert to kg.
    - If the unit is 'kg' (or any variation like 'KG', 'Kg'), no conversion is needed.
    """
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
        print(f"Created output folder: {output_folder}")  # Debug log

    combined_data = []

    for pdf_path in pdf_paths:
        print(f"Processing PDF: {pdf_path}")  # Debug log

        text = extract_text_from_pdf(pdf_path)
        if not text.strip():
            print(f"No text extracted from {pdf_path}")
            continue

        result = process_with_gemini(text, api_key)
        if not result or "Error" in result:
            print(f"Error processing {pdf_path} with LLM")
            continue

        try:
            # Clean the response (remove markdown formatting)
            cleaned_result = result.strip().strip("```json").strip("```")
            extracted_data = json.loads(cleaned_result)
            combined_data.extend(extracted_data)  # Add data to the combined list
        except Exception as e:
            print(f"Error parsing LLM response for {pdf_path}: {e}")
            continue

    # Save combined data to a single JSON file
    output_file = os.path.join(output_folder, "combined_data.json")
    print(f"Saving combined JSON file to: {output_file}")  # Debug log

    try:
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(combined_data, f, indent=4)
        print(f"Combined JSON file saved successfully.")  # Debug log
    except Exception as e:
        print(f"Error saving combined JSON file: {e}")
        return "Error saving combined JSON file"

    # Convert combined JSON to Excel
    excel_path = convert_json_to_excel(output_folder, filename)
    return excel_path if excel_path else "Error saving Excel file"


# ===================== Convert JSON to Excel =====================
def convert_json_to_excel(output_folder, filename="combined_invoice_data.xlsx"):
    json_file = os.path.join(output_folder, "combined_data.json")
    print(f"Loading JSON file: {json_file}")  # Debug log

    try:
        with open(json_file, "r", encoding="utf-8") as file:
            file_content = file.read().strip().strip("```json").strip("```")
            print(f"File content: {file_content}")  # Debug log

            json_data = json.loads(file_content)
    except Exception as e:
        print(f"Error processing JSON file: {e}")
        return None

    if json_data:
        print(f"Combined data: {json_data}")  # Debug log
        df = pd.DataFrame(json_data)

        # Convert weights in the 'Weight' column
        if "Weight" in df.columns:
            df["Weight"] = df["Weight"].apply(convert_weight_to_kg)

        # Save the data as Excel
        excel_path = os.path.join(output_folder, filename)
        try:
            df.to_excel(excel_path, index=False, engine="openpyxl")
            print(f"Excel file saved at {excel_path}")
        except Exception as e:
            print(f"Error saving Excel file: {e}")
            return None

        # Delete JSON files after successful Excel creation
        try:
            for file in os.listdir(output_folder):
                if file.endswith(".json"):
                    os.remove(os.path.join(output_folder, file))
                    print(f"Deleted JSON file: {file}")
        except Exception as e:
            print(f"Error deleting JSON files: {e}")

        return excel_path
    else:
        print("No data to save.")
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
