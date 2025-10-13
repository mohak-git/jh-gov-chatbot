from langchain.tools import BaseTool
from orchestrator.utils import pdf_to_text, post_to_level, text_to_pdf
import orchestrator.config as config
import logging
from orchestrator.rag import GeminiClient, Summarizer
import os

logger = logging.getLogger(__name__)


class MultiLevelIngestTool(BaseTool):
    name: str = "MultiLevelIngest"
    description: str

    def _run(self, pdf_paths: list):
        llm = GeminiClient(config.GEMINI_MODEL, config.GOOGLE_API_KEY)
        summarizer = Summarizer(llm)

        # --- Step 1: Level2 ingest ---
        files = [
            ("files", (os.path.basename(p), open(p, "rb"), "application/pdf"))
            for p in pdf_paths
        ]
        logger.info("Ingesting PDFs into Level2...")
        resp_l2 = post_to_level(config.LEVEL2_URL, "/ingest", files=files)
        for _, (filename, file_obj, mime) in files:
            file_obj.close()

        # --- Step 2: Summarize each PDF individually (Level2 → Level1) ---
        summary_l1_pdfs = []
        for pdf_path in pdf_paths:
            logger.info(f"Processing PDF for Level1 summary: {pdf_path}")

            # Extract text
            extracted_text = pdf_to_text(pdf_path)
            level2_char_count = len(extracted_text)
            target_level1_chars = int(level2_char_count * config.LEVEL2_TO_1_RATIO)
            logger.info(
                f"Summarizing Level2 content into Level1 for {os.path.basename(pdf_path)} "
                f"({target_level1_chars} chars target)..."
            )

            # Summarize to Level1
            summary_l1_text = summarizer.compress(
                extracted_text, target_level1_chars, "level2", "level1"
            )

            # Save Level1 summary PDF
            summary_l1_pdf = os.path.join(
                config.PDFS_DIR, f"summary_l2_to_l1_{os.path.basename(pdf_path)}.pdf"
            )
            text_to_pdf(summary_l1_text, summary_l1_pdf)
            summary_l1_pdfs.append((summary_l1_pdf, summary_l1_text))

        # --- Step 3: Ingest all Level1 summaries ---
        files = [
            (
                "files",
                (os.path.basename(p), open(p, "rb"), "application/pdf"),
            )
            for p, _ in summary_l1_pdfs
        ]
        logger.info("Ingesting all Level1 summaries into Level1...")
        resp_l1 = post_to_level(config.LEVEL1_URL, "/ingest", files=files)
        for _, (filename, file_obj, mime) in files:
            file_obj.close()

        # --- Step 4: Summarize each Level1 summary into Level0 ---
        summary_l0_pdfs = []
        for summary_l1_pdf, summary_l1_text in summary_l1_pdfs:
            logger.info(
                f"Summarizing Level1 summary for {summary_l1_pdf} into Level0..."
            )
            level1_char_count = len(summary_l1_text)
            target_level0_chars = int(level1_char_count * config.LEVEL1_TO_0_RATIO)

            summary_l0_text = summarizer.compress(
                summary_l1_text, target_level0_chars, "level1", "level0"
            )
            summary_l0_pdf = os.path.join(
                config.PDFS_DIR, f"summary_l1_to_l0_{os.path.basename(summary_l1_pdf)}"
            )
            text_to_pdf(summary_l0_text, summary_l0_pdf)
            summary_l0_pdfs.append(summary_l0_pdf)

        # --- Step 5: Ingest all Level0 summaries ---
        files = [
            (
                "files",
                (os.path.basename(p), open(p, "rb"), "application/pdf"),
            )
            for p in summary_l0_pdfs
        ]
        logger.info("Ingesting all Level0 summaries into Level0...")
        resp_l0 = post_to_level(config.LEVEL0_URL, "/ingest", files=files)
        for _, (filename, file_obj, mime) in files:
            file_obj.close()

        logger.info("Multi-level ingestion completed successfully.")
        return {"level2": resp_l2, "level1": resp_l1, "level0": resp_l0}
