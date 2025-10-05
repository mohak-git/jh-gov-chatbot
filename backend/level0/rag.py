import logging
from typing import List, Dict, Any

import numpy as np
import google.generativeai as genai

from level0.vectorstore import FaissStore

logger = logging.getLogger(__name__)


# -------------------------------------------------------------------
# Embeddings Client
# -------------------------------------------------------------------
class EmbeddingsClient:
    def __init__(self, model_name: str, api_key: str, batch_size: int = 64):
        if not api_key:
            raise RuntimeError("GOOGLE_API_KEY not set.")
        genai.configure(api_key=api_key)
        self.model_name = model_name
        self.batch_size = batch_size

    def embed(self, texts: List[str]) -> np.ndarray:
        if not texts:
            return np.zeros((0, 768), dtype=np.float32)
        batches: List[np.ndarray] = []
        total = len(texts)
        for i in range(0, total, self.batch_size):
            batch = texts[i : i + self.batch_size]
            logger.info(
                f"[EMBED] Processing batch {i//self.batch_size + 1}/{(total + self.batch_size - 1)//self.batch_size}:\n"
                f"  batch_size = {len(batch)}"
            )

            try:
                resp = genai.embed_content(
                    model=self.model_name, content=batch, task_type="retrieval_document"
                )
                if isinstance(resp, dict) and "embeddings" in resp:
                    vectors = [
                        np.array(item["values"], dtype=np.float32)
                        for item in resp["embeddings"]
                    ]
                elif isinstance(resp, dict) and "embedding" in resp:
                    vectors = [np.array(resp["embedding"], dtype=np.float32)]
                else:
                    vecs = getattr(resp, "embeddings", None)
                    if vecs is None:
                        vecs = [getattr(resp, "embedding")]
                    vectors = [
                        np.array(getattr(v, "values", v), dtype=np.float32)
                        for v in vecs
                    ]
                batches.append(np.vstack(vectors))
                logger.info(
                    f"[EMBED] Batch embedded successfully | vectors={len(vectors)}"
                )
            except Exception as e:
                logger.exception(
                    f"[EMBED] Failed to embed batch {i//self.batch_size + 1}"
                )
                raise RuntimeError("Embedding failed") from e
            return (
                np.vstack(batches) if batches else np.zeros((0, 768), dtype=np.float32)
            )


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
        preview = prompt if len(prompt) < 4000 else prompt[:4000] + "\n... [truncated]"
        logger.info(
            f"[LLM] Generating answer with Gemini:\n  prompt_preview:\n{preview}"
        )
        try:
            response = self.model.generate_content(
                prompt, generation_config={"max_output_tokens": max_output_tokens}
            )
            logger.info(
                f"[LLM] Generation completed successfully | output_length={len(response.text or '')}"
            )
            return (response.text or "").strip()
        except Exception:
            logger.exception("[LLM] Generation failed")
            raise RuntimeError("LLM generation failed")


# -------------------------------------------------------------------
# RAG Pipeline
# -------------------------------------------------------------------
class RAGPipeline:
    def __init__(
        self, store: FaissStore, embedder: EmbeddingsClient, llm: GeminiClient
    ):
        self.store = store
        self.embedder = embedder
        self.llm = llm

    def build_index(self, chunks: List[Dict[str, Any]]) -> int:
        texts = [c["text"] for c in chunks]
        if not texts:
            logger.info("[INDEX] No chunks to index.")
            return 0
        logger.info(f"[INDEX] Building index:\n  total_chunks={len(chunks)}")
        try:
            vectors = self.embedder.embed(texts)

            logger.info(f"[INDEX] Indexing {vectors.shape[0]} vectors…")
            self.store.add(vectors, chunks)
            self.store.save()
            logger.info(
                f"[INDEX] Index built and saved | vectors_added={vectors.shape[0]}"
            )

            return vectors.shape[0]
        except Exception:
            logger.exception("[INDEX] Failed to build index")
            raise RuntimeError("Index build failed")

    def retrieve(self, question: str, top_k: int) -> List[Dict[str, Any]]:
        logger.info(
            f"[RETRIEVE] Retrieving top {top_k} chunks for question:\n  {question}"
        )
        try:
            q_vec = self.embedder.embed([question])[0]
            hits = self.store.search(q_vec, top_k)
            results = [
                {
                    "score": score,
                    "text": meta.get("text", ""),
                    "source_file": meta.get("source_file", ""),
                    "page_start": int(meta.get("page_start", 0)),
                    "page_end": int(meta.get("page_end", 0)),
                }
                for score, meta in hits
            ]
            logger.info(f"[RETRIEVE] Retrieved {len(results)} chunks")
            return results
        except Exception:
            logger.exception("[RETRIEVE] Retrieval failed")
            raise RuntimeError("Retrieval failed")

    def answer(
        self, question: str, top_k: int, max_output_tokens: int
    ) -> Dict[str, Any]:
        retrieved = self.retrieve(question, top_k)
        context_blocks = []
        for i, r in enumerate(retrieved, start=1):
            header = f"[Source {i}] file: {r['source_file']} pages: {r['page_start']}-{r['page_end']} (score={r['score']:.3f})"
            context_blocks.append(header + "\n" + r["text"])
        context_text = "\n\n".join(context_blocks)
        prompt = (
            "You are a helpful assistant answering questions about Jharkhand government policies.\n"
            "Use ONLY the provided sources. If the answer is not contained, say you don't know.\n"
            "Cite sources inline as [Source N] where N corresponds to the source block.\n\n"
            f"Question: {question}\n\nSources:\n{context_text}\n\nAnswer:"
        )
        logger.info(
            f"[RAG] Generating answer for question:\n  {question}\n  retrieved_sources={len(retrieved)}"
        )
        try:
            answer_text = self.llm.generate(prompt, max_output_tokens=max_output_tokens)
            logger.info(f"[RAG] Answer generated | answer_length={len(answer_text)}")
        except Exception:
            logger.exception("[RAG] Answer generation failed")
            raise RuntimeError("Answer generation failed")

        citations = [
            {
                "source_file": r["source_file"],
                "page_start": r["page_start"],
                "page_end": r["page_end"],
                "score": r["score"],
                "snippet": r["text"][:500],
            }
            for r in retrieved
        ]
        return {"answer": answer_text, "citations": citations, "prompt": prompt}
