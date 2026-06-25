import logging
from typing import List, Dict, Any, Union
from dataclasses import dataclass

# pyrefly: ignore [missing-import]
from langchain_text_splitters import RecursiveCharacterTextSplitter

# Configure module-level logger
logger = logging.getLogger(__name__)

@dataclass
class DocumentChunk:
    """
    Represents a semantically meaningful chunk of text extracted from a medical document.
    Ensures metadata is strictly preserved for exact medical citations.
    """
    chunk_content: str
    metadata: Dict[str, Any]


class MedicalTextChunker:
    """
    A specialized text chunker for medical documents.
    
    This class has a single responsibility: taking extracted text and metadata
    (from a document loader) and splitting it into overlapping text chunks suitable 
    for downstream vector embedding. It does not handle file loading, embeddings, 
    or VectorDB interactions.
    """

    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200, log_level: int = logging.INFO):
        """
        Initializes the MedicalTextChunker.

        Args:
            chunk_size: The maximum size of each text chunk (in characters).
            chunk_overlap: The number of characters to overlap between consecutive chunks 
                           to preserve semantic context.
            log_level: The logging level to use. Defaults to logging.INFO.
        """
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        logger.setLevel(log_level)

        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

        try:
            self.text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=self.chunk_size,
                chunk_overlap=self.chunk_overlap,
                # Standard separators optimize for natural paragraph/sentence breaks
                separators=["\n\n", "\n", " ", ""]
            )
            logger.debug(f"Initialized RecursiveCharacterTextSplitter with chunk_size={chunk_size} and overlap={chunk_overlap}.")
        except Exception as e:
            logger.critical(f"Failed to initialize text splitter: {str(e)}")
            raise

    def _extract_content_and_metadata(self, document: Any) -> tuple[str, Dict[str, Any]]:
        """
        Helper method to robustly extract content and metadata whether the input 
        is a dictionary or a dataclass/object (e.g., DocumentPage).
        """
        if isinstance(document, dict):
            content = document.get("page_content", "")
            metadata = document.get("metadata", {})
            return content, metadata
        
        # Assume it's an object with attributes (like DocumentPage)
        content = getattr(document, "page_content", "")
        metadata = getattr(document, "metadata", {})
        return content, metadata

    def chunk_documents(self, documents: List[Any]) -> List[DocumentChunk]:
        """
        Splits a list of medical documents into smaller, overlapping chunks while 
        strictly preserving the original metadata.

        Args:
            documents: A list of document objects or dictionaries containing 
                       'page_content' and 'metadata'.

        Returns:
            A list of DocumentChunk objects containing the chunked text and inherited metadata.
        """
        if not documents:
            logger.warning("No documents provided for chunking. Returning empty list.")
            return []

        all_chunks: List[DocumentChunk] = []
        logger.info(f"Starting chunking process for {len(documents)} document page(s).")

        for idx, doc in enumerate(documents):
            try:
                page_content, metadata = self._extract_content_and_metadata(doc)
                
                if not page_content or not page_content.strip():
                    logger.debug(f"Document at index {idx} has empty content; skipping.")
                    continue

                # Split the text using the langchain splitter
                text_chunks = self.text_splitter.split_text(page_content)
                
                # Attach the original metadata to every resulting chunk
                for chunk_idx, chunk_text in enumerate(text_chunks):
                    # We copy the metadata to avoid accidental mutation downstream, 
                    # and optionally append chunk-specific metadata.
                    chunk_metadata = metadata.copy()
                    chunk_metadata["chunk_index"] = chunk_idx
                    
                    all_chunks.append(DocumentChunk(
                        chunk_content=chunk_text,
                        metadata=chunk_metadata
                    ))

            except Exception as e:
                # Log the error but continue processing the remaining documents
                source_hint = metadata.get("source", f"index {idx}") if 'metadata' in locals() else f"index {idx}"
                logger.error(f"Error chunking document from {source_hint}: {str(e)}")
                continue

        logger.info(f"Finished chunking. Produced {len(all_chunks)} total chunks from {len(documents)} document pages.")
        return all_chunks
