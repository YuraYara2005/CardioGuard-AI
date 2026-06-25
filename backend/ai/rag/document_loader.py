import os
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

# pyrefly: ignore [missing-import]
import fitz  # PyMuPDF

# Configure module-level logger
logger = logging.getLogger(__name__)

@dataclass
class DocumentPage:
    """
    Represents a single page extracted from a medical document.
    Ensures a standardized data structure for downstream tasks.
    """
    page_content: str
    metadata: Dict[str, Any]


class MedicalDocumentLoader:
    """
    A loader for medical PDF documents (e.g., AHA/ESC cardiology guidelines).
    
    This class has a single responsibility: loading files from the local file system,
    extracting the raw text, and capturing basic metadata. It does not handle
    chunking, embeddings, or VectorDB operations.
    """

    def __init__(self, log_level: int = logging.INFO):
        """
        Initializes the MedicalDocumentLoader.

        Args:
            log_level: The logging level to use. Defaults to logging.INFO.
        """
        # Ensure the logger has at least one handler to avoid "No handler found" warnings
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        logger.setLevel(log_level)

    def load_file(self, filepath: str) -> List[DocumentPage]:
        """
        Loads a single PDF file and extracts its text and metadata page by page.

        Args:
            filepath: The absolute or relative path to the PDF file.

        Returns:
            A list of DocumentPage objects, each representing an extracted page.
            Returns an empty list if the file is severely corrupted.

        Raises:
            FileNotFoundError: If the specified file does not exist.
        """
        if not os.path.exists(filepath):
            logger.error(f"File not found: {filepath}")
            raise FileNotFoundError(f"The file {filepath} does not exist.")

        if not filepath.lower().endswith('.pdf'):
            logger.warning(f"File {filepath} does not appear to have a .pdf extension.")

        pages_data: List[DocumentPage] = []
        filename = os.path.basename(filepath)
        
        logger.info(f"Starting to load document: {filepath}")

        try:
            # fitz.open manages the file resource
            with fitz.open(filepath) as doc:
                total_pages = doc.page_count
                logger.debug(f"Document {filename} opened successfully. Total pages: {total_pages}")
                
                for page_num in range(total_pages):
                    try:
                        page = doc.load_page(page_num)
                        text = page.get_text("text")
                        
                        # Retain the page even if text is empty (e.g., image-only pages) 
                        # so that downstream OCR or metadata-only processes can handle it.
                        if not text.strip():
                            logger.debug(f"Page {page_num + 1} in {filename} contains no extractable text.")
                            
                        metadata = {
                            "source": filepath,
                            "filename": filename,
                            "page_number": page_num + 1,
                            "total_pages": total_pages,
                        }
                        
                        pages_data.append(DocumentPage(page_content=text, metadata=metadata))
                        
                    except Exception as page_e:
                        # Graceful handling of individual corrupted pages without crashing the entire document load
                        logger.error(f"Error extracting text from page {page_num + 1} of {filename}: {str(page_e)}")
                        continue
                        
        except fitz.FileDataError as fde:
            logger.error(f"Corrupted or invalid PDF file: {filepath} - {str(fde)}")
        except Exception as e:
            logger.error(f"Unexpected error while opening {filepath}: {str(e)}")

        logger.info(f"Finished loading {filepath}. Successfully extracted {len(pages_data)} pages.")
        return pages_data

    def load_directory(self, directory_path: str, recursive: bool = False) -> List[DocumentPage]:
        """
        Loads all PDF files from a specified directory.

        Args:
            directory_path: The path to the directory containing PDF files.
            recursive: If True, searches subdirectories recursively.

        Returns:
            A combined list of DocumentPage objects from all successfully processed PDFs.

        Raises:
            NotADirectoryError: If the specified directory path does not exist or is not a directory.
        """
        if not os.path.exists(directory_path) or not os.path.isdir(directory_path):
            logger.error(f"Directory not found: {directory_path}")
            raise NotADirectoryError(f"The directory {directory_path} does not exist or is not a directory.")

        all_pages_data: List[DocumentPage] = []
        logger.info(f"Starting to load documents from directory: {directory_path} (recursive={recursive})")

        pdf_files = []
        if recursive:
            for root, _, files in os.walk(directory_path):
                for file in files:
                    if file.lower().endswith('.pdf'):
                        pdf_files.append(os.path.join(root, file))
        else:
            for file in os.listdir(directory_path):
                if file.lower().endswith('.pdf'):
                    file_path = os.path.join(directory_path, file)
                    if os.path.isfile(file_path):
                        pdf_files.append(file_path)

        logger.info(f"Found {len(pdf_files)} PDF file(s) in {directory_path}.")

        for file_path in pdf_files:
            try:
                pages = self.load_file(file_path)
                all_pages_data.extend(pages)
            except Exception as e:
                # Catching any top-level exceptions from load_file so one bad file doesn't crash the pipeline
                logger.error(f"Failed to process file {file_path} in directory {directory_path}: {str(e)}")
                continue

        logger.info(f"Finished loading directory {directory_path}. Total pages extracted across all files: {len(all_pages_data)}.")
        return all_pages_data
