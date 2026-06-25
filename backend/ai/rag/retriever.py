import logging
from typing import Any

# Configure module-level logger
logger = logging.getLogger(__name__)

class MedicalRetriever:
    """
    Acts as the bridge between a user's natural language query and the vector database.
    
    Responsibilities:
    1. Embed the raw text query using the injected embedding service.
    2. Query the injected vector store for the most relevant medical chunks.
    3. Consolidate and format the retrieved chunks into a clean, readable string 
       ready for LLM prompt injection.
    """

    def __init__(
        self, 
        embedding_service: Any, 
        vector_store: Any, 
        log_level: int = logging.INFO
    ):
        """
        Initializes the MedicalRetriever with the necessary services.

        Args:
            embedding_service: An instance of MedicalEmbeddingService (or compatible) 
                               capable of embedding a query.
            vector_store: An instance of MedicalVectorStore (or compatible) 
                          capable of searching by vector.
            log_level: The logging level to use. Defaults to logging.INFO.
        """
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        logger.setLevel(log_level)

        self.embedding_service = embedding_service
        self.vector_store = vector_store
        
        logger.info("MedicalRetriever initialized with injected embedding and vector store services.")

    def retrieve_context(self, query: str, n_results: int = 5) -> str:
        """
        Takes a raw text question, retrieves relevant medical context, and formats it.

        Args:
            query: The raw text question from the doctor or patient.
            n_results: The maximum number of relevant chunks to retrieve.

        Returns:
            A consolidated string of medical context, or a standard message if nothing is found.
        """
        if not query or not query.strip():
            logger.warning("Empty query provided to retriever. Returning empty context.")
            return "No context found."

        logger.info(f"Retrieving context for query: '{query}' (max results: {n_results})")

        try:
            # 1. Embed the query
            query_vector = self.embedding_service.embed_query(query)
            
            if not query_vector:
                logger.warning("Embedding service returned an empty vector. Returning no context.")
                return "No context found."

            # 2. Search the vector store
            results = self.vector_store.search_by_vector(query_vector, n_results=n_results)

            if not results:
                logger.info("No relevant context found in the vector store for the given query.")
                return "No context found."

            # 3. Format the results into a highly readable string for an LLM
            context_blocks = []
            
            for i, res in enumerate(results):
                content = res.get("content", "").strip()
                metadata = res.get("metadata", {})
                
                if not content:
                    continue
                    
                filename = metadata.get("filename", "Unknown Source")
                page = metadata.get("page_number", "N/A")
                
                # Create a clean block for this chunk
                block = (
                    f"--- Context {i+1} ---\n"
                    f"Source: {filename} (Page {page})\n"
                    f"Content:\n{content}\n"
                )
                context_blocks.append(block)

            if not context_blocks:
                return "No context found."

            # Join all blocks with double newlines to separate them clearly
            final_context = "\n".join(context_blocks)
            
            logger.info(f"Successfully retrieved and formatted {len(context_blocks)} chunks of context.")
            return final_context

        except Exception as e:
            logger.error(f"Error during context retrieval: {str(e)}")
            # Even on failure, we return a safe string rather than crashing the LLM pipeline
            return "No context found due to an internal retrieval error."
