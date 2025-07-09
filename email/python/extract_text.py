import fitz  # PyMuPDF
import pytesseract
from PIL import Image
import io
import os
from bs4 import BeautifulSoup

# PDF text extraction (with OCR fallback)
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

# HTML text extraction
def extract_text_from_html(html_path):
    with open(html_path, "r", encoding="utf-8") as f:
        html_content = f.read()

    soup = BeautifulSoup(html_content, "html.parser")

    text = soup.get_text(separator="\n", strip=True)
    return text

# Main extraction dispatcher based on file extension
def extract_text_from_file(file_path):
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".pdf":
        return extract_text_from_pdf(file_path)
    elif ext in [".html", ".htm"]:
        return extract_text_from_html(file_path)
    else:
        print(f"Unsupported file type: {file_path}")
        return ""

def extract_from_folder(folder_path, output_folder=None):
    if output_folder is None:
        output_folder = os.path.join(folder_path, "output")
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    for filename in os.listdir(folder_path):
        if filename.lower().endswith((".pdf", ".html", ".htm")):
            file_path = os.path.join(folder_path, filename)
            print(f"Processing: {filename}")
            text = extract_text_from_file(file_path)

            base_name = os.path.splitext(filename)[0]
            output_path = os.path.join(output_folder, f"{base_name}.txt")
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(text)
            print(f"Saved to: {output_path}")

if __name__ == "__main__":
    folder_with_files = "/src/email/python/assets"  # Change this to your folder
    extract_from_folder(folder_with_files)
