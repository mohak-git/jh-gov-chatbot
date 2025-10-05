import logging
import google.generativeai as genai

logger = logging.getLogger(__name__)


# -------------------------------------------------------------------
# LLM Client
# -------------------------------------------------------------------
class GeminiClient:
    def __init__(self, model_name: str, api_key: str):
        if not api_key:
            raise RuntimeError("GOOGLE_API_KEY not set.")
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model_name)

    def generate(self, prompt: str, max_output_tokens: int = 512) -> str:
        preview = prompt if len(prompt) < 3000 else prompt[:3000] + "\n...[truncated]"
        logger.info(f"[LLM] Generating text with Gemini\nPrompt Preview:\n{preview}")

        try:
            resp = self.model.generate_content(prompt)
            text = (resp.text or "").strip()
            logger.info(f"[LLM] Generation success | output_length={len(text)}")
            return text
        except Exception as e:
            logger.exception("[LLM] Generation failed")
            raise RuntimeError("LLM generation failed") from e


# ---------------------------------------------------------
# Summarizer
# ---------------------------------------------------------
class Summarizer:
    def __init__(self, gemini_client: GeminiClient):
        self.gemini = gemini_client

    def compress(
        self, text: str, target_chars: int, level_from: str, level_to: str
    ) -> str:
        """
        Compress a chunk of text into a smaller summary for the next level.

        :param text: Full text to summarize
        :param ratio: Fraction of original size (e.g., 0.2 means ~20%)
        :param level_from: Source level name (for logging)
        :param level_to: Target level name (for logging)
        :return: Compressed summary text
        """
        logger.info(
            f"[Summarizer] Compressing from {level_from} → {level_to} "
            f"into {target_chars} characters | input_length={len(text)}"
        )

        prompt = (
            f"You are an assistant compressing government scheme documents.\n"
            f"Summarize the following text to approximately {target_chars} characters."
            f"Preserve the key details needed"
            f"for answering queries at the {level_to} level."
            f"---\n{text}\n---\n\n"
            f"Now provide the compressed summary:"
        )

        try:
            summary = self.gemini.generate(prompt)
            logger.info(
                f"[Summarizer] Compression successful | "
                f"from {len(text)} chars → {len(summary)} chars"
            )
            return summary
        except Exception:
            logger.exception(
                f"[Summarizer] Failed compression {level_from} → {level_to}"
            )
            raise RuntimeError("Text compression failed")
