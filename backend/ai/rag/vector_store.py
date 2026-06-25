import logging
import uuid
from typing import List, Dict, Any

# pyrefly: ignore [missing-import]
import chromadb

# Configure module-level logger
logger = logging.getLogger(__name__)

class MedicalVectorStore:
    """
    A vector storage service specifically designed for medical documents using ChromaDB.
    
    This class handles persistent storage of pre-computed text embeddings, along with 
    their original content and metadata. It does not handle text splitting or embedding generation.
    """

    def __init__(
        self, 
        persist_directory: str = "./chroma_db", 
        collection_name: str = "cardiology_guidelines",
        log_level: int = logging.INFO
    ):
        """
        Initializes the MedicalVectorStore and connects to the ChromaDB instance.

        Args:
            persist_directory: The local directory path where ChromaDB will persist the data.
            collection_name: The name of the collection to use within ChromaDB.
            log_level: The logging level to use. Defaults to logging.INFO.
        """
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        logger.setLevel(log_level)

        self.persist_directory = persist_directory
        self.collection_name = collection_name

        logger.info(f"Initializing ChromaDB PersistentClient at '{self.persist_directory}'")
        try:
            self.client = chromadb.PersistentClient(path=self.persist_directory)
            self.collection = self.client.get_or_create_collection(name=self.collection_name)
            logger.info(f"Successfully connected to collection '{self.collection_name}'. Current count: {self.collection.count()}")
        except Exception as e:
            logger.critical(f"Failed to initialize ChromaDB: {str(e)}")
            raise RuntimeError(f"Database initialization error: {str(e)}") from e

    def _extract_chunk_data(self, embedded_chunk: Any) -> tuple[str, Dict[str, Any], List[float]]:
        """
        Helper method to robustly extract content, metadata, and embeddings from either
        a dictionary or a dataclass/object (e.g., EmbeddedChunk).
        """
        if isinstance(embedded_chunk, dict):
            content = embedded_chunk.get("chunk_content", "")
            metadata = embedded_chunk.get("metadata", {})
            embedding = embedded_chunk.get("embedding", [])
            return content, metadata, embedding
        
        content = getattr(embedded_chunk, "chunk_content", "")
        metadata = getattr(embedded_chunk, "metadata", {})
        embedding = getattr(embedded_chunk, "embedding", [])
        return content, metadata, embedding

    def store_chunks(self, embedded_chunks: List[Any]) -> None:
        """
        Takes a list of embedded chunks, formats them, and upserts them into ChromaDB.

        Args:
            embedded_chunks: A list of EmbeddedChunk objects or dictionaries containing 
                             'chunk_content', 'metadata', and 'embedding'.
        """
        if not embedded_chunks:
            logger.warning("No chunks provided to store. Skipping upsert.")
            return

        logger.info(f"Preparing to store {len(embedded_chunks)} chunks into '{self.collection_name}'.")

        ids: List[str] = []
        embeddings: List[List[float]] = []
        metadatas: List[Dict[str, Any]] = []
        documents: List[str] = []

        for idx, chunk in enumerate(embedded_chunks):
            try:
                content, metadata, embedding = self._extract_chunk_data(chunk)

                if not content or not embedding:
                    logger.debug(f"Chunk at index {idx} is missing content or embedding; skipping.")
                    continue

                # Generate a unique ID for the vector
                chunk_id = str(uuid.uuid4())
                
                # ChromaDB requires metadata values to be strings, ints, or floats.
                # We sanitize metadata to avoid insertion errors.
                sanitized_metadata = {k: v for k, v in metadata.items() if isinstance(v, (str, int, float, bool))}

                ids.append(chunk_id)
                embeddings.append(embedding)
                metadatas.append(sanitized_metadata)
                documents.append(content)
            except Exception as e:
                logger.error(f"Error parsing chunk at index {idx}: {str(e)}")
                continue

        if not ids:
            logger.warning("No valid chunks were found after parsing. Nothing to insert.")
            return

        try:
            # We use upsert so that if an ID already exists, it updates the record.
            self.collection.upsert(
                ids=ids,
                embeddings=embeddings,
                metadatas=metadatas,
                documents=documents
            )
            logger.info(f"Successfully upserted {len(ids)} records into ChromaDB.")
        except Exception as e:
            logger.error(f"Failed to upsert chunks into ChromaDB: {str(e)}")
            raise

    def search_by_vector(self, query_vector: List[float], n_results: int = 5) -> List[Dict[str, Any]]:
        """
        Queries the ChromaDB collection using a dense vector to find the most relevant chunks.

        Args:
            query_vector: A list of floats representing the embedded search query.
            n_results: The maximum number of results to return.

        Returns:
            A list of dictionaries containing the matched content, metadata, and distance.
        """
        if not query_vector:
            logger.warning("Empty query_vector provided. Returning empty results.")
            return []

        logger.debug(f"Searching collection '{self.collection_name}' for top {n_results} matches.")

        try:
            results = self.collection.query(
                query_embeddings=[query_vector],
                n_results=n_results,
                # Include metadata, documents, and distances in the result set
                include=["metadatas", "documents", "distances"]
            )

            # ChromaDB returns a dictionary of lists of lists. We flatten this into a clean list of dicts.
            formatted_results: List[Dict[str, Any]] = []
            
            # Since we only passed one query_vector, results are in index 0
            if not results["ids"] or not results["ids"][0]:
                logger.info("No matching results found in the database.")
                return formatted_results

            for i in range(len(results["ids"][0])):
                doc_id = results["ids"][0][i]
                document = results["documents"][0][i] if results.get("documents") else ""
                metadata = results["metadatas"][0][i] if results.get("metadatas") else {}
                distance = results["distances"][0][i] if results.get("distances") else 0.0

                formatted_results.append({
                    "id": doc_id,
                    "content": document,
                    "metadata": metadata,
                    "distance": distance
                })

            logger.info(f"Search returned {len(formatted_results)} results.")
            return formatted_results

        except Exception as e:
            logger.error(f"Failed to query ChromaDB: {str(e)}")
            raise
