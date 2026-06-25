import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

try:
    # pyrefly: ignore [missing-import]
    from sentence_transformers import SentenceTransformer
except ImportError:
    # We catch this at module level to provide a clearer error if the package is missing,
    # though the class also handles initialization errors.
    pass

# Configure module-level logger
logger = logging.getLogger(__name__)

@dataclass
class EmbeddedChunk:
    """
    Represents a text chunk coupled tightly with its dense vector embedding 
    and strictly preserved original metadata.
    """
    chunk_content: str
    metadata: Dict[str, Any]
    embedding: List[float]


class MedicalEmbeddingService:
    """
    A service for generating dense vector embeddings from medical text.
    
    This class strictly handles loading the sentence-transformers model weights 
    into memory and computing embeddings for either document chunks or queries.
    It does not handle document chunking or VectorDB integration.
    """

    def __init__(
        self, 
        model_name: str = "BAAI/bge-small-en-v1.5", 
        device: Optional[str] = None,
        log_level: int = logging.INFO
    ):
        """
        Initializes the MedicalEmbeddingService and loads the model weights.

        Args:
            model_name: The HuggingFace model hub name for the embedding model.
            device: The device to load the model on (e.g., "cuda", "cpu", "mps").
                    If None, sentence-transformers will automatically detect and use 
                    the best available device.
            log_level: The logging level to use. Defaults to logging.INFO.
        """
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        logger.setLevel(log_level)

        self.model_name = model_name
        self.device = device

        logger.info(f"Initializing embedding model '{self.model_name}' on device '{self.device or 'auto'}'.")
        
        try:
            # If the model is not cached locally, sentence-transformers will download it
            kwargs = {}
            if self.device:
                kwargs["device"] = self.device
                
            self.model = SentenceTransformer(self.model_name, **kwargs)
            logger.info("Embedding model loaded successfully.")
        except Exception as e:
            logger.critical(f"Failed to load embedding model '{self.model_name}': {str(e)}")
            raise RuntimeError(f"Could not initialize the embedding model: {str(e)}") from e

    def _extract_chunk_content(self, chunk: Any) -> tuple[str, Dict[str, Any]]:
        """
        Helper method to robustly extract content and metadata whether the input 
        is a dictionary or a dataclass/object (e.g., DocumentChunk).
        """
        if isinstance(chunk, dict):
            content = chunk.get("chunk_content", "")
            metadata = chunk.get("metadata", {})
            return content, metadata
        
        content = getattr(chunk, "chunk_content", "")
        metadata = getattr(chunk, "metadata", {})
        return content, metadata

    def embed_chunks(self, chunks: List[Any]) -> List[EmbeddedChunk]:
        """
        Computes dense vector embeddings for a list of document chunks.

        Args:
            chunks: A list of DocumentChunk objects (from chunker.py) or dictionaries 
                    containing 'chunk_content' and 'metadata'.

        Returns:
            A new list of EmbeddedChunk dataclasses that tightly couple the text, 
            metadata, and vector embedding together.
        """
        if not chunks:
            logger.warning("No chunks provided for embedding. Returning empty list.")
            return []

        logger.info(f"Computing embeddings for {len(chunks)} chunks.")
        
        embedded_results: List[EmbeddedChunk] = []
        texts_to_embed: List[str] = []
        valid_chunks: List[Any] = []

        # First pass: extract all text to batch the embedding process for performance
        for idx, chunk in enumerate(chunks):
            content, metadata = self._extract_chunk_content(chunk)
            if not content.strip():
                logger.debug(f"Chunk at index {idx} has empty content; skipping embedding.")
                continue
            
            texts_to_embed.append(content)
            valid_chunks.append((content, metadata))

        if not texts_to_embed:
            return []

        try:
            # Generate embeddings in a batch. 
            # We convert the numpy arrays to flat python lists of floats for downstream compatibility (e.g., JSON serialization or VectorDBs)
            embeddings = self.model.encode(texts_to_embed, convert_to_numpy=True)
            
            for (content, metadata), emb in zip(valid_chunks, embeddings):
                embedded_results.append(
                    EmbeddedChunk(
                        chunk_content=content,
                        metadata=metadata.copy(),
                        embedding=emb.tolist()
                    )
                )
            
            logger.info(f"Successfully generated embeddings for {len(embedded_results)} chunks.")
            
        except Exception as e:
            logger.error(f"Error computing bulk embeddings for chunks: {str(e)}")
            raise

        return embedded_results

    def embed_query(self, query: str) -> List[float]:
        """
        Computes a vector embedding for a single text string (e.g., a search query).

        Args:
            query: The raw text string to embed.

        Returns:
            A flat list of floats representing the dense vector embedding.
        """
        if not query or not query.strip():
            logger.warning("Empty query provided for embedding.")
            return []

        logger.debug(f"Computing embedding for query: '{query[:50]}...'")
        
        try:
            # encode single query and convert to list of floats
            embedding = self.model.encode(query, convert_to_numpy=True)
            return embedding.tolist()
        except Exception as e:
            logger.error(f"Error computing embedding for query: {str(e)}")
            raise
