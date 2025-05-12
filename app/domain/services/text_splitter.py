"""
Service for splitting text into chunks.
"""
from typing import List
import re
from langchain.text_splitter import RecursiveCharacterTextSplitter

class TextSplitter:
    """Service for splitting text into chunks."""
    
    def split_text(self, text: str, chunk_size: int = 1000, chunk_overlap: int = 200) -> List[str]:
        """
        Split text into chunks of specified size with overlap using LangChain's splitter.
        
        Args:
            text: Source text
            chunk_size: Chunk size in characters
            chunk_overlap: Overlap size between chunks
            
        Returns:
            List of text chunks
        """
        # If text is shorter than chunk size, return it as a single chunk
        if len(text) <= chunk_size:
            return [text]
        
        # Use LangChain's RecursiveCharacterTextSplitter for better performance
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
        
        return text_splitter.split_text(text)
    
    def split_text_by_semantic(self, text: str, chunk_size: int = 1000, chunk_overlap: int = 200) -> List[str]:
        """
        Split text into chunks with respect to semantic boundaries.
        
        Args:
            text: Source text
            chunk_size: Chunk size in characters
            chunk_overlap: Overlap size between chunks
            
        Returns:
            List of text chunks
        """
        # First try to split by headings and paragraphs
        heading_pattern = re.compile(r'^#+\s+.+$|^.+\n[-=]+$', re.MULTILINE)
        headings = list(heading_pattern.finditer(text))
        
        # If there are enough headings, use them as boundaries
        if len(headings) > 1:
            chunks = []
            for i in range(len(headings)):
                start = headings[i].start()
                end = headings[i + 1].start() if i < len(headings) - 1 else len(text)
                
                section = text[start:end]
                
                # If section is larger than chunk size, split it further
                if len(section) > chunk_size:
                    section_chunks = self.split_text(section, chunk_size, chunk_overlap)
                    chunks.extend(section_chunks)
                else:
                    chunks.append(section)
            
            return chunks
        
        # Fallback to regular splitting
        return self.split_text(text, chunk_size, chunk_overlap)
    
    def split_code(self, code: str, chunk_size: int = 1000, chunk_overlap: int = 200) -> List[str]:
        """
        Split code into chunks, preserving function and class boundaries where possible.
        
        Args:
            code: Source code
            chunk_size: Maximum chunk size in characters
            chunk_overlap: Overlap size between chunks
            
        Returns:
            List of code chunks
        """
        # Split code by function or class definitions
        import re
        
        # Patterns for function and class definitions
        patterns = [
            r'(def\s+\w+\s*\([^)]*\)\s*:.*?)(?=\n\s*def|\n\s*class|\Z)',  # Python functions
            r'(class\s+\w+.*?)(?=\n\s*def|\n\s*class|\Z)',                # Python classes
            r'(function\s+\w+\s*\([^)]*\)\s*\{.*?\n\})',                  # JavaScript functions
            r'(class\s+\w+\s*\{.*?\n\})',                                 # JavaScript classes
        ]
        
        # Try to find all code blocks
        blocks = []
        remaining_code = code
        
        for pattern in patterns:
            matches = list(re.finditer(pattern, remaining_code, re.DOTALL))
            for match in matches:
                blocks.append((match.start(), match.end(), match.group(0)))
            
            # Remove matched blocks from remaining code
            if matches:
                new_code = ""
                last_end = 0
                for _, end, _ in blocks:
                    new_code += remaining_code[last_end:end]
                    last_end = end
                new_code += remaining_code[last_end:]
                remaining_code = new_code
        
        # Add remaining code as a final block
        if remaining_code.strip():
            blocks.append((0, len(remaining_code), remaining_code))
        
        # Sort blocks by their original position
        blocks.sort()
        
        # Process blocks into chunks
        chunks = []
        current_chunk = ""
        
        for _, _, block in blocks:
            # If block is too large, split it further
            if len(block) > chunk_size:
                if current_chunk:
                    chunks.append(current_chunk)
                    current_chunk = ""
                
                # Split large block by lines to preserve as much context as possible
                lines = block.split('\n')
                temp_chunk = ""
                
                for line in lines:
                    if len(temp_chunk) + len(line) + 1 > chunk_size:
                        chunks.append(temp_chunk)
                        temp_chunk = line + '\n'
                    else:
                        temp_chunk += line + '\n'
                
                if temp_chunk:
                    current_chunk = temp_chunk
            elif len(current_chunk) + len(block) > chunk_size:
                chunks.append(current_chunk)
                current_chunk = block
            else:
                current_chunk += block
        
        if current_chunk:
            chunks.append(current_chunk)
        
        return chunks
