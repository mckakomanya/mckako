"""
OncoRAD Vector Store Module

Manages the vector database for clinical document storage and retrieval.
Uses ChromaDB for vector storage with sentence-transformers for embeddings.
"""

import os
import hashlib
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
from datetime import datetime

try:
    import chromadb
    from chromadb.config import Settings
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False


class DocumentChunk:
    """Represents a chunk of a document with metadata."""

    def __init__(
        self,
        text: str,
        document_name: str,
        page_number: Optional[int] = None,
        section: Optional[str] = None,
        chunk_index: int = 0,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.text = text
        self.document_name = document_name
        self.page_number = page_number
        self.section = section
        self.chunk_index = chunk_index
        self.metadata = metadata or {}
        self.chunk_id = self._generate_id()

    def _generate_id(self) -> str:
        """Generate unique ID for this chunk."""
        content = f"{self.document_name}:{self.page_number}:{self.chunk_index}:{self.text[:100]}"
        return hashlib.md5(content.encode()).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "chunk_id": self.chunk_id,
            "text": self.text,
            "document_name": self.document_name,
            "page_number": self.page_number,
            "section": self.section,
            "chunk_index": self.chunk_index,
            **self.metadata
        }


class ClinicalVectorStore:
    """
    Vector store for clinical documents using ChromaDB.

    Provides semantic search capabilities for oncology treatment guidelines,
    clinical studies, and medical literature.
    """

    COLLECTION_NAME = "oncorad_clinical_docs"
    DEFAULT_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

    def __init__(
        self,
        persist_directory: str = "./data/vector_db",
        embedding_model: Optional[str] = None,
        use_gpu: bool = False
    ):
        """
        Initialize the vector store.

        Args:
            persist_directory: Directory for persistent storage
            embedding_model: Sentence transformer model name
            use_gpu: Whether to use GPU for embeddings
        """
        self.persist_directory = Path(persist_directory)
        self.persist_directory.mkdir(parents=True, exist_ok=True)

        # Initialize embedding model
        self.embedding_model_name = embedding_model or self.DEFAULT_MODEL
        self._embedder: Optional[SentenceTransformer] = None

        # Initialize ChromaDB
        self._client: Optional[chromadb.Client] = None
        self._collection = None
        self._use_gpu = use_gpu

        # Track loaded documents
        self._document_registry: Dict[str, Dict[str, Any]] = {}

    @property
    def embedder(self) -> 'SentenceTransformer':
        """Lazy loading of embedding model."""
        if self._embedder is None:
            if not SENTENCE_TRANSFORMERS_AVAILABLE:
                raise ImportError(
                    "sentence-transformers is required. "
                    "Install with: pip install sentence-transformers"
                )
            device = "cuda" if self._use_gpu else "cpu"
            self._embedder = SentenceTransformer(
                self.embedding_model_name,
                device=device
            )
        return self._embedder

    @property
    def client(self) -> 'chromadb.Client':
        """Lazy loading of ChromaDB client."""
        if self._client is None:
            if not CHROMADB_AVAILABLE:
                raise ImportError(
                    "chromadb is required. Install with: pip install chromadb"
                )
            self._client = chromadb.PersistentClient(
                path=str(self.persist_directory),
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
        return self._client

    @property
    def collection(self):
        """Get or create the main collection."""
        if self._collection is None:
            self._collection = self.client.get_or_create_collection(
                name=self.COLLECTION_NAME,
                metadata={
                    "description": "OncoRAD clinical documents",
                    "hnsw:space": "cosine"
                }
            )
        return self._collection

    def _embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a list of texts."""
        embeddings = self.embedder.encode(
            texts,
            convert_to_numpy=True,
            show_progress_bar=len(texts) > 10
        )
        return embeddings.tolist()

    def add_document_chunks(
        self,
        chunks: List[DocumentChunk],
        document_type: str = "guideline"
    ) -> int:
        """
        Add document chunks to the vector store.

        Args:
            chunks: List of DocumentChunk objects
            document_type: Type of document (guideline, study, textbook)

        Returns:
            Number of chunks added
        """
        if not chunks:
            return 0

        # Prepare data for ChromaDB
        ids = []
        documents = []
        metadatas = []

        for chunk in chunks:
            ids.append(chunk.chunk_id)
            documents.append(chunk.text)
            metadatas.append({
                "document_name": chunk.document_name,
                "page_number": chunk.page_number or -1,
                "section": chunk.section or "",
                "chunk_index": chunk.chunk_index,
                "document_type": document_type,
                "indexed_at": datetime.now().isoformat()
            })

        # Generate embeddings
        embeddings = self._embed_texts(documents)

        # Add to collection (upsert to handle duplicates)
        self.collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas
        )

        # Update document registry
        doc_name = chunks[0].document_name
        self._document_registry[doc_name] = {
            "chunks": len(chunks),
            "document_type": document_type,
            "indexed_at": datetime.now().isoformat()
        }

        return len(chunks)

    def search(
        self,
        query: str,
        n_results: int = 5,
        document_filter: Optional[str] = None,
        section_filter: Optional[str] = None,
        document_type_filter: Optional[str] = None,
        min_relevance: float = 0.0
    ) -> List[Dict[str, Any]]:
        """
        Search for relevant document chunks.

        Args:
            query: Search query text
            n_results: Maximum number of results
            document_filter: Filter by specific document name
            section_filter: Filter by section (e.g., "Treatment", "Outcomes")
            document_type_filter: Filter by document type
            min_relevance: Minimum relevance score (0-1)

        Returns:
            List of matching chunks with metadata and scores
        """
        # Build where clause for filtering
        where_clause = None
        where_conditions = []

        if document_filter:
            where_conditions.append({"document_name": {"$eq": document_filter}})
        if section_filter:
            where_conditions.append({"section": {"$contains": section_filter}})
        if document_type_filter:
            where_conditions.append({"document_type": {"$eq": document_type_filter}})

        if len(where_conditions) == 1:
            where_clause = where_conditions[0]
        elif len(where_conditions) > 1:
            where_clause = {"$and": where_conditions}

        # Generate query embedding
        query_embedding = self._embed_texts([query])[0]

        # Perform search
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=where_clause,
            include=["documents", "metadatas", "distances"]
        )

        # Format results
        formatted_results = []
        if results and results['ids'] and results['ids'][0]:
            for i, chunk_id in enumerate(results['ids'][0]):
                # Convert distance to similarity score (cosine distance)
                distance = results['distances'][0][i]
                relevance_score = 1 - distance  # Convert distance to similarity

                if relevance_score >= min_relevance:
                    formatted_results.append({
                        "chunk_id": chunk_id,
                        "text": results['documents'][0][i],
                        "document_name": results['metadatas'][0][i].get('document_name'),
                        "page_number": results['metadatas'][0][i].get('page_number'),
                        "section": results['metadatas'][0][i].get('section'),
                        "document_type": results['metadatas'][0][i].get('document_type'),
                        "relevance_score": round(relevance_score, 4)
                    })

        return formatted_results

    def search_by_sections(
        self,
        query: str,
        sections: List[str],
        n_results_per_section: int = 3
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Search across multiple sections and organize results.

        Args:
            query: Search query text
            sections: List of sections to search (e.g., ["Treatment", "Outcomes"])
            n_results_per_section: Results per section

        Returns:
            Dictionary mapping sections to their results
        """
        results_by_section = {}

        for section in sections:
            results = self.search(
                query=query,
                n_results=n_results_per_section,
                section_filter=section
            )
            results_by_section[section] = results

        return results_by_section

    def hybrid_search(
        self,
        clinical_query: str,
        risk_level: str,
        tumor_type: str,
        n_results: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Perform a hybrid search optimized for clinical queries.

        Searches for treatment protocols and outcomes based on
        clinical parameters.

        Args:
            clinical_query: The clinical question
            risk_level: Patient risk classification
            tumor_type: Type of tumor
            n_results: Maximum results

        Returns:
            Combined and ranked results from multiple searches
        """
        # Construct enhanced queries
        queries = [
            clinical_query,
            f"{tumor_type} {risk_level} tratamiento radioterapia",
            f"{tumor_type} sobrevida control local resultados",
            f"{tumor_type} fraccionamiento dosis esquema"
        ]

        all_results = {}  # Use dict to deduplicate by chunk_id

        for query in queries:
            results = self.search(
                query=query,
                n_results=n_results // 2
            )
            for result in results:
                chunk_id = result['chunk_id']
                if chunk_id not in all_results:
                    all_results[chunk_id] = result
                else:
                    # Boost score for chunks found by multiple queries
                    current_score = all_results[chunk_id]['relevance_score']
                    new_score = result['relevance_score']
                    all_results[chunk_id]['relevance_score'] = min(
                        1.0,
                        current_score + (new_score * 0.3)
                    )

        # Sort by relevance and return top results
        sorted_results = sorted(
            all_results.values(),
            key=lambda x: x['relevance_score'],
            reverse=True
        )

        return sorted_results[:n_results]

    def get_document_list(self) -> List[Dict[str, Any]]:
        """Get list of all indexed documents."""
        # Query collection for unique documents
        all_items = self.collection.get(include=["metadatas"])

        document_info = {}
        for metadata in all_items.get('metadatas', []):
            doc_name = metadata.get('document_name')
            if doc_name:
                if doc_name not in document_info:
                    document_info[doc_name] = {
                        "filename": doc_name,
                        "document_type": metadata.get('document_type', 'unknown'),
                        "chunk_count": 0,
                        "indexed_at": metadata.get('indexed_at', 'unknown')
                    }
                document_info[doc_name]["chunk_count"] += 1

        return list(document_info.values())

    def get_stats(self) -> Dict[str, Any]:
        """Get vector store statistics."""
        count = self.collection.count()
        documents = self.get_document_list()

        return {
            "total_chunks": count,
            "total_documents": len(documents),
            "documents": documents,
            "persist_directory": str(self.persist_directory),
            "embedding_model": self.embedding_model_name
        }

    def delete_document(self, document_name: str) -> int:
        """
        Delete all chunks from a specific document.

        Args:
            document_name: Name of document to delete

        Returns:
            Number of chunks deleted
        """
        # Find all chunks for this document
        results = self.collection.get(
            where={"document_name": {"$eq": document_name}},
            include=["metadatas"]
        )

        if results and results['ids']:
            chunk_ids = results['ids']
            self.collection.delete(ids=chunk_ids)
            return len(chunk_ids)

        return 0

    def clear_all(self) -> None:
        """Clear all data from the vector store."""
        self.client.delete_collection(self.COLLECTION_NAME)
        self._collection = None
        self._document_registry = {}


class DocumentProcessor:
    """
    Processes documents into chunks for vector storage.

    Handles PDF, DOCX, and text files with intelligent chunking
    that preserves document structure.
    """

    DEFAULT_CHUNK_SIZE = 1000  # characters
    DEFAULT_CHUNK_OVERLAP = 200  # characters

    def __init__(
        self,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        chunk_overlap: int = DEFAULT_CHUNK_OVERLAP
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def process_text(
        self,
        text: str,
        document_name: str,
        page_number: Optional[int] = None,
        section: Optional[str] = None
    ) -> List[DocumentChunk]:
        """
        Process raw text into chunks.

        Args:
            text: Raw text content
            document_name: Name of source document
            page_number: Page number if applicable
            section: Section name if applicable

        Returns:
            List of DocumentChunk objects
        """
        chunks = []
        text = text.strip()

        if not text:
            return chunks

        # Split into chunks with overlap
        start = 0
        chunk_index = 0

        while start < len(text):
            end = start + self.chunk_size

            # Try to break at sentence boundary
            if end < len(text):
                # Look for sentence endings
                for delimiter in ['. ', '.\n', '! ', '? ']:
                    last_delim = text[start:end].rfind(delimiter)
                    if last_delim > self.chunk_size // 2:
                        end = start + last_delim + 1
                        break

            chunk_text = text[start:end].strip()

            if chunk_text:
                chunks.append(DocumentChunk(
                    text=chunk_text,
                    document_name=document_name,
                    page_number=page_number,
                    section=section,
                    chunk_index=chunk_index
                ))
                chunk_index += 1

            start = end - self.chunk_overlap

        return chunks

    def process_pdf(self, pdf_path: str) -> List[DocumentChunk]:
        """
        Process a PDF file into chunks.

        Args:
            pdf_path: Path to PDF file

        Returns:
            List of DocumentChunk objects
        """
        try:
            from pypdf import PdfReader
        except ImportError:
            raise ImportError("pypdf is required. Install with: pip install pypdf")

        pdf_path = Path(pdf_path)
        document_name = pdf_path.name

        reader = PdfReader(str(pdf_path))
        all_chunks = []

        for page_num, page in enumerate(reader.pages, start=1):
            text = page.extract_text()
            if text:
                # Detect section headers
                section = self._detect_section(text)

                page_chunks = self.process_text(
                    text=text,
                    document_name=document_name,
                    page_number=page_num,
                    section=section
                )
                all_chunks.extend(page_chunks)

        return all_chunks

    def _detect_section(self, text: str) -> Optional[str]:
        """
        Attempt to detect the section from text content.

        Args:
            text: Text content to analyze

        Returns:
            Detected section name or None
        """
        section_keywords = {
            "Tratamiento": ["tratamiento", "treatment", "terapia", "therapy", "manejo"],
            "Diagnóstico": ["diagnóstico", "diagnosis", "estadificación", "staging"],
            "Outcomes": ["sobrevida", "survival", "control local", "outcomes", "resultados"],
            "Toxicidad": ["toxicidad", "toxicity", "efectos adversos", "side effects"],
            "Fraccionamiento": ["fraccionamiento", "fractionation", "dosis", "dose", "esquema"]
        }

        text_lower = text[:500].lower()  # Check first 500 chars

        for section, keywords in section_keywords.items():
            for keyword in keywords:
                if keyword in text_lower:
                    return section

        return None


# Factory function for easy initialization
def create_vector_store(
    persist_directory: str = "./data/vector_db",
    **kwargs
) -> ClinicalVectorStore:
    """Create and return a configured vector store instance."""
    return ClinicalVectorStore(persist_directory=persist_directory, **kwargs)
