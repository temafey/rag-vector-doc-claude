"""
Tests for TextSplitter service.
"""
import pytest
from app.domain.services.text_splitter import TextSplitter

class TestTextSplitter:
    """Test cases for TextSplitter."""
    
    def test_split_text_short(self, text_splitter):
        """Test splitting short text that fits in a single chunk."""
        text = "This is a short text that should fit in a single chunk."
        chunk_size = 100
        chunks = text_splitter.split_text(text, chunk_size=chunk_size)
        
        assert len(chunks) == 1
        assert chunks[0] == text
    
    def test_split_text_long(self, text_splitter):
        """Test splitting long text into multiple chunks."""
        # Create a long text with multiple paragraphs
        paragraphs = ["Paragraph " + str(i) * 50 for i in range(1, 6)]
        text = "\n\n".join(paragraphs)
        
        chunk_size = 100
        chunk_overlap = 20
        chunks = text_splitter.split_text(text, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        
        # Check that text was split into multiple chunks
        assert len(chunks) > 1
        
        # Check that all text is included in chunks
        combined_text = " ".join([chunk.strip() for chunk in chunks])
        for paragraph in paragraphs:
            assert paragraph.strip() in combined_text
    
    def test_split_text_with_overlap(self, text_splitter):
        """Test that chunks have proper overlap."""
        # Create a text with clearly identifiable parts
        parts = ["Part A: " + "A" * 50, "Part B: " + "B" * 50, "Part C: " + "C" * 50]
        text = " ".join(parts)
        
        chunk_size = 70
        chunk_overlap = 30
        chunks = text_splitter.split_text(text, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        
        # Check that we have overlap
        assert len(chunks) >= 3
        
        # Check for overlap content
        found_overlap = False
        for i in range(len(chunks) - 1):
            chunk_end = chunks[i][-20:]  # Last 20 chars of current chunk
            next_chunk_start = chunks[i+1][:20]  # First 20 chars of next chunk
            
            # Look for some common content
            for j in range(min(len(chunk_end), len(next_chunk_start)) - 5):
                if chunk_end[j:j+5] in next_chunk_start:
                    found_overlap = True
                    break
            
            if found_overlap:
                break
        
        assert found_overlap, "Could not find overlap between chunks"
    
    def test_split_text_by_semantic(self, text_splitter):
        """Test splitting text by semantic boundaries."""
        text = """# Introduction
        
        This is the introduction section. It provides context for the document.
        
        # Method
        
        The method section explains the approach used. It has multiple sentences.
        
        # Results
        
        The results section presents findings. It is important.
        
        # Conclusion
        
        The conclusion summarizes key points."""
        
        chunks = text_splitter.split_text_by_semantic(text, chunk_size=200)
        
        # Check that headings are preserved at start of chunks
        headings = ["# Introduction", "# Method", "# Results", "# Conclusion"]
        found_headings = []
        
        for chunk in chunks:
            for heading in headings:
                if heading in chunk:
                    found_headings.append(heading)
                    break
        
        # Assert that we found at least some of the headings
        assert len(found_headings) >= 2, "Semantic splitting did not preserve headings"
    
    def test_split_code(self, text_splitter):
        """Test splitting code while preserving function boundaries."""
        code = """
        def function_one():
            # This is the first function
            print("Function one")
            return True
            
        def function_two(param):
            # This is the second function
            result = param * 2
            print(f"Function two: {result}")
            return result
            
        class TestClass:
            def method_one(self):
                return "Method one"
                
            def method_two(self):
                return "Method two"
        """
        
        chunks = text_splitter.split_code(code, chunk_size=200)
        
        # Check that functions and classes are preserved
        markers = ["def function_one", "def function_two", "class TestClass"]
        for marker in markers:
            found = False
            for chunk in chunks:
                if marker in chunk:
                    found = True
                    break
            assert found, f"Code splitter did not preserve code structure: {marker} not found"
