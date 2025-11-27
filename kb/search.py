"""
KB search module with semantic and keyword matching.
Supports embedding-based search with fallback to keyword/TF-IDF matching.
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from collections import Counter
import math

from .kb_loader import KBEntry

logger = logging.getLogger(__name__)


class KBSearchResult:
    """Result of KB search."""
    
    def __init__(self, entry: KBEntry, score: float):
        self.entry = entry
        self.score = score
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.entry.id,
            "title": self.entry.title,
            "snippet": self.entry.snippet or self.entry.full_text[:200],
            "score": round(self.score, 2),
            "category": self.entry.category,
        }


class KBSearch:
    """Knowledge base search engine."""
    
    def __init__(self, entries: List[KBEntry], embedding_model: Optional[str] = None):
        self.entries = entries
        self.embedding_model = embedding_model
        self.use_embeddings = False
        
        # Try to initialize embeddings if available
        if embedding_model:
            self._try_initialize_embeddings()
    
    def _try_initialize_embeddings(self):
        """Try to initialize embedding model."""
        try:
            from langchain.embeddings import HuggingFaceEmbeddings
            self.embeddings = HuggingFaceEmbeddings(model_name=self.embedding_model)
            self.use_embeddings = True
            logger.info(f"Initialized embeddings with model: {self.embedding_model}")
        except Exception as e:
            logger.warning(f"Failed to initialize embeddings: {e}. Using fallback keyword search.")
            self.use_embeddings = False
    
    def search(self, query: str, top_k: int = 3) -> List[KBSearchResult]:
        """Search KB entries."""
        if not query or not self.entries:
            return []
        
        if self.use_embeddings:
            return self._embedding_search(query, top_k)
        else:
            return self._keyword_search(query, top_k)
    
    def _embedding_search(self, query: str, top_k: int) -> List[KBSearchResult]:
        """Search using embeddings."""
        try:
            query_embedding = self.embeddings.embed_query(query)
            
            results = []
            for entry in self.entries:
                # Embed entry text
                entry_text = f"{entry.title} {entry.snippet} {' '.join(entry.symptoms)}"
                entry_embedding = self.embeddings.embed_query(entry_text)
                
                # Compute cosine similarity
                score = self._cosine_similarity(query_embedding, entry_embedding)
                results.append(KBSearchResult(entry, score))
            
            # Sort by score and return top_k
            results.sort(key=lambda x: x.score, reverse=True)
            return results[:top_k]
        except Exception as e:
            logger.error(f"Embedding search failed: {e}. Falling back to keyword search.")
            return self._keyword_search(query, top_k)
    
    def _keyword_search(self, query: str, top_k: int) -> List[KBSearchResult]:
        """Search using keyword and TF-IDF matching."""
        query_tokens = self._tokenize(query)
        results = []
        
        for entry in self.entries:
            # Combine entry text
            entry_text = f"{entry.title} {entry.snippet} {' '.join(entry.symptoms)}"
            entry_tokens = self._tokenize(entry_text)
            
            # Calculate BM25-like score
            score = self._compute_score(query_tokens, entry_tokens, entry)
            
            if score > 0:
                results.append(KBSearchResult(entry, score))
        
        # Sort by score and return top_k
        results.sort(key=lambda x: x.score, reverse=True)
        return results[:top_k]
    
    def _tokenize(self, text: str) -> List[str]:
        """Simple tokenization."""
        return text.lower().split()
    
    def _compute_score(self, query_tokens: List[str], entry_tokens: List[str], entry: KBEntry) -> float:
        """Compute BM25-like score for keyword search."""
        score = 0.0
        
        # Exact phrase match bonus
        query_phrase = " ".join(query_tokens)
        entry_text = " ".join(entry_tokens)
        if query_phrase in entry_text:
            score += 2.0
        
        # Token overlap with TF-IDF-like weighting
        query_counter = Counter(query_tokens)
        entry_counter = Counter(entry_tokens)
        
        for token, query_count in query_counter.items():
            if token in entry_counter:
                entry_count = entry_counter[token]
                # BM25-like formula
                token_score = query_count * entry_count / (query_count + entry_count)
                
                # Weight by position (title > symptoms > text)
                if token in entry.title.lower().split():
                    token_score *= 3.0
                elif token in " ".join(entry.symptoms).lower().split():
                    token_score *= 2.0
                
                score += token_score
        
        # Normalize by query length
        if query_tokens:
            score = score / len(query_tokens)
        
        return score
    
    @staticmethod
    def _cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
        """Compute cosine similarity between two vectors."""
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        magnitude1 = math.sqrt(sum(a * a for a in vec1))
        magnitude2 = math.sqrt(sum(a * a for a in vec2))
        
        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0
        
        return dot_product / (magnitude1 * magnitude2)
