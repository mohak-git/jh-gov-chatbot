import os
import shutil
import logging
import requests
from typing import List, Union
from fpdf import FPDF
from pypdf import PdfReader

logger = logging.getLogger(__name__)


def save_uploaded_pdfs(files: List, dest_dir: str) -> List[str]:
    """
    Save uploaded file-like objects to a destination directory.
    Returns list of saved file paths.
    """
    os.makedirs(dest_dir, exist_ok=True)
    saved_paths = []

    for f in files:
        try:
            path = os.path.join(dest_dir, f.filename)
            with open(path, "wb") as buffer:
                shutil.copyfileobj(f.file, buffer)
            saved_paths.append(path)
            logger.info(f"Saved uploaded PDF -> {path}")
        except Exception as e:
            logger.error(f"Failed to save file {f.filename}: {e}")
            raise RuntimeError(f"Failed to save {f.filename}: {e}")

    return saved_paths


def post_to_level(
    url: str, endpoint: str, json: dict = None, files: list = None, timeout: int = 600
) -> dict:
    """
    Helper to POST request to a Level server.
    Supports JSON or file upload.
    """
    full_url = f"{url}{endpoint}"
    try:
        response = requests.post(full_url, json=json, files=files, timeout=timeout)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Request to {full_url} failed: {e}")
        raise RuntimeError(f"Request to {full_url} failed: {e}")


def text_to_pdf(text: Union[str, List[str]], output_path: str) -> str:
    """
    Convert plain text into a PDF file.
    Accepts string or list of strings.
    """
    try:
        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()
        pdf.set_font("Arial", size=12)

        if isinstance(text, str):
            lines = text.split("\n")
        else:
            lines = []
            for chunk in text:
                lines.extend(chunk.split("\n"))

        for line in lines:
            safe_line = line.encode("latin-1", "replace").decode(
                "latin-1"
            )  # FPDF limitation
            pdf.multi_cell(0, 8, safe_line)

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        pdf.output(output_path)
        logger.info(f"Saved summary PDF -> {output_path}")
        return output_path
    except Exception as e:
        logger.error(f"Failed to create PDF {output_path}: {e}")
        raise RuntimeError(f"PDF generation failed: {e}")


def pdf_to_text(pdf_path: str) -> str:
    """
    Extracts text from a PDF file using PyPDF.
    """
    text_chunks = []
    try:
        reader = PdfReader(pdf_path)
        for page in reader.pages:
            text = page.extract_text()
            if text:
                text_chunks.append(text.strip())
        logger.info(f"Extracted text from {pdf_path}, {len(text_chunks)} pages")
    except Exception as e:
        logger.error(f"Failed to parse {pdf_path}: {e}")
        raise RuntimeError(f"Failed to parse {pdf_path}: {e}")

    return "\n".join(text_chunks).strip()
