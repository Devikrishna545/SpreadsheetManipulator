"""
Script Reuser module
------------------
Handles prompt similarity checking and script reuse functionality to save time and tokens
"""

import os
import json
import hashlib
import pickle
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
import pandas as pd
from src.controller.script_manager import ScriptManager
from src.controller.script_executor import ScriptExecutor
from src.controller.file_manager import FileManager
import logging

# Optional imports for semantic similarity
try:
    from sentence_transformers import SentenceTransformer
    from sklearn.metrics.pairwise import cosine_similarity
    import numpy as np
    SEMANTIC_SIMILARITY_AVAILABLE = True
    print("✅ ScriptReuser: Semantic similarity libraries loaded successfully")
except ImportError as e:
    print(f"⚠️ ScriptReuser: Semantic similarity libraries not available: {e}")
    print("📝 ScriptReuser: Will fall back to exact string matching")
    SEMANTIC_SIMILARITY_AVAILABLE = False
    SentenceTransformer = None
    cosine_similarity = None
    # Import numpy separately as it's needed for other operations
    try:
        import numpy as np
    except ImportError:
        print("⚠️ ScriptReuser: NumPy not available, using basic data structures")
        np = None

class ScriptReuser:
    """
    Manages script reuse based on prompt semantic similarity
    """
    
    def __init__(self, similarity_threshold: float = 1.0):
        """
        Initialize the script reuser
        
        Args:
            similarity_threshold: Minimum similarity score (0-1) for script reuse
        """
        self.similarity_threshold = similarity_threshold
        self.script_manager = ScriptManager()
        self.script_executor = ScriptExecutor()
        
        # Directory for storing prompt-script mappings
        self.mapping_dir = os.path.join('src', 'mappings', 'script')
        os.makedirs(self.mapping_dir, exist_ok=True)
        
        # File to store successful prompt-script mappings
        self.mapping_file = os.path.join(self.mapping_dir, 'prompt_script_mappings.json')
        
        # Initialize sentence transformer model for semantic similarity
        self.model = None
        if SEMANTIC_SIMILARITY_AVAILABLE:
            try:
                print("🔄 ScriptReuser: Loading semantic similarity model...")
                
                # Check for CUDA availability and configure device
                device = 'cpu'  # Default to CPU
                if SEMANTIC_SIMILARITY_AVAILABLE:
                    try:
                        import torch
                        if torch.cuda.is_available():
                            device = 'cuda'
                            print(f"✅ ScriptReuser: CUDA detected! Using GPU: {torch.cuda.get_device_name(0)}")
                        else:
                            print("⚠️ ScriptReuser: CUDA not available, using CPU")
                    except ImportError:
                        print("⚠️ ScriptReuser: PyTorch not available, using CPU")
                
                # Load model with device specification
                self.model = SentenceTransformer('all-MiniLM-L6-v2', device=device)
                print(f"✅ ScriptReuser: Semantic similarity model loaded successfully on {device.upper()}")
                
            except Exception as e:
                logging.warning(f"Failed to load sentence transformer model: {e}")
                print(f"⚠️ ScriptReuser: Failed to load semantic model - {e}")
                print("📝 ScriptReuser: Will fall back to exact string matching")
                self.model = None
        else:
            print("⚠️ ScriptReuser: Semantic similarity libraries not available")
            print("📝 ScriptReuser: Using exact string matching for script reuse")
            
        # Load existing mappings
        self.mappings = self._load_mappings()
        print(f"📊 ScriptReuser: Loaded {len(self.mappings)} existing prompt-script mappings")
        
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    def _load_mappings(self) -> List[Dict[str, Any]]:
        """
        Load existing prompt-script mappings from file
        
        Returns:
            List[Dict[str, Any]]: List of mapping dictionaries
        """
        if os.path.exists(self.mapping_file):
            try:
                with open(self.mapping_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logging.warning(f"Failed to load mappings: {e}")
                return []
        return []

    def _save_mappings(self) -> None:
        """Save current mappings to file"""
        try:
            with open(self.mapping_file, 'w', encoding='utf-8') as f:
                json.dump(self.mappings, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logging.error(f"Failed to save mappings: {e}")

    def _get_prompt_embedding(self, prompt: str) -> Optional[Any]:
        """
        Get embedding for a prompt using sentence transformer
        
        Args:
            prompt: The prompt text
            
        Returns:
            Optional[Any]: Embedding vector or None if model not available
        """
        if self.model is None or not SEMANTIC_SIMILARITY_AVAILABLE:
            return None
            
        try:
            embedding = self.model.encode([prompt])
            return embedding[0]
        except Exception as e:
            logging.warning(f"Failed to get embedding for prompt: {e}")
            return None

    def _calculate_similarity(self, embedding1: Any, embedding2: Any) -> float:
        """
        Calculate cosine similarity between two embeddings
        
        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector
            
        Returns:
            float: Similarity score between 0 and 1
        """
        if not SEMANTIC_SIMILARITY_AVAILABLE:
            return 0.0
            
        try:
            similarity = cosine_similarity([embedding1], [embedding2])[0][0]
            return float(similarity)
        except Exception as e:
            logging.warning(f"Failed to calculate similarity: {e}")
            return 0.0

    def _create_dataframe_hash(self, df: pd.DataFrame) -> str:
        """
        Create a hash of the DataFrame structure and data for compatibility checking
        
        Args:
            df: DataFrame to hash
            
        Returns:
            str: Hash string
        """
        try:
            # Create hash based on columns, dtypes, and shape with robust type handling
            structure_info = {
                'columns': [str(col) for col in df.columns],  # Ensure all columns are strings
                'dtypes': {str(col): str(dtype) for col, dtype in df.dtypes.items()},  # Ensure keys and values are strings
                'shape': [int(df.shape[0]), int(df.shape[1])]  # Ensure shape values are integers
            }
            
            # Convert to string and hash with explicit sorting for consistency
            structure_str = json.dumps(structure_info, sort_keys=True, default=str)
            return hashlib.md5(structure_str.encode('utf-8')).hexdigest()
        except Exception as e:
            logging.warning(f"Failed to create DataFrame hash: {e}")
            # Return a basic hash based on shape only as fallback
            try:
                basic_hash = f"{df.shape[0]}x{df.shape[1]}_{len(df.columns)}"
                return hashlib.md5(basic_hash.encode('utf-8')).hexdigest()
            except:
                return "fallback_hash"

    def find_similar_prompt(self, prompt: str, current_df: pd.DataFrame) -> Optional[Dict[str, Any]]:
        """
        Find a similar prompt with a successful script that can be reused
        
        Args:
            prompt: The current prompt to check
            current_df: Current DataFrame for structure compatibility
            
        Returns:
            Optional[Dict[str, Any]]: Mapping info if similar prompt found, None otherwise
        """
        if not self.mappings:
            print(f"🔍 ScriptReuser: No existing mappings to check")
            return None

        # Get current DataFrame structure hash
        current_df_hash = self._create_dataframe_hash(current_df)
        
        print(f"🔍 ScriptReuser: Checking {len(self.mappings)} existing mappings for similarity >= {self.similarity_threshold}")
        
        best_match = None
        best_similarity = 0.0
        matches_checked = 0

        # If semantic similarity is available, use it
        if SEMANTIC_SIMILARITY_AVAILABLE and self.model is not None:
            # Get embedding for current prompt
            current_embedding = self._get_prompt_embedding(prompt)
            if current_embedding is None:
                print(f"❌ ScriptReuser: Failed to get embedding for current prompt")
                return None

            for mapping in self.mappings:
                try:
                    matches_checked += 1
                    
                    # Check if we have the embedding stored
                    if 'embedding' not in mapping:
                        continue

                    # Load stored embedding
                    if np is not None:
                        stored_embedding = np.array(mapping['embedding'])
                    else:
                        stored_embedding = mapping['embedding']
                    
                    # Calculate similarity
                    similarity = self._calculate_similarity(current_embedding, stored_embedding)
                    
                    print(f"   📝 Mapping {matches_checked}: similarity {similarity:.3f} | prompt: '{mapping['prompt'][:50]}...'")
                    
                    # Check if similarity meets threshold
                    if similarity >= self.similarity_threshold:
                        # Check DataFrame structure compatibility
                        if mapping.get('df_hash') == current_df_hash:
                            # Perfect match - same structure
                            print(f"   ✅ Perfect match: similarity {similarity:.3f} with matching DataFrame structure")
                            if similarity > best_similarity:
                                best_similarity = similarity
                                best_match = mapping
                        else:
                            # Structure mismatch - still consider but with penalty
                            adjusted_similarity = similarity * 0.9  # 10% penalty for structure mismatch
                            print(f"   ⚠️ Structure mismatch: similarity {similarity:.3f} -> {adjusted_similarity:.3f} (with penalty)")
                            if adjusted_similarity >= self.similarity_threshold and adjusted_similarity > best_similarity:
                                best_similarity = adjusted_similarity
                                best_match = mapping
                                
                except Exception as e:
                    logging.warning(f"Error processing mapping: {e}")
                    continue
        else:
            # Fallback to exact string matching
            print(f"🔍 ScriptReuser: Using exact string matching fallback")
            
            for mapping in self.mappings:
                try:
                    matches_checked += 1
                    
                    # Check for exact match
                    if mapping['prompt'].lower().strip() == prompt.lower().strip():
                        print(f"   📝 Mapping {matches_checked}: exact match found | prompt: '{mapping['prompt'][:50]}...'")
                        
                        # Check DataFrame structure compatibility
                        if mapping.get('df_hash') == current_df_hash:
                            print(f"   ✅ Perfect match: exact match with matching DataFrame structure")
                            best_match = mapping
                            best_similarity = 1.0
                            break
                        else:
                            print(f"   ⚠️ Structure mismatch: exact match but different DataFrame structure")
                            if best_match is None:  # Only use if no better match found
                                best_match = mapping
                                best_similarity = 0.9  # Penalty for structure mismatch
                                
                except Exception as e:
                    logging.warning(f"Error processing mapping: {e}")
                    continue

        if best_match:
            print(f"✅ ScriptReuser: Found similar prompt with similarity {best_similarity:.3f}")
            print(f"   📝 Original prompt: {best_match['prompt'][:80]}...")
            print(f"   📝 Current prompt: {prompt[:80]}...")
            print(f"   🎯 Success count: {best_match.get('success_count', 1)} times")
            print(f"   📅 Last used: {best_match.get('last_used', 'unknown')}")
        else:
            print(f"❌ ScriptReuser: No similar prompts found (checked {matches_checked} mappings)")
            
        return best_match

    def save_successful_execution(self, prompt: str, script: str, script_id: str, 
                                 session_id: str, current_df: pd.DataFrame,
                                 use_advanced_processing: bool = False) -> None:
        """
        Save a successful prompt-script execution for future reuse
        
        Args:
            prompt: The original prompt
            script: The successful script
            script_id: Script ID from ScriptManager
            session_id: Session ID
            current_df: DataFrame that was successfully processed
            use_advanced_processing: Whether advanced processing was used
        """
        # Create DataFrame hash
        df_hash = self._create_dataframe_hash(current_df)

        # Create mapping entry
        mapping = {
            'prompt': prompt,
            'script': script,
            'script_id': script_id,
            'session_id': session_id,
            'df_hash': df_hash,
            'use_advanced_processing': use_advanced_processing,
            'created_at': datetime.now().isoformat(),
            'success_count': 1,
            'last_used': datetime.now().isoformat()
        }

        # Add embedding if semantic similarity is available
        if SEMANTIC_SIMILARITY_AVAILABLE and self.model is not None:
            embedding = self._get_prompt_embedding(prompt)
            if embedding is not None:
                mapping['embedding'] = embedding.tolist()  # Convert to list for JSON serialization
        
        # Check if similar prompt already exists
        for i, existing in enumerate(self.mappings):
            if existing.get('script_id') == script_id:
                # Update existing entry
                existing['success_count'] = existing.get('success_count', 0) + 1
                existing['last_used'] = datetime.now().isoformat()
                self._save_mappings()
                return

        # Add new mapping
        self.mappings.append(mapping)
        self._save_mappings()
        
        logging.info(f"Saved successful execution mapping for prompt: {prompt[:50]}...")

    def reuse_script(self, mapping: Dict[str, Any], current_df: pd.DataFrame,
                    file_manager: Optional[FileManager] = None, 
                    session_id: Optional[str] = None) -> Tuple[pd.DataFrame, List[List[int]], bool]:
        """
        Reuse a script from a similar prompt
        
        Args:
            mapping: The mapping information from find_similar_prompt
            current_df: Current DataFrame to process
            file_manager: File manager instance
            session_id: Session ID for context
            
        Returns:
            Tuple[pd.DataFrame, List[List[int]], bool]: (processed_df, modified_cells, success)
        """
        try:
            script = mapping['script']
            use_advanced_processing = mapping.get('use_advanced_processing', False)
            
            logging.info(f"Reusing script from similar prompt")
            logging.info(f"Script ID: {mapping['script_id']}")
            
            # Execute the script using appropriate method
            if use_advanced_processing:
                modified_df, modified_cells = self.script_executor.execute_script(
                    script, current_df.copy(), file_manager, session_id
                )
            else:
                modified_df, modified_cells = self.script_executor.execute_simple_script(
                    script, current_df.copy(), mapping['prompt']
                )
            
            # Update usage statistics
            mapping['success_count'] = mapping.get('success_count', 0) + 1
            mapping['last_used'] = datetime.now().isoformat()
            self._save_mappings()
            
            return modified_df, modified_cells, True
            
        except Exception as e:
            logging.error(f"Failed to reuse script: {e}")
            return current_df, [], False

    def cleanup_old_mappings(self, max_age_days: int = 30, max_mappings: int = 100) -> int:
        """
        Clean up old or rarely used mappings
        
        Args:
            max_age_days: Maximum age of mappings to keep
            max_mappings: Maximum number of mappings to keep
            
        Returns:
            int: Number of mappings cleaned up
        """
        if not self.mappings:
            return 0

        from datetime import datetime, timedelta
        
        cutoff_date = datetime.now() - timedelta(days=max_age_days)
        original_count = len(self.mappings)
        
        # Filter out old mappings
        self.mappings = [
            mapping for mapping in self.mappings
            if datetime.fromisoformat(mapping.get('last_used', mapping.get('created_at', ''))) > cutoff_date
        ]
        
        # Keep only the most frequently used mappings if we still have too many
        if len(self.mappings) > max_mappings:
            self.mappings.sort(key=lambda x: x.get('success_count', 0), reverse=True)
            self.mappings = self.mappings[:max_mappings]
        
        cleaned_count = original_count - len(self.mappings)
        
        if cleaned_count > 0:
            self._save_mappings()
            logging.info(f"Cleaned up {cleaned_count} old mappings")
        
        return cleaned_count

    def get_mapping_stats(self) -> Dict[str, Any]:
        """
        Get statistics about saved mappings
        
        Returns:
            Dict[str, Any]: Statistics information
        """
        if not self.mappings:
            return {
                'total_mappings': 0,
                'total_reuses': 0,
                'avg_similarity_threshold': self.similarity_threshold,
                'model_available': SEMANTIC_SIMILARITY_AVAILABLE and self.model is not None,
                'semantic_mode': SEMANTIC_SIMILARITY_AVAILABLE
            }

        total_reuses = sum(mapping.get('success_count', 0) for mapping in self.mappings)
        
        return {
            'total_mappings': len(self.mappings),
            'total_reuses': total_reuses,
            'avg_similarity_threshold': self.similarity_threshold,
            'model_available': SEMANTIC_SIMILARITY_AVAILABLE and self.model is not None,
            'semantic_mode': SEMANTIC_SIMILARITY_AVAILABLE,
            'oldest_mapping': min(mapping.get('created_at', '') for mapping in self.mappings),
            'newest_mapping': max(mapping.get('created_at', '') for mapping in self.mappings)
        }

    def _calculate_string_similarity(self, str1: str, str2: str) -> float:
        """
        Calculate basic string similarity using longest common subsequence
        Fallback when semantic similarity is not available
        
        Args:
            str1: First string
            str2: Second string
            
        Returns:
            float: Similarity score between 0 and 1
        """
        if not str1 or not str2:
            return 0.0
        
        # Normalize strings
        str1 = str1.lower().strip()
        str2 = str2.lower().strip()
        
        # Exact match
        if str1 == str2:
            return 1.0
        
        # Calculate Jaccard similarity based on words
        words1 = set(str1.split())
        words2 = set(str2.split())
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        if not union:
            return 0.0
        
        return len(intersection) / len(union)
