import os
from typing import List, Dict, Any, Tuple
import logging
from pypdf import PdfReader
import level0.config as config


# -------------------------------------------------------------------
# Logging Setup
# -------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


# -------------------------------------------------------------------
# PDF Utilities
# -------------------------------------------------------------------
def read_pdf_with_pages(file_path: str) -> List[Tuple[int, str]]:
    """Read a PDF and return a list of (page_number, text) tuples."""
    pages: List[Tuple[int, str]] = []
    try:
        reader = PdfReader(file_path)
        for i, page in enumerate(reader.pages):
            try:
                text = page.extract_text() or ""
            except Exception as e:
                logger.warning(
                    f"Failed to extract text from page {i+1} of {file_path}: {e}"
                )
                text = ""
            if text.strip():
                pages.append((i + 1, _clean_text(text)))
        logger.info(f"Extracted {len(pages)} pages from {os.path.basename(file_path)}")
    except Exception as e:
        logger.error(f"Failed to read PDF {file_path}: {e}")
    return pages


def _clean_text(text: str) -> str:
    """Clean PDF text by removing null chars and trimming lines."""
    text = text.replace("\x00", " ")
    return "\n".join(line.strip() for line in text.splitlines())


def split_into_chunks(
    pages: List[Tuple[int, str]], chunk_size: int, chunk_overlap: int
) -> List[Dict[str, Any]]:
    """Split pages into overlapping chunks."""
    chunks: List[Dict[str, Any]] = []
    buffer: List[Tuple[int, str]] = []
    current_len = 0

    def flush_chunk():
        nonlocal buffer, current_len
        if not buffer:
            return
        page_start = buffer[0][0]
        page_end = buffer[-1][0]
        content = "\n".join(t for _, t in buffer)
        chunks.append(
            {
                "text": content,
                "page_start": page_start,
                "page_end": page_end,
            }
        )
        if chunk_overlap > 0 and len(content) > chunk_overlap:
            overlap_text = content[-chunk_overlap:]
            buffer = [(page_end, overlap_text)]
            current_len = len(overlap_text)
        else:
            buffer = []
            current_len = 0

    for page_num, text in pages:
        tokens = text
        while tokens:
            remaining = chunk_size - current_len
            if remaining <= 0:
                flush_chunk()
                continue
            take = tokens[:remaining]
            buffer.append((page_num, take))
            current_len += len(take)
            tokens = tokens[remaining:]
            if current_len >= chunk_size:
                flush_chunk()

    if current_len > 0:
        flush_chunk()

    logger.info(f"Created {len(chunks)} chunks from {len(pages)} pages")
    return chunks


def ingest_pdfs(pdf_dir: str | None = None) -> List[Dict[str, Any]]:
    """Ingest PDFs from a directory into chunks."""
    base = pdf_dir or config.PDFS_DIR
    if not os.path.isdir(base):
        logger.error(f"PDF directory not found: {base}")
        raise FileNotFoundError(f"PDF directory not found: {base}")

    pdf_files = [
        os.path.join(base, f) for f in os.listdir(base) if f.lower().endswith(".pdf")
    ]
    pdf_files.sort()
    all_chunks: List[Dict[str, Any]] = []
    logger.info(f"Found {len(pdf_files)} PDF files in {base}")

    for idx, file_path in enumerate(pdf_files, start=1):
        logger.info(
            f"({idx}/{len(pdf_files)}) Processing {os.path.basename(file_path)}"
        )
        file_pages = read_pdf_with_pages(file_path)
        chunks = split_into_chunks(file_pages, config.CHUNK_SIZE, config.CHUNK_OVERLAP)
        for ch in chunks:
            ch["source_file"] = os.path.basename(file_path)
        all_chunks.extend(chunks)
        logger.info(f"Finished {os.path.basename(file_path)}: {len(chunks)} chunks")

    logger.info(
        f"Ingestion complete: {len(all_chunks)} chunks from {len(pdf_files)} files"
    )
    return all_chunks
