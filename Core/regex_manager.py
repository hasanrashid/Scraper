"""
Regex Pattern Manager - Centralized management of regex patterns for the Scraper project
"""

import re
import json
from typing import Dict, List, Optional, Union
from pathlib import Path
import logging


class RegexManager:
    """
    Centralized manager for regex patterns used throughout the application
    """
    
    def __init__(self, patterns_file: str = "Configuration/regex_patterns.json"):
        self.patterns_file = patterns_file
        self.logger = logging.getLogger(__name__)
        self._patterns = {}
        self._compiled_patterns = {}
        self._load_patterns()
    
    def _load_patterns(self):
        """Load regex patterns from JSON configuration file"""
        
        try:
            patterns_path = Path(self.patterns_file)
            if not patterns_path.exists():
                raise FileNotFoundError(f"Regex patterns file not found: {self.patterns_file}")
            
            with open(patterns_path, 'r', encoding='utf-8') as file:
                self._patterns = json.load(file)
            
            self.logger.info(f"Loaded regex patterns from {self.patterns_file}")
            
        except Exception as e:
            self.logger.error(f"Failed to load regex patterns: {str(e)}")
            raise
    
    def get_pattern(self, category: str, pattern_name: str, compiled: bool = True) -> Union[str, re.Pattern]:
        """
        Get a regex pattern by category and name
        
        Args:
            category: Pattern category (e.g., 'book_detection', 'pdf_site_crawler')
            pattern_name: Specific pattern name within the category
            compiled: Whether to return compiled pattern (True) or raw string (False)
            
        Returns:
            Compiled regex pattern or raw pattern string
        """
        
        cache_key = f"{category}.{pattern_name}"
        
        # Get raw pattern
        if category not in self._patterns:
            raise ValueError(f"Pattern category '{category}' not found")
        
        pattern_data = self._patterns[category]
        if pattern_name not in pattern_data:
            raise ValueError(f"Pattern '{pattern_name}' not found in category '{category}'")
        
        raw_pattern = pattern_data[pattern_name]
        
        if not compiled:
            return raw_pattern
        
        # Return cached compiled pattern or compile new one
        if cache_key not in self._compiled_patterns:
            try:
                if isinstance(raw_pattern, list):
                    # Compile list of patterns
                    self._compiled_patterns[cache_key] = [
                        re.compile(pattern, re.IGNORECASE) for pattern in raw_pattern
                    ]
                else:
                    # Compile single pattern
                    self._compiled_patterns[cache_key] = re.compile(raw_pattern, re.IGNORECASE)
                    
            except re.error as e:
                self.logger.error(f"Invalid regex pattern {cache_key}: {str(e)}")
                raise
        
        return self._compiled_patterns[cache_key]
    
    def get_patterns_list(self, category: str, pattern_name: str, compiled: bool = True) -> List[re.Pattern]:
        """
        Get a list of compiled regex patterns
        
        Args:
            category: Pattern category
            pattern_name: Pattern name that contains a list
            compiled: Whether to return compiled patterns
            
        Returns:
            List of compiled regex patterns
        """
        
        # Handle special case where the category itself is a list (e.g., social_media_exclusions)
        if category in self._patterns and isinstance(self._patterns[category], list):
            if pattern_name == '' or pattern_name is None:
                # Return the list directly
                patterns = self._patterns[category]
                if compiled:
                    cache_key = f"{category}._list"
                    if cache_key not in self._compiled_patterns:
                        self._compiled_patterns[cache_key] = [
                            re.compile(pattern, re.IGNORECASE) for pattern in patterns
                        ]
                    return self._compiled_patterns[cache_key]
                else:
                    return patterns
        
        patterns = self.get_pattern(category, pattern_name, compiled)
        
        if compiled and isinstance(patterns, list):
            return patterns
        elif not compiled and isinstance(patterns, list):
            return [re.compile(pattern, re.IGNORECASE) for pattern in patterns]
        else:
            return [patterns] if compiled else [re.compile(patterns, re.IGNORECASE)]
    
    def search(self, category: str, pattern_name: str, text: str, 
               flags: int = re.IGNORECASE) -> Optional[re.Match]:
        """
        Perform regex search using specified pattern
        
        Args:
            category: Pattern category
            pattern_name: Pattern name
            text: Text to search in
            flags: Additional regex flags
            
        Returns:
            Match object or None
        """
        
        pattern = self.get_pattern(category, pattern_name, compiled=True)
        return pattern.search(text)
    
    def findall(self, category: str, pattern_name: str, text: str, 
                flags: int = re.IGNORECASE) -> List[str]:
        """
        Find all matches using specified pattern
        
        Args:
            category: Pattern category
            pattern_name: Pattern name
            text: Text to search in
            flags: Additional regex flags
            
        Returns:
            List of all matches
        """
        
        pattern = self.get_pattern(category, pattern_name, compiled=True)
        return pattern.findall(text)
    
    def substitute(self, category: str, pattern_name: str, text: str, 
                   replacement: str, count: int = 0) -> str:
        """
        Perform regex substitution using specified pattern
        
        Args:
            category: Pattern category
            pattern_name: Pattern name
            text: Text to perform substitution on
            replacement: Replacement string
            count: Maximum number of replacements (0 for all)
            
        Returns:
            Text with substitutions performed
        """
        
        pattern = self.get_pattern(category, pattern_name, compiled=True)
        return pattern.sub(replacement, text, count)
    
    def test_pattern_match(self, category: str, pattern_name: str, 
                          test_strings: List[str]) -> Dict[str, bool]:
        """
        Test a pattern against multiple strings
        
        Args:
            category: Pattern category
            pattern_name: Pattern name
            test_strings: List of strings to test
            
        Returns:
            Dictionary mapping test strings to match results
        """
        
        pattern = self.get_pattern(category, pattern_name, compiled=True)
        results = {}
        
        for test_string in test_strings:
            results[test_string] = bool(pattern.search(test_string))
        
        return results
    
    def get_nested_pattern(self, category: str, subcategory: str, 
                          pattern_name: str, compiled: bool = True) -> Union[str, re.Pattern]:
        """
        Get a pattern from nested structure (e.g., page_metadata.title_author_split)
        
        Args:
            category: Main category
            subcategory: Subcategory within main category
            pattern_name: Pattern name within subcategory
            compiled: Whether to return compiled pattern
            
        Returns:
            Compiled regex pattern or raw pattern string
        """
        
        cache_key = f"{category}.{subcategory}.{pattern_name}"
        
        if category not in self._patterns:
            raise ValueError(f"Pattern category '{category}' not found")
        
        if subcategory not in self._patterns[category]:
            raise ValueError(f"Subcategory '{subcategory}' not found in '{category}'")
        
        if pattern_name not in self._patterns[category][subcategory]:
            raise ValueError(f"Pattern '{pattern_name}' not found in '{category}.{subcategory}'")
        
        raw_pattern = self._patterns[category][subcategory][pattern_name]
        
        if not compiled:
            return raw_pattern
        
        if cache_key not in self._compiled_patterns:
            try:
                self._compiled_patterns[cache_key] = re.compile(raw_pattern, re.IGNORECASE)
            except re.error as e:
                self.logger.error(f"Invalid regex pattern {cache_key}: {str(e)}")
                raise
        
        return self._compiled_patterns[cache_key]
    
    def reload_patterns(self):
        """Reload patterns from file (useful for runtime configuration changes)"""
        
        self._patterns.clear()
        self._compiled_patterns.clear()
        self._load_patterns()
        self.logger.info("Regex patterns reloaded from file")
    
    def validate_all_patterns(self) -> Dict[str, bool]:
        """
        Validate all regex patterns for syntax errors
        
        Returns:
            Dictionary mapping pattern paths to validation results
        """
        
        results = {}
        
        def validate_recursive(data, path=""):
            for key, value in data.items():
                current_path = f"{path}.{key}" if path else key
                
                if isinstance(value, dict):
                    validate_recursive(value, current_path)
                elif isinstance(value, list):
                    for i, pattern in enumerate(value):
                        pattern_path = f"{current_path}[{i}]"
                        try:
                            re.compile(pattern)
                            results[pattern_path] = True
                        except re.error:
                            results[pattern_path] = False
                elif isinstance(value, str):
                    try:
                        re.compile(value)
                        results[current_path] = True
                    except re.error:
                        results[current_path] = False
        
        validate_recursive(self._patterns)
        return results
    
    def get_available_categories(self) -> List[str]:
        """Get list of available pattern categories"""
        return list(self._patterns.keys())
    
    def get_category_patterns(self, category: str) -> List[str]:
        """Get list of pattern names in a category"""
        if category not in self._patterns:
            return []
        
        def get_pattern_names(data, prefix=""):
            names = []
            for key, value in data.items():
                current_name = f"{prefix}.{key}" if prefix else key
                if isinstance(value, dict):
                    names.extend(get_pattern_names(value, current_name))
                else:
                    names.append(current_name)
            return names
        
        return get_pattern_names(self._patterns[category])


# Global instance for easy access
regex_manager = RegexManager()