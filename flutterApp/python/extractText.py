import fitz  # PyMuPDF
import pytesseract
from PIL import Image
import io
import os

# Optional: Set tesseract path if needed
# pytesseract.pytesseract.tesseract_cmd = r'/usr/bin/tesseract'  # Linux
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'  # Windows

def extract_text_from_pdf(pdf_path):
    doc = fitz.open(pdf_path)
    all_text = []

    for page_number in range(len(doc)):
        page = doc[page_number]
        text = page.get_text()

        if text.strip():
            all_text.append(f"\n[Page {page_number + 1} - Extracted Text]\n{text}")
        else:
            # Render page to image and use OCR
            pix = page.get_pixmap(dpi=300)
            image = Image.open(io.BytesIO(pix.tobytes()))
            ocr_text = pytesseract.image_to_string(image)
            all_text.append(f"\n[Page {page_number + 1} - OCR Text]\n{ocr_text}")

    return "\n".join(all_text)

# Example usage
pdf_file = "sample.pdf"  # Replace with your PDF attachment path
output_text = extract_text_from_pdf(pdf_file)

# Save or print
with open("output.txt", "w", encoding="utf-8") as f:
    f.write(output_text)

print("Extraction complete. Output saved to output.txt")
