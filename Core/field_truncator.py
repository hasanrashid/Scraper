"""
Field Truncation Utility - Ensures fields fit within size limits for CSV/JSON storage
Truncates from the end backwards to maintain readability of field beginnings
"""

from typing import Any, Dict, List, Union


class FieldTruncator:
    """Utility class for truncating fields to maximum lengths"""
    
    # Default maximum lengths for common fields (in characters)
    DEFAULT_MAX_LENGTHS = {
        'title': 200,
        'bengali_book_title': 200,
        'english_book_title': 200,
        'author': 100,
        'bengali_author': 100,
        'english_author': 100,
        'description': 500,
        'url': 2048,
        'page_url': 2048,
        'download_url': 2048,
        'source_url': 2048,
        'website_name': 100,
        'website': 100,
        'isbn': 50,
    }
    
    @staticmethod
    def truncate_field(value: Any, max_length: int = 200, field_name: str = "") -> Any:
        """
        Truncate a field to maximum length, from the end backwards.
        
        Args:
            value: The value to truncate
            max_length: Maximum length in characters
            field_name: Optional field name for custom max_length lookup
            
        Returns:
            Truncated value, or original if not a string or already within limit
        """
        if not isinstance(value, str):
            return value
        
        value = value.strip()
        
        if len(value) <= max_length:
            return value
        
        # Truncate and add ellipsis if space allows
        if max_length > 3:
            return value[:max_length - 3] + "..."
        else:
            return value[:max_length]
    
    @staticmethod
    def truncate_dict(data: Dict[str, Any], max_lengths: Dict[str, int] = None) -> Dict[str, Any]:
        """
        Truncate all string fields in a dictionary.
        
        Args:
            data: Dictionary to truncate
            max_lengths: Optional custom max lengths dict
            
        Returns:
            New dictionary with truncated values
        """
        if max_lengths is None:
            max_lengths = FieldTruncator.DEFAULT_MAX_LENGTHS
        
        truncated = {}
        for key, value in data.items():
            if isinstance(value, str):
                max_len = max_lengths.get(key, 200)
                truncated[key] = FieldTruncator.truncate_field(value, max_len, key)
            else:
                truncated[key] = value
        
        return truncated
    
    @staticmethod
    def truncate_list(values: List[Any], max_length: int = 200) -> List[Any]:
        """
        Truncate all string values in a list.
        
        Args:
            values: List of values to truncate
            max_length: Maximum length for each string
            
        Returns:
            New list with truncated values
        """
        return [
            FieldTruncator.truncate_field(v, max_length) if isinstance(v, str) else v
            for v in values
        ]
    
    @staticmethod
    def truncate_csv_row(row: List[Any], field_names: List[str] = None, 
                         max_lengths: Dict[str, int] = None) -> List[Any]:
        """
        Truncate values in a CSV row based on field names.
        
        Args:
            row: List of values for the row
            field_names: List of field names corresponding to row values
            max_lengths: Optional custom max lengths dict
            
        Returns:
            Truncated row
        """
        if max_lengths is None:
            max_lengths = FieldTruncator.DEFAULT_MAX_LENGTHS
        
        if field_names is None or len(field_names) != len(row):
            # No field names available, use default truncation
            return FieldTruncator.truncate_list(row, 200)
        
        truncated_row = []
        for field_name, value in zip(field_names, row):
            if isinstance(value, str):
                max_len = max_lengths.get(field_name, 200)
                truncated_row.append(FieldTruncator.truncate_field(value, max_len, field_name))
            else:
                truncated_row.append(value)
        
        return truncated_row
    
    @staticmethod
    def truncate_scraped_page(page_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Truncate fields in a scraped page dictionary (used in consolidated_scraper.py).
        
        Args:
            page_data: Dictionary with scraped page data
            
        Returns:
            New dictionary with truncated fields
        """
        field_limits = {
            'bengali_title': 200,
            'english_title': 200,
            'bengali_author': 100,
            'english_author': 100,
            'post_link': 2048,
            'scrape_date': 50,
        }
        
        truncated = {}
        for key, value in page_data.items():
            if key == 'download_links' and isinstance(value, list):
                # Handle download links list
                truncated_links = []
                for link in value:
                    if isinstance(link, dict):
                        link_dict = {}
                        for link_key, link_value in link.items():
                            if link_key == 'url' and isinstance(link_value, str):
                                link_dict[link_key] = FieldTruncator.truncate_field(
                                    link_value, 2048, link_key
                                )
                            else:
                                link_dict[link_key] = link_value
                        truncated_links.append(link_dict)
                    else:
                        truncated_links.append(
                            FieldTruncator.truncate_field(link, 2048) if isinstance(link, str) else link
                        )
                truncated[key] = truncated_links
            elif isinstance(value, str):
                max_len = field_limits.get(key, 200)
                truncated[key] = FieldTruncator.truncate_field(value, max_len, key)
            else:
                truncated[key] = value
        
        return truncated
