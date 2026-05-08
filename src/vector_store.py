from dataclasses import dataclass
from typing import Optional

import chromadb
from chromadb.utils import embedding_functions

import config
from src.document_processor import DocumentChunk


@dataclass
class RetrievedChunk:
    text: str
    score: float
    doc_id: str
    title: str
    source_filename: str
    doc_type: str
    chunk_index: int
    section: str = ""


class LegalVectorStore:
    def __init__(self) -> None:
        self._client = chromadb.PersistentClient(path=str(config.CHROMA_DIR))
        self._ef = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=config.EMBEDDING_MODEL
        )
        self._collections: dict[str, chromadb.Collection] = {}

    def _collection(self, name: str) -> chromadb.Collection:
        if name not in self._collections:
            self._collections[name] = self._client.get_or_create_collection(
                name=name,
                embedding_function=self._ef,
                metadata={"hnsw:space": "cosine"},
            )
        return self._collections[name]

    def add_chunks(self, chunks: list[DocumentChunk], collection_name: str) -> None:
        if not chunks:
            return
        col = self._collection(collection_name)
        ids = [f"{c.doc_id}_{c.chunk_index}" for c in chunks]
        docs = [c.text for c in chunks]
        metas = [
            {
                "doc_id": c.doc_id,
                "title": c.title,
                "source_filename": c.source_filename,
                "doc_type": c.doc_type,
                "chunk_index": c.chunk_index,
                "section": c.section,
            }
            for c in chunks
        ]
        col.upsert(ids=ids, documents=docs, metadatas=metas)

    def query(
        self,
        query_text: str,
        collection_names: list[str],
        n_results: int = config.TOP_K_RETRIEVAL,
        doc_id_filter: Optional[str] = None,
    ) -> list[RetrievedChunk]:
        all_results: list[RetrievedChunk] = []

        for col_name in collection_names:
            try:
                col = self._collection(col_name)
                where = {"doc_id": doc_id_filter} if doc_id_filter else None
                kwargs: dict = dict(
                    query_texts=[query_text],
                    n_results=min(n_results, max(col.count(), 1)),
                    include=["documents", "metadatas", "distances"],
                )
                if where:
                    kwargs["where"] = where
                res = col.query(**kwargs)

                docs = res["documents"][0]
                metas = res["metadatas"][0]
                dists = res["distances"][0]

                for doc, meta, dist in zip(docs, metas, dists):
                    score = 1.0 - dist
                    all_results.append(
                        RetrievedChunk(
                            text=doc,
                            score=score,
                            doc_id=meta.get("doc_id", ""),
                            title=meta.get("title", ""),
                            source_filename=meta.get("source_filename", ""),
                            doc_type=meta.get("doc_type", ""),
                            chunk_index=int(meta.get("chunk_index", 0)),
                            section=meta.get("section", ""),
                        )
                    )
            except Exception:
                continue

        # Deduplicate, sort by score descending, return top n
        seen: set[str] = set()
        unique: list[RetrievedChunk] = []
        for r in sorted(all_results, key=lambda x: x.score, reverse=True):
            key = f"{r.doc_id}_{r.chunk_index}"
            if key not in seen:
                seen.add(key)
                unique.append(r)

        return unique[:n_results]

    def get_all_chunks_for_doc(self, doc_id: str, collection_name: str) -> list[RetrievedChunk]:
        col = self._collection(collection_name)
        res = col.get(where={"doc_id": doc_id}, include=["documents", "metadatas"])
        chunks: list[RetrievedChunk] = []
        for doc, meta in zip(res["documents"], res["metadatas"]):
            chunks.append(
                RetrievedChunk(
                    text=doc,
                    score=1.0,
                    doc_id=meta.get("doc_id", ""),
                    title=meta.get("title", ""),
                    source_filename=meta.get("source_filename", ""),
                    doc_type=meta.get("doc_type", ""),
                    chunk_index=int(meta.get("chunk_index", 0)),
                    section=meta.get("section", ""),
                )
            )
        return sorted(chunks, key=lambda x: x.chunk_index)

    def list_documents(self, collection_names: Optional[list[str]] = None) -> list[dict]:
        if collection_names is None:
            collection_names = list(config.COLLECTIONS.values())

        seen_ids: set[str] = set()
        docs: list[dict] = []

        for col_name in collection_names:
            try:
                col = self._collection(col_name)
                res = col.get(include=["metadatas"])
                for meta in res["metadatas"]:
                    doc_id = meta.get("doc_id", "")
                    if doc_id and doc_id not in seen_ids:
                        seen_ids.add(doc_id)
                        docs.append(
                            {
                                "doc_id": doc_id,
                                "title": meta.get("title", ""),
                                "doc_type": meta.get("doc_type", ""),
                                "source_filename": meta.get("source_filename", ""),
                                "collection": col_name,
                            }
                        )
            except Exception:
                continue

        return docs

    def delete_document(self, doc_id: str, collection_name: str) -> None:
        col = self._collection(collection_name)
        res = col.get(where={"doc_id": doc_id})
        if res["ids"]:
            col.delete(ids=res["ids"])

    def collection_count(self, collection_name: str) -> int:
        try:
            return self._collection(collection_name).count()
        except Exception:
            return 0
