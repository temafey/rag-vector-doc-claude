"""
PDF file parser.
"""
from typing import List, Dict, Any
import os
import io

# This requires PyPDF2 package
from PyPDF2 import PdfReader

from app.infrastructure.parsers.parser_factory import DocumentParser

class PdfParser(DocumentParser):
    """Parser for PDF files."""
    
    def can_parse(self, file_path: str) -> bool:
        """
        Check if parser can handle PDF files.
        
        Args:
            file_path: Path to the file
            
        Returns:
            True if file extension is .pdf, False otherwise
        """
        return file_path.lower().endswith('.pdf')
        
    def parse(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Parse PDF file into list of documents.
        
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
                            "total_pages": len(reader.pages)
                        }
                        
                        # Add PDF metadata
                        metadata.update(pdf_info)
                        
                        documents.append({
                            "content": text,
                            "metadata": metadata
                        })
                    except Exception as e:
                        # If a page fails, log it and continue
                        print(f"Error extracting text from page {page_num + 1}: {str(e)}")
                
                # If no pages were extracted successfully, raise an error
                if not documents:
                    raise ValueError("No text could be extracted from any page")
                    
        except Exception as e:
            raise ValueError(f"Error parsing PDF file {file_path}: {str(e)}")
        
        return documents
