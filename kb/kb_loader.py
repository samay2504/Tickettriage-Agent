"""
Knowledge Base loader and manager.
Loads KB entries from JSON file.
"""

import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class KBEntry:
    """Knowledge Base entry."""
    
    def __init__(self, entry_dict: Dict[str, Any]):
        self.id: str = entry_dict.get("id", "")
        self.title: str = entry_dict.get("title", "")
        self.category: str = entry_dict.get("category", "Other")
        self.symptoms: List[str] = entry_dict.get("symptoms", [])
        self.snippet: str = entry_dict.get("snippet", "")
        self.recommended_action: str = entry_dict.get("recommended_action", "")
        self.full_text: str = entry_dict.get("full_text", "")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "title": self.title,
            "category": self.category,
            "symptoms": self.symptoms,
            "snippet": self.snippet,
            "recommended_action": self.recommended_action,
            "full_text": self.full_text,
        }


class KBLoader:
    """Load and manage knowledge base."""
    
    def __init__(self, kb_path: str):
        self.kb_path = Path(kb_path)
        self.entries: List[KBEntry] = []
        self._load_kb()
    
    def _load_kb(self):
        """Load KB from JSON file."""
        if not self.kb_path.exists():
            logger.warning(f"KB file not found: {self.kb_path}")
            self.entries = []
            return
        
        try:
            with open(self.kb_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            if isinstance(data, list):
                self.entries = [KBEntry(entry) for entry in data]
            else:
                logger.error(f"KB file is not a list: {self.kb_path}")
                self.entries = []
            
            logger.info(f"Loaded {len(self.entries)} KB entries from {self.kb_path}")
        except Exception as e:
            logger.error(f"Failed to load KB: {e}")
            self.entries = []
    
    def get_entries(self) -> List[KBEntry]:
        """Get all KB entries."""
        return self.entries
    
    def get_entry_by_id(self, entry_id: str) -> Optional[KBEntry]:
        """Get KB entry by ID."""
        for entry in self.entries:
            if entry.id == entry_id:
                return entry
        return None
    
    def reload(self):
        """Reload KB from file."""
        self._load_kb()
