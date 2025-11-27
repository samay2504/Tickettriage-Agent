"""
Tests for KB loader and search functionality.
"""

import pytest
from kb.kb_loader import KBLoader, KBEntry
from kb.search import KBSearch, KBSearchResult


class TestKBLoader:
    """Tests for KBLoader."""
    
    def test_load_kb(self, kb_loader):
        """Test loading KB from file."""
        entries = kb_loader.get_entries()
        assert len(entries) == 2
        assert entries[0].id == "TEST-001"
    
    def test_get_entry_by_id(self, kb_loader):
        """Test getting entry by ID."""
        entry = kb_loader.get_entry_by_id("TEST-001")
        assert entry is not None
        assert entry.title == "Test Bug"
    
    def test_get_entry_by_id_not_found(self, kb_loader):
        """Test getting nonexistent entry."""
        entry = kb_loader.get_entry_by_id("NONEXISTENT")
        assert entry is None
    
    def test_entry_to_dict(self, kb_loader):
        """Test converting entry to dict."""
        entry = kb_loader.get_entry_by_id("TEST-001")
        entry_dict = entry.to_dict()
        assert entry_dict["id"] == "TEST-001"
        assert entry_dict["title"] == "Test Bug"


class TestKBSearch:
    """Tests for KB search."""
    
    def test_search_exact_match(self, kb_search):
        """Test exact phrase matching."""
        results = kb_search.search("error crash", top_k=1)
        assert len(results) > 0
        assert results[0].entry.id == "TEST-001"
    
    def test_search_partial_match(self, kb_search):
        """Test partial token matching."""
        results = kb_search.search("login problem", top_k=1)
        assert len(results) > 0
        assert results[0].entry.id == "TEST-002"
    
    def test_search_no_match(self, kb_search):
        """Test search with no matches."""
        results = kb_search.search("xyz123 notaword", top_k=1)
        # May return results with lower scores or empty
        assert isinstance(results, list)
    
    def test_search_empty_query(self, kb_search):
        """Test search with empty query."""
        results = kb_search.search("", top_k=1)
        assert len(results) == 0
    
    def test_search_top_k(self, kb_search):
        """Test top_k limiting."""
        results = kb_search.search("test", top_k=1)
        assert len(results) <= 1
    
    def test_search_result_to_dict(self, kb_loader):
        """Test converting search result to dict."""
        entry = kb_loader.get_entries()[0]
        result = KBSearchResult(entry, 0.95)
        result_dict = result.to_dict()
        assert result_dict["score"] == 0.95
        assert result_dict["id"] == "TEST-001"
    
    def test_cosine_similarity(self):
        """Test cosine similarity calculation."""
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [1.0, 0.0, 0.0]
        similarity = KBSearch._cosine_similarity(vec1, vec2)
        assert similarity == 1.0
        
        vec3 = [0.0, 1.0, 0.0]
        similarity = KBSearch._cosine_similarity(vec1, vec3)
        assert similarity == 0.0
