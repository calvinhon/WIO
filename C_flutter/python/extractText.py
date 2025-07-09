import fitz  # PyMuPDF
import pytesseract
from PIL import Image
import io
import os

# Optional: set tesseract path manually
# pytesseract.pytesseract.tesseract_cmd = r'/usr/bin/tesseract'  # Linux
# pytesseract.pytesseract.tesseract_cmd = r'C:\\Program Files\\Tesseract-OCR\\tesseract.exe'  # Windows

def extract_text_from_pdf(pdf_path):
    doc = fitz.open(pdf_path)
    all_text = []

    for page_number in range(len(doc)):
        page = doc[page_number]

        # 1. Extract regular text
        text = page.get_text()

        # 2. Also do OCR (always, just in case)
        pix = page.get_pixmap(dpi=300)
        image = Image.open(io.BytesIO(pix.tobytes()))
        ocr_text = pytesseract.image_to_string(image)

        # 3. Combine both results
        combined = ""
        if text.strip():
            combined += f"\n[Page {page_number + 1} - Extracted Text]\n{text.strip()}"
        if ocr_text.strip():
            combined += f"\n[Page {page_number + 1} - OCR Text]\n{ocr_text.strip()}"

        all_text.append(combined)

    return "\n".join(all_text)


def extract_from_folder(folder_path, output_folder=None):
    if output_folder is None:
        output_folder = os.path.join(folder_path, "output")
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    for filename in os.listdir(folder_path):
        if filename.lower().endswith(".pdf"):
            pdf_path = os.path.join(folder_path, filename)
            print(f"Processing: {filename}")
            text = extract_text_from_pdf(pdf_path)

            base_name = os.path.splitext(filename)[0]
            output_path = os.path.join(output_folder, f"{base_name}.txt")
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(text)
            print(f"Saved to: {output_path}")


# Example usage
if __name__ == "__main__":
    folder_with_pdfs = "/src/flutter_app_new/python/assets"  # Change to your actual folder
    extract_from_folder(folder_with_pdfs)
