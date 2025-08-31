"""Manage mappings between spreadsheets and command files for auto-execution."""

import os, json, hashlib
from datetime import datetime
from typing import Optional, Dict, List

class MappingManager:
    """Manage mappings between spreadsheets and command files."""
    
    def __init__(self, mappings_dir: str = "src/mappings/data"):
        """Initialize with mappings storage directory."""
        self.mappings_dir = mappings_dir
        self.mappings_file = os.path.join(mappings_dir, "spreadsheet_command_mappings.json")

        os.makedirs(mappings_dir, exist_ok=True)
        if not os.path.exists(self.mappings_file):
            self._initialize_mappings_file()
    
    def _initialize_mappings_file(self) -> None:
        """Create mappings file with empty structure."""
        initial_data = {
            "mappings": [],
            "created_at": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat(),
            "version": "1.0"
        }
        with open(self.mappings_file, 'w', encoding='utf-8') as f:
            json.dump(initial_data, f, indent=2, ensure_ascii=False)
    
    def _load_mappings(self) -> Dict:
        """Load mappings JSON from disk."""
        try:
            with open(self.mappings_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self._initialize_mappings_file()
            return self._load_mappings()
    
    def _save_mappings(self, data: Dict) -> None:
        """Persist mappings JSON to disk with updated timestamp."""
        data["last_updated"] = datetime.now().isoformat()
        with open(self.mappings_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def _generate_spreadsheet_hash(self, filename: str, file_content: Optional[bytes] = None) -> str:
        """Return hash id based on filename and optionally content."""
        if file_content:
            # Hash based on content for more accuracy
            hasher = hashlib.md5()
            hasher.update(file_content)
            content_hash = hasher.hexdigest()[:8]
            return f"{filename}_{content_hash}"
        else:
            # Hash based on filename only
            hasher = hashlib.md5()
            hasher.update(filename.encode('utf-8'))
            return f"{filename}_{hasher.hexdigest()[:8]}"
    
    def create_mapping(self, spreadsheet_filename: str, command_filename: str, 
                      commands: List[str], spreadsheet_content: Optional[bytes] = None) -> str:
        """Create a mapping record and return its ID."""
        data = self._load_mappings()
        
        # Generate unique mapping ID
        mapping_id = f"map_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{len(data['mappings']) + 1}"
        
        # Generate spreadsheet hash
        spreadsheet_hash = self._generate_spreadsheet_hash(spreadsheet_filename, spreadsheet_content)
        
        # Create mapping entry
        mapping = {
            "mapping_id": mapping_id,
            "spreadsheet_filename": spreadsheet_filename,
            "spreadsheet_hash": spreadsheet_hash,
            "command_filename": command_filename,
            "commands": commands,
            "command_count": len(commands),
            "created_at": datetime.now().isoformat(),
            "last_used": None,
            "use_count": 0,
            "is_active": True
        }
        
        data["mappings"].append(mapping)
        self._save_mappings(data)
        
        return mapping_id
    
    def find_mapping_by_spreadsheet(self, spreadsheet_filename: str, 
                                   spreadsheet_content: Optional[bytes] = None) -> Optional[Dict]:
        """Find and return mapping for a spreadsheet if present."""
        data = self._load_mappings()
        spreadsheet_hash = self._generate_spreadsheet_hash(spreadsheet_filename, spreadsheet_content)
        
        # First try to match by hash (most accurate)
        for mapping in data["mappings"]:
            if mapping["is_active"] and mapping["spreadsheet_hash"] == spreadsheet_hash:
                return mapping
        
        # Fallback: match by filename only
        for mapping in data["mappings"]:
            if mapping["is_active"] and mapping["spreadsheet_filename"] == spreadsheet_filename:
                return mapping
        
        return None
    
    def get_all_mappings(self) -> List[Dict]:
        """Return all mappings."""
        data = self._load_mappings()
        return data["mappings"]
    
    def get_active_mappings(self) -> List[Dict]:
        """Return only active mappings."""
        data = self._load_mappings()
        return [mapping for mapping in data["mappings"] if mapping["is_active"]]
    
    def update_mapping(self, mapping_id: str, **kwargs) -> bool:
        """Update mapping fields; return True if updated, else False."""
        data = self._load_mappings()
        
        for mapping in data["mappings"]:
            if mapping["mapping_id"] == mapping_id:
                mapping.update(kwargs)
                mapping["last_updated"] = datetime.now().isoformat()
                self._save_mappings(data)
                return True
        
        return False
    
    def delete_mapping(self, mapping_id: str) -> bool:
        """Mark a mapping as inactive; return True if successful."""
        return self.update_mapping(mapping_id, is_active=False)
    
    def increment_use_count(self, mapping_id: str):
        """Increment the use count for a mapping."""
        self.update_mapping(
            mapping_id, 
            use_count=self.get_mapping_by_id(mapping_id)["use_count"] + 1,
            last_used=datetime.now().isoformat()
        )
    
    def get_mapping_by_id(self, mapping_id: str) -> Optional[Dict]:
        """Return a specific mapping by ID, if present."""
        data = self._load_mappings()
        for mapping in data["mappings"]:
            if mapping["mapping_id"] == mapping_id:
                return mapping
        return None
    
    def get_commands_for_spreadsheet(self, spreadsheet_filename: str, 
                                   spreadsheet_content: Optional[bytes] = None) -> Optional[List[str]]:
        """Return command list for spreadsheet if mapping exists, else None."""
        mapping = self.find_mapping_by_spreadsheet(spreadsheet_filename, spreadsheet_content)
        if mapping:
            self.increment_use_count(mapping["mapping_id"])
            return mapping["commands"]
        return None
    
    def get_mapping_stats(self) -> Dict:
        """Return basic statistics about mappings."""
        data = self._load_mappings()
        active_mappings = [m for m in data["mappings"] if m["is_active"]]
        
        return {
            "total_mappings": len(data["mappings"]),
            "active_mappings": len(active_mappings),
            "inactive_mappings": len(data["mappings"]) - len(active_mappings),
            "total_commands": sum(m["command_count"] for m in active_mappings),
            "total_uses": sum(m["use_count"] for m in data["mappings"]),
            "last_updated": data.get("last_updated"),
            "created_at": data.get("created_at")
        }
    
    def check_spreadsheet_conflicts(self, spreadsheet_filename: str) -> List[Dict]:
        """Return active mappings that share the same spreadsheet filename."""
        data = self._load_mappings()
        conflicts = []
        
        for mapping in data["mappings"]:
            if (mapping["is_active"] and 
                mapping["spreadsheet_filename"].lower() == spreadsheet_filename.lower()):
                conflicts.append(mapping)
        
        return conflicts
