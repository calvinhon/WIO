import fitz  # PyMuPDF
from PIL import Image
import pytesseract
import io
import subprocess
import json
import sys
import logging
import re
from pathlib import Path
from bs4 import BeautifulSoup
from typing import List, Optional, Union
import signal
import time

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TextExtractor:
    def __init__(self, key_info_path: str = "assets/clients/hoach.json", 
                 pwd_rules_path: str = "assets/email/email.txt",
                 pwd_gen_script: str = "ollama_gen_pwds.py"):
        self.key_info_path = key_info_path
        self.pwd_rules_path = pwd_rules_path
        self.pwd_gen_script = pwd_gen_script
        
    def generate_passwords(self) -> List[str]:
        """Generate passwords using ollama_gen_pwds.py script."""
        try:
            logger.info("Generating passwords using Ollama...")
            
            result = subprocess.run(
                ["python3", self.pwd_gen_script, self.key_info_path, self.pwd_rules_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=300,
                text=True
            )
            
            if result.returncode != 0:
                logger.error(f"Password generation failed: {result.stderr}")
                return []
            
            # Parse the output - it should be a JSON array of strings
            output = result.stdout.strip()
            
            # Try to extract JSON from the output (in case there's extra text)
            try:
                # Look for JSON array in the output
                json_match = re.search(r'\[.*\]', output, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                    passwords = json.loads(json_str)
                else:
                    # Try to parse the entire output as JSON
                    passwords = json.loads(output)
                
                # Filter out empty/invalid passwords
                filtered_passwords = [pwd for pwd in passwords if pwd and pwd.strip() and pwd != "N/A"]
                logger.info(f"Generated {len(filtered_passwords)} valid passwords")
                return filtered_passwords
                
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON from password generation output: {e}")
                return []
                
        except subprocess.TimeoutExpired:
            logger.error("Password generation timed out")
            return []
        except Exception as e:
            logger.error(f"Password generation error: {e}")
            return []

    def try_open_pdf(self, pdf_path: str, passwords: List[str]) -> Optional[fitz.Document]:
        """Try to open encrypted PDF with generated passwords."""
        
        for i, pwd in enumerate(passwords):
            if pwd is None:
                continue
            try:
                doc = fitz.open(pdf_path)
                if doc.needs_pass:
                    logger.info(f"Trying password {i+1}/{len(passwords)}: '{pwd}'")
                    auth_result = doc.authenticate(pwd)
                    if auth_result:
                        logger.info(f"PDF decrypted successfully with password: '{pwd}'")
                        # Verify the document is actually unlocked by checking if we can access pages
                        try:
                            # Try to access the first page to verify unlock
                            if len(doc) > 0:
                                test_page = doc[0]
                                # Try to get text from the page to verify access
                                test_text = test_page.get_text()
                                logger.info(f"Document verified as unlocked - found {len(test_text)} characters on first page")
                                return doc
                            else:
                                logger.warning("Document has no pages")
                                doc.close()
                        except Exception as e:
                            logger.error(f"Failed to verify document unlock: {e}")
                            doc.close()
                    else:
                        logger.debug(f"Authentication failed for password: '{pwd}'")
                        doc.close()
                else:
                    logger.info("PDF opened without password")
                    return doc
            except Exception as e:
                logger.debug(f"Error trying password '{pwd}': {e}")
                if 'doc' in locals():
                    doc.close()
                continue
        
        logger.error("Failed to unlock PDF with any password")
        return None

    class TimeoutException(Exception):
        pass

    def timeout_handler(self, signum, frame):
        raise self.TimeoutException()

    def safe_ocr(self, image: Image.Image, timeout_sec: int = 10) -> str:
        """Perform OCR with timeout protection."""
        if sys.platform == "win32":
            # Windows doesn't support signal.alarm, use alternative approach
            return self._safe_ocr_windows(image, timeout_sec)
        
        signal.signal(signal.SIGALRM, self.timeout_handler)
        signal.alarm(timeout_sec)
        try:
            return pytesseract.image_to_string(image)
        except self.TimeoutException:
            logger.warning("OCR timed out")
            return ""
        except Exception as e:
            logger.error(f"OCR error: {e}")
            return ""
        finally:
            signal.alarm(0)

    def _safe_ocr_windows(self, image: Image.Image, timeout_sec: int) -> str:
        """OCR for Windows without signal.alarm."""
        try:
            return pytesseract.image_to_string(image)
        except Exception as e:
            logger.error(f"OCR error: {e}")
            return ""

    def extract_text_with_ocr(self, doc: fitz.Document) -> str:
        """Extract text from PDF using both direct extraction and OCR."""
        if doc.is_closed:
            logger.error("Document is closed, cannot extract text")
            return ""
        
        # Remove this check as it's causing the issue
        # The document might report needs_pass even after successful authentication
        # if doc.needs_pass:
        #     logger.error("Document still requires password, authentication may have failed")
        #     return ""
        
        all_text = []
        logger.info(f"Processing {len(doc)} pages...")
        
        for page_number in range(len(doc)):
            try:
                page = doc[page_number]
                text = page.get_text()
                
                # Only do OCR if direct text extraction yields little content
                ocr_text = ""
                if len(text.strip()) < 100:  # Threshold for triggering OCR
                    logger.debug(f"Running OCR on page {page_number + 1} (little text found)")
                    try:
                        pix = page.get_pixmap(dpi=300)
                        image = Image.open(io.BytesIO(pix.tobytes()))
                        ocr_text = self.safe_ocr(image)
                    except Exception as e:
                        logger.error(f"OCR failed for page {page_number + 1}: {e}")
                else:
                    logger.debug(f"Page {page_number + 1}: {len(text.strip())} characters extracted directly")

                combined = ""
                if text.strip():
                    combined += f"\n[Page {page_number + 1} - Extracted Text]\n{text.strip()}"
                if ocr_text.strip():
                    combined += f"\n[Page {page_number + 1} - OCR Text]\n{ocr_text.strip()}"
                
                all_text.append(combined)
                
            except Exception as e:
                logger.error(f"Error processing page {page_number + 1}: {e}")
                continue
        
        result = "\n".join(all_text)
        logger.info(f"Extracted {len(result)} total characters from PDF")
        return result

    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """Extract text from PDF file."""
        doc = None
        
        # First, try to determine if the PDF is encrypted
        try:
            test_doc = fitz.open(pdf_path)
            needs_password = test_doc.needs_pass
            test_doc.close()
        except Exception as e:
            logger.error(f"Failed to open PDF for initial check: {e}")
            return ""
        
        if needs_password:
            logger.info(f"PDF is encrypted, attempting to unlock: {pdf_path}")
            
            # Check if password generation files exist
            if not Path(self.key_info_path).exists():
                logger.error(f"Key info file not found: {self.key_info_path}")
                return ""
            if not Path(self.pwd_rules_path).exists():
                logger.error(f"Password rules file not found: {self.pwd_rules_path}")
                return ""
            if not Path(self.pwd_gen_script).exists():
                logger.error(f"Password generation script not found: {self.pwd_gen_script}")
                return ""
            
            # Generate passwords and try to unlock
            passwords = self.generate_passwords()
            if not passwords:
                logger.error("No passwords generated")
                return ""
            
            doc = self.try_open_pdf(pdf_path, passwords)
            if not doc:
                logger.error("Could not unlock the encrypted PDF")
                return ""
            
            # Extract text from the unlocked document
            try:
                text = self.extract_text_with_ocr(doc)
                return text
            finally:
                doc.close()
        else:
            # PDF is not encrypted, open normally
            try:
                doc = fitz.open(pdf_path)
                logger.info("PDF opened successfully (not encrypted)")
            except Exception as e:
                logger.error(f"Failed to open PDF: {e}")
                return ""
        
        # Extract text from the opened document
        try:
            return self.extract_text_with_ocr(doc)
        finally:
            if doc:
                doc.close()

    def extract_text_from_html(self, html_path: str) -> str:
        """Extract text from HTML file."""
        try:
            with open(html_path, "r", encoding="utf-8", errors="ignore") as f:
                html_content = f.read()
            soup = BeautifulSoup(html_content, "html.parser")
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            
            # Get visible text only
            text = soup.get_text(separator="\n", strip=True)
            return text
        except Exception as e:
            logger.error(f"Error processing HTML file {html_path}: {e}")
            return ""

    def extract_from_folder(self, folder_path: str, output_dir: str = "assets/output") -> None:
        """Extract text from all supported files in a folder."""
        folder_path = Path(folder_path)
        output_dir = Path(output_dir)
        
        if not folder_path.exists():
            logger.error(f"Input folder does not exist: {folder_path}")
            return
            
        output_dir.mkdir(parents=True, exist_ok=True)
        
        supported_extensions = {".pdf", ".html", ".htm"}
        files_processed = 0
        
        for file_path in folder_path.iterdir():
            if not file_path.is_file():
                continue
                
            if file_path.suffix.lower() not in supported_extensions:
                continue
                
            logger.info(f"Processing: {file_path}")
            
            try:
                if file_path.suffix.lower() == ".pdf":
                    text = self.extract_text_from_pdf(str(file_path))
                elif file_path.suffix.lower() in [".html", ".htm"]:
                    text = self.extract_text_from_html(str(file_path))
                else:
                    continue
                
                if text.strip():
                    output_path = output_dir / (file_path.stem + ".txt")
                    with open(output_path, "w", encoding="utf-8") as f:
                        f.write(text)
                    logger.info(f"Saved extracted text to {output_path}")
                    files_processed += 1
                else:
                    logger.warning(f"No text extracted from {file_path}")
                    
            except Exception as e:
                logger.error(f"Error processing {file_path}: {e}")
                continue
        
        logger.info(f"Processing complete. {files_processed} files processed successfully.")

def main():
    if len(sys.argv) != 2:
        print("Usage: python3 extract_text.py <folder_with_files>")
        sys.exit(1)
    
    folder_path = sys.argv[1]
    extractor = TextExtractor()
    extractor.extract_from_folder(folder_path)

if __name__ == "__main__":
    main()