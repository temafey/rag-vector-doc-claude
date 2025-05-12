"""
Enhanced PDF file parser with OCR support.
"""
from typing import List, Dict, Any, Optional, Tuple
import os
import io
import tempfile
import logging
import concurrent.futures
from pathlib import Path

# Required packages
from PyPDF2 import PdfReader
import fitz  # PyMuPDF
import pytesseract
from PIL import Image
import numpy as np

from app.infrastructure.parsers.parser_factory import DocumentParser
from app.config.config_loader import get_config

# Setup logging
logger = logging.getLogger(__name__)

class PdfParser(DocumentParser):
    """Enhanced parser for PDF files with OCR support."""
    
    def __init__(self):
        """Initialize PDF parser."""
        self.config = get_config()
        
        # Get OCR configuration
        self.enable_ocr = self.config.get("pdf_parser", {}).get("enable_ocr", True)
        self.ocr_language = self.config.get("pdf_parser", {}).get("ocr_language", "eng+rus")
        self.min_text_length = self.config.get("pdf_parser", {}).get("min_text_length", 100)
        self.ocr_dpi = self.config.get("pdf_parser", {}).get("ocr_dpi", 300)
        self.max_workers = self.config.get("pdf_parser", {}).get("max_workers", 4)
        
        # Initialize thread pool for parallel OCR
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers)
        
        # Try to set up tesseract path from config
        tesseract_path = self.config.get("pdf_parser", {}).get("tesseract_path", None)
        if tesseract_path:
            pytesseract.pytesseract.tesseract_cmd = tesseract_path
        
        # Verify tesseract is available
        try:
            pytesseract.get_tesseract_version()
            self.ocr_available = True
        except:
            logger.warning("Tesseract not available. OCR will be disabled.")
            self.ocr_available = False
            self.enable_ocr = False
    
    def can_parse(self, file_path: str) -> bool:
        """
        Check if parser can handle PDF files.
        
        Args:
            file_path: Path to the file
            
        Returns:
            True if file extension is .pdf, False otherwise
        """
        return file_path.lower().endswith('.pdf')
    
    def extract_text_with_ocr(self, image: Image.Image, language: str = "eng+rus") -> str:
        """
        Extract text from image using OCR.
        
        Args:
            image: PIL Image
            language: OCR language(s)
            
        Returns:
            Extracted text
        """
        if not self.ocr_available:
            return ""
        
        try:
            # Perform OCR
            text = pytesseract.image_to_string(image, lang=language)
            return text
        except Exception as e:
            logger.error(f"OCR error: {str(e)}")
            return ""
    
    def extract_text_from_page(self, page: fitz.Page, page_num: int, enable_ocr: bool = True) -> str:
        """
        Extract text from PDF page with optional OCR.
        
        Args:
            page: PyMuPDF page object
            page_num: Page number for logging
            enable_ocr: Whether to use OCR if needed
            
        Returns:
            Extracted text
        """
        # First try to extract text directly
        text = page.get_text()
        
        # If text extraction failed or returned very little text, try OCR
        if enable_ocr and self.ocr_available and len(text.strip()) < self.min_text_length:
            try:
                # Render page as image
                pix = page.get_pixmap(matrix=fitz.Matrix(self.ocr_dpi/72, self.ocr_dpi/72))
                
                # Convert to PIL Image
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                
                # Perform OCR
                ocr_text = self.extract_text_with_ocr(img, self.ocr_language)
                
                # Combine texts if both available
                if text.strip() and ocr_text.strip():
                    combined_text = text + "\n\n" + ocr_text
                    return combined_text
                
                # Return OCR text if it's better
                if len(ocr_text.strip()) > len(text.strip()):
                    return ocr_text
            except Exception as e:
                logger.error(f"Error in OCR for page {page_num}: {str(e)}")
        
        return text
    
    def parse_with_pymupdf(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Parse PDF using PyMuPDF with OCR support.
        
        Args:
            file_path: Path to the PDF file
            
        Returns:
            List of documents, each page as a separate document
        """
        documents = []
        
        try:
            # Open the PDF file
            pdf_document = fitz.open(file_path)
            
            # Extract document metadata
            metadata = pdf_document.metadata
            pdf_info = {}
            
            if metadata:
                for key in ["title", "author", "subject", "creator", "producer", "keywords"]:
                    if key in metadata and metadata[key]:
                        pdf_info[f'pdf_{key}'] = metadata[key]
            
            # Process each page in parallel if OCR is enabled
            if self.enable_ocr and self.ocr_available and pdf_document.page_count > 1:
                # Prepare arguments for parallel processing
                page_args = [(pdf_document[i], i) for i in range(pdf_document.page_count)]
                
                # Extract text in parallel
                with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                    page_texts = list(executor.map(
                        lambda args: self.extract_text_from_page(args[0], args[1], self.enable_ocr), 
                        page_args
                    ))
                
                # Create documents from extracted texts
                for i, text in enumerate(page_texts):
                    if not text.strip():
                        continue
                    
                    metadata = {
                        "source_file": os.path.basename(file_path),
                        "file_type": "pdf",
                        "page_number": i + 1,
                        "total_pages": pdf_document.page_count
                    }
                    
                    # Add PDF metadata
                    metadata.update(pdf_info)
                    
                    # Add processing info
                    if self.enable_ocr and self.ocr_available:
                        metadata["processing"] = "ocr_enabled"
                    
                    documents.append({
                        "content": text,
                        "metadata": metadata
                    })
            else:
                # Process pages sequentially
                for i in range(pdf_document.page_count):
                    page = pdf_document[i]
                    text = self.extract_text_from_page(page, i, self.enable_ocr)
                    
                    if not text.strip():
                        continue
                    
                    metadata = {
                        "source_file": os.path.basename(file_path),
                        "file_type": "pdf",
                        "page_number": i + 1,
                        "total_pages": pdf_document.page_count
                    }
                    
                    # Add PDF metadata
                    metadata.update(pdf_info)
                    
                    # Add processing info
                    if self.enable_ocr and self.ocr_available:
                        metadata["processing"] = "ocr_enabled"
                    
                    documents.append({
                        "content": text,
                        "metadata": metadata
                    })
            
            pdf_document.close()
            
        except Exception as e:
            logger.error(f"Error parsing PDF with PyMuPDF: {str(e)}")
            # Try fallback to PyPDF2
            return self.parse_with_pypdf2(file_path)
        
        return documents
    
    def parse_with_pypdf2(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Parse PDF using PyPDF2 as fallback method.
        
        Args:
            file_path: Path to the PDF file
            
        Returns:
            List of documents, each page as a separate document
        """
        documents = []
        
        try:
            # Open the PDF file
            with open(file_path, 'rb') as file:
                reader = PdfReader(file)
                
                # Extract metadata from PDF
                info = reader.metadata
                pdf_info = {}
                
                if info:
                    if info.title:
                        pdf_info['pdf_title'] = info.title
                    if info.author:
                        pdf_info['pdf_author'] = info.author
                    if info.creator:
                        pdf_info['pdf_creator'] = info.creator
                    if info.producer:
                        pdf_info['pdf_producer'] = info.producer
                    if info.subject:
                        pdf_info['pdf_subject'] = info.subject
                
                # Extract text from each page
                for page_num, page in enumerate(reader.pages):
                    try:
                        text = page.extract_text()
                        
                        # Skip empty pages
                        if not text.strip():
                            continue
                            
                        # Create metadata for this page
                        metadata = {
                            "source_file": os.path.basename(file_path),
                            "file_type": "pdf",
                            "page_number": page_num + 1,
                            "total_pages": len(reader.pages),
                            "processing": "pypdf2"
                        }
                        
                        # Add PDF metadata
                        metadata.update(pdf_info)
                        
                        documents.append({
                            "content": text,
                            "metadata": metadata
                        })
                    except Exception as e:
                        logger.error(f"Error extracting text from page {page_num + 1}: {str(e)}")
                
        except Exception as e:
            logger.error(f"Error parsing PDF with PyPDF2: {str(e)}")
            raise ValueError(f"Error parsing PDF file {file_path}: {str(e)}")
        
        return documents
    
    def parse(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Parse PDF file into list of documents with OCR support.
        
        Args:
            file_path: Path to the PDF file
            
        Returns:
            List of documents, each page as a separate document
        """
        # Try parsing with PyMuPDF first (better text extraction + OCR)
        try:
            documents = self.parse_with_pymupdf(file_path)
            
            # If no documents were extracted, fall back to PyPDF2
            if not documents:
                logger.info(f"No content extracted with PyMuPDF, falling back to PyPDF2 for {file_path}")
                documents = self.parse_with_pypdf2(file_path)
        except Exception as e:
            # If PyMuPDF fails, try PyPDF2
            logger.warning(f"PyMuPDF failed, falling back to PyPDF2 for {file_path}: {str(e)}")
            documents = self.parse_with_pypdf2(file_path)
        
        # Check if we got any content
        if not documents:
            raise ValueError(f"No text could be extracted from {file_path}")
        
        return documents
    
    def get_pdf_toc(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Extract table of contents from PDF file.
        
        Args:
            file_path: Path to the PDF file
            
        Returns:
            List of TOC entries with title, level, and page number
        """
        toc = []
        
        try:
            # Open the PDF file with PyMuPDF
            pdf_document = fitz.open(file_path)
            
            # Get table of contents
            toc_data = pdf_document.get_toc()
            
            # Convert to more readable format
            for entry in toc_data:
                level, title, page = entry
                toc.append({
                    "level": level,
                    "title": title,
                    "page": page
                })
            
            pdf_document.close()
            
        except Exception as e:
            logger.error(f"Error extracting TOC: {str(e)}")
        
        return toc
    
    def extract_text_by_section(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Extract text by sections defined in table of contents instead of pages.
        
        Args:
            file_path: Path to the PDF file
            
        Returns:
            List of documents, each section as a separate document
        """
        # First try to get table of contents
        toc = self.get_pdf_toc(file_path)
        
        # If no TOC, fall back to regular page parsing
        if not toc:
            logger.info(f"No TOC found in {file_path}, using regular page parsing")
            return self.parse(file_path)
        
        try:
            # Open the PDF file
            pdf_document = fitz.open(file_path)
            
            # Extract document metadata
            metadata = pdf_document.metadata
            pdf_info = {}
            
            if metadata:
                for key in ["title", "author", "subject", "creator", "producer", "keywords"]:
                    if key in metadata and metadata[key]:
                        pdf_info[f'pdf_{key}'] = metadata[key]
            
            # Process sections
            documents = []
            
            # Add section pages
            section_pages = []
            for i, entry in enumerate(toc):
                start_page = entry["page"] - 1  # PyMuPDF uses 0-based page numbers
                
                # Determine end page
                if i < len(toc) - 1:
                    end_page = toc[i+1]["page"] - 1
                else:
                    end_page = pdf_document.page_count - 1
                
                section_pages.append((entry["title"], entry["level"], start_page, end_page))
            
            # Extract text from each section
            for title, level, start_page, end_page in section_pages:
                text = ""
                
                # Combine text from all pages in the section
                for page_num in range(start_page, end_page + 1):
                    page_text = self.extract_text_from_page(pdf_document[page_num], page_num, self.enable_ocr)
                    text += page_text + "\n\n"
                
                # Skip empty sections
                if not text.strip():
                    continue
                
                metadata = {
                    "source_file": os.path.basename(file_path),
                    "file_type": "pdf",
                    "section_title": title,
                    "section_level": level,
                    "start_page": start_page + 1,
                    "end_page": end_page + 1,
                    "total_pages": pdf_document.page_count
                }
                
                # Add PDF metadata
                metadata.update(pdf_info)
                
                # Add processing info
                if self.enable_ocr and self.ocr_available:
                    metadata["processing"] = "ocr_enabled"
                
                documents.append({
                    "content": text,
                    "metadata": metadata
                })
            
            pdf_document.close()
            
            # If no sections were processed, fall back to regular page parsing
            if not documents:
                logger.info(f"No sections processed in {file_path}, using regular page parsing")
                return self.parse(file_path)
            
            return documents
            
        except Exception as e:
            logger.error(f"Error extracting sections: {str(e)}")
            # Fall back to regular page parsing
            return self.parse(file_path)
