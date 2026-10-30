from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import List, Sequence
import re

import numpy as np
from openai import OpenAI


@dataclass
class Document:
    """Chunk text, its vector, and the source filename."""

    text: str
    embedding: np.ndarray
    source: str


class RAGPipeline:
    """
    Responsible for loading corpus, chunking, generating vector index, and retrieval.
    """

    def __init__(
        self,
        data_dir: Path,
        embedding_model: str = "text-embedding-3-small",
        generation_model: str = "gpt-4.1-mini",
        chunk_size: int = 200,
        chunk_overlap: int = 40,
        top_k: int = 4,
    ) -> None:
        # To change models or chunk parameters, modify here or override via environment variables
        self.data_dir = data_dir
        self.embedding_model = os.getenv("EMBEDDING_MODEL", embedding_model)
        self.generation_model = os.getenv("GENERATION_MODEL", generation_model)
        self.chunk_size = int(os.getenv("CHUNK_SIZE", chunk_size))
        self.chunk_overlap = int(os.getenv("CHUNK_OVERLAP", chunk_overlap))
        self.top_k = int(os.getenv("TOP_K", top_k))

        # Need to configure OPENAI_API_KEY in environment variables first
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.documents: List[Document] = []

    def load_and_build_index(self) -> None:
        """Load corpus, chunk, embed, and cache in memory."""
        raw_texts = self._load_corpus()
        chunk_items: List[tuple[str, str]] = []  # (chunk, source filename)
        for text, source in raw_texts:
            chunk_items.extend(self._chunk_text(text, source))

        if not chunk_items:
            raise ValueError("No usable corpus chunks found; please check data files.")

        chunks_only = [c for c, _ in chunk_items]
        embeddings = self._embed_texts(chunks_only)
        self.documents = [
            Document(text=chunk, embedding=emb, source=source)
            for (chunk, source), emb in zip(chunk_items, embeddings)
        ]

    def _load_corpus(self) -> List[tuple[str, str]]:
        """Read all txt files and return (content, filename)."""
        if not self.data_dir.exists():
            raise FileNotFoundError(f"Corpus directory does not exist: {self.data_dir}")

        texts: List[tuple[str, str]] = []
        for file_path in self.data_dir.glob("*.txt"):
            content = file_path.read_text(encoding="utf-8").strip()
            if content:
                texts.append((content, file_path.name))
        return texts

    def _chunk_text(self, text: str, source: str) -> List[tuple[str, str]]:
        """
        Split long text into chunks with overlap.
        - chunk_size: number of words per chunk
        - chunk_overlap: sliding window overlap to reduce sentence cuts
        """
        words = text.split()
        if not words:
            return []

        chunks: List[tuple[str, str]] = []
        step = max(1, self.chunk_size - self.chunk_overlap)
        for start in range(0, len(words), step):
            window = words[start : start + self.chunk_size]
            if window:
                chunks.append((" ".join(window), source))
        return chunks

    def _embed_texts(self, texts: Sequence[str]) -> List[np.ndarray]:
        """Batch embedding, returns list of numpy arrays."""
        response = self.client.embeddings.create(
            model=self.embedding_model,
            input=list(texts),
        )
        vectors = [
            np.array(item.embedding, dtype=np.float32) for item in response.data
        ]
        return vectors

    def search(self, query: str) -> List[Document]:
        """Embed query and return top_k matched documents."""
        if not self.documents:
            raise ValueError("Vector index not ready; please call load_and_build_index first.")

        query_vec = self._embed_texts([query])[0]
        doc_matrix = np.vstack([doc.embedding for doc in self.documents])

        # Normalize then compute cosine similarity
        doc_norms = np.linalg.norm(doc_matrix, axis=1, keepdims=True)
        query_norm = np.linalg.norm(query_vec)
        # Avoid division by zero
        doc_norms[doc_norms == 0] = 1e-10
        if query_norm == 0:
            query_norm = 1e-10

        scores = (doc_matrix @ query_vec) / (doc_norms.flatten() * query_norm)
        top_indices = scores.argsort()[::-1][: self.top_k]
        return [self.documents[i] for i in top_indices]

    def generate_answer(self, question: str, contexts: List[Document]) -> str:
        """
        Call LLM to generate answer.
        - To change model, modify generation_model or environment variable GENERATION_MODEL.
        - To control output length, add max_tokens in chat.completions.create.
        """
        context_texts = [doc.text for doc in contexts]

        # Privacy guard with corpus priority:
        # - If private question AND we have private info in current contexts -> answer with contexts.
        # - If private question AND current contexts lack private info -> try to pull private-related docs.
        # - If still none, then refuse for privacy.
        if self._is_private_question(question):
            if not self._has_private_info(context_texts):
                private_docs = self._find_private_docs(limit=self.top_k)
                if private_docs:
                    contexts = private_docs
                    context_texts = [doc.text for doc in contexts]
                else:
                    return "This is my privacy, I cannot answer that."

        # English system prompt with hard rules
        system_prompt = (
            "You are the AI persona of Steve Jobs. Follow these hard rules:\n"
            "1) Use only the provided public materials (talks/interviews before 2011) to inform answers.\n"
            "2) If a question asks for private life details not covered, say: "
            "\"I have not spoken about this in public; it's my private life, and I cannot answer.\"\n"
            "3) If a question involves products/events after 2011, say you passed away in 2011; "
            "at most offer hypothetical thoughts based on past views, clearly marked as hypothetical.\n"
            "4) If you do not have enough relevant context, say: \"I don't really talk about these in public.\" "
            "Do NOT mention documents, materials, or retrieval.\n"
            "5) Do not fabricate detailed events you never publicly shared or any post-2011 facts.\n"
            "Keep answers concise, energetic, in Steve Jobs' style. Do not mention reference snippets explicitly."
        )
        joined_contexts = "\n\n".join(
            f"- Snippet {idx+1}:\n{ctx}" for idx, ctx in enumerate(context_texts)
        )
        user_content = (
            f"User question: {question}\n\n"
            "Use the following reference snippets silently; do NOT mention them. "
            "If they are insufficient to answer, reply with: \"I don't really talk about these in public.\"\n"
            f"{joined_contexts}"
        )

        completion = self.client.chat.completions.create(
            model=self.generation_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
        )
        return completion.choices[0].message.content.strip()

    def _is_private_question(self, question: str) -> bool:
        """
        Coarse-grained detection of private life sensitive questions to avoid model hallucination.
        If matched, follow privacy rule response.
        """
        q = question.lower()
        # Keywords can be extended as needed
        private_keywords = [
            r"first love", r"初恋", r"girlfriend", r"boyfriend", r"lover",
            r"恋人", r"约会", r"结婚", r"婚姻", r"家庭隐私", r"私生活",
            r"孩子的名字", r"wife", r"spouse"
        ]
        return any(re.search(pat, q) for pat in private_keywords)

    def _has_private_info(self, contexts: List[str]) -> bool:
        """Check if contexts contain private-life related cues."""
        ctx = " ".join(contexts).lower()
        return self._contains_private_terms(ctx)

    def _find_private_docs(self, limit: int = 4) -> List[Document]:
        """Return up to `limit` documents that contain private-life cues."""
        hits: List[Document] = []
        for doc in self.documents:
            if self._contains_private_terms(doc.text.lower()):
                hits.append(doc)
                if len(hits) >= limit:
                    break
        return hits

    def _contains_private_terms(self, text: str) -> bool:
        private_terms = [
            "love", "girlfriend", "boyfriend", "wife", "spouse",
            "marriage", "children", "family", "lover", "dating"
        ]
        return any(term in text for term in private_terms)


