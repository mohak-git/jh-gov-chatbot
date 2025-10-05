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

        # --- Step 2: Parse PDFs to text ---
        extracted_texts = [pdf_to_text(p) for p in pdf_paths]
        level2_text = "\n\n".join(extracted_texts)
        level2_char_count = len(level2_text)
        logger.info(f"Level2 text length: {level2_char_count} chars")

        # --- Step 3: Summarize Level2 → Level1 ---
        target_level1_chars = int(level2_char_count * config.LEVEL2_TO_1_RATIO)
        logger.info(f"Summarizing Level2 content into Level1 {target_level1_chars}...")
        summary_l1_text = summarizer.compress(
            level2_text, target_level1_chars, "level2", "level1"
        )
        summary_l1_pdf = os.path.join(config.PDFS_DIR, "summary_l2_to_l1.pdf")
        text_to_pdf(summary_l1_text, summary_l1_pdf)

        # --- Step 4: Level1 ingest ---
        files = [
            (
                "files",
                (
                    os.path.basename(summary_l1_pdf),
                    open(summary_l1_pdf, "rb"),
                    "application/pdf",
                ),
            )
        ]
        logger.info("Ingesting summarized PDF into Level1...")
        resp_l1 = post_to_level(config.LEVEL1_URL, "/ingest", files=files)
        for _, (filename, file_obj, mime) in files:
            file_obj.close()

        # --- Step 5: Summarize Level1 → Level0 ---
        level1_char_count = len(summary_l1_text)
        target_level0_chars = int(level1_char_count * config.LEVEL1_TO_0_RATIO)
        logger.info(f"Summarizing Level1 content into Level0 {target_level0_chars}...")
        summary_l0_text = summarizer.compress(
            summary_l1_text, target_level0_chars, "level1", "level0"
        )
        summary_l0_pdf = os.path.join(config.PDFS_DIR, "summary_l1_to_l0.pdf")
        text_to_pdf(summary_l0_text, summary_l0_pdf)

        # --- Step 5: Level0 ingest ---
        files = [
            (
                "files",
                (
                    os.path.basename(summary_l0_pdf),
                    open(summary_l0_pdf, "rb"),
                    "application/pdf",
                ),
            )
        ]
        resp_l0 = post_to_level(config.LEVEL0_URL, "/ingest", files=files)
        for _, (filename, file_obj, mime) in files:
            file_obj.close()

        logger.info("Multi-level ingestion completed successfully.")
        return {"level2": resp_l2, "level1": resp_l1, "level0": resp_l0}
