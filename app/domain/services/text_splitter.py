"""
Service for splitting text into chunks.
"""
from typing import List
import re

class TextSplitter:
    """Service for splitting text into chunks."""
    
    def split_text(self, text: str, chunk_size: int = 1000, chunk_overlap: int = 200) -> List[str]:
        """
        Split text into chunks of specified size with overlap.
        
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
        
        # Split text into paragraphs
        paragraphs = re.split(r'\n\s*\n', text)
        
        chunks = []
        current_chunk = []
        current_size = 0
        
        for paragraph in paragraphs:
            # Skip empty paragraphs
            if not paragraph.strip():
                continue
            
            paragraph_size = len(paragraph)
            
            # If paragraph is larger than chunk size, split it into sentences
            if paragraph_size > chunk_size:
                sentences = re.split(r'(?<=[.!?])\s+', paragraph)
                for sentence in sentences:
                    sentence_size = len(sentence)
                    
                    # If sentence is larger than chunk size, add it as a separate chunk
                    if sentence_size > chunk_size:
                        # If there's text in current chunk, add it to chunks list
                        if current_size > 0:
                            chunks.append('\n\n'.join(current_chunk))
                            current_chunk = []
                            current_size = 0
                        
                        # Split large sentence into parts
                        for i in range(0, sentence_size, chunk_size - chunk_overlap):
                            chunks.append(sentence[i:i + chunk_size])
                    else:
                        # If adding sentence would exceed chunk size,
                        # finalize current chunk and start a new one
                        if current_size + sentence_size > chunk_size:
                            chunks.append('\n\n'.join(current_chunk))
                            # Save part of text for next chunk (overlap)
                            overlap_size = min(chunk_overlap, current_size)
                            if overlap_size > 0:
                                # Take last sentences for overlap
                                last_paragraphs = []
                                overlap_counter = 0
                                for i in range(len(current_chunk) - 1, -1, -1):
                                    last_paragraphs.insert(0, current_chunk[i])
                                    overlap_counter += len(current_chunk[i])
                                    if overlap_counter >= overlap_size:
                                        break
                                
                                current_chunk = last_paragraphs
                                current_size = overlap_counter
                            else:
                                current_chunk = []
                                current_size = 0
                        
                        current_chunk.append(sentence)
                        current_size += sentence_size
            else:
                # If adding paragraph would exceed chunk size,
                # finalize current chunk and start a new one
                if current_size + paragraph_size > chunk_size:
                    chunks.append('\n\n'.join(current_chunk))
                    # Save part of text for next chunk (overlap)
                    overlap_size = min(chunk_overlap, current_size)
                    if overlap_size > 0:
                        # Take last paragraphs for overlap
                        last_paragraphs = []
                        overlap_counter = 0
                        for i in range(len(current_chunk) - 1, -1, -1):
                            last_paragraphs.insert(0, current_chunk[i])
                            overlap_counter += len(current_chunk[i])
                            if overlap_counter >= overlap_size:
                                break
                        
                        current_chunk = last_paragraphs
                        current_size = overlap_counter
                    else:
                        current_chunk = []
                        current_size = 0
                
                current_chunk.append(paragraph)
                current_size += paragraph_size
        
        # Add last chunk if it exists
        if current_size > 0:
            chunks.append('\n\n'.join(current_chunk))
        
        return chunks
