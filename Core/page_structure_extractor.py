"""
Page Structure Extractor for flexible metadata extraction from web pages.
Supports configurable extraction rules for different sites.
"""

import re
import logging
from urllib.parse import urlparse, quote_plus
from typing import Dict, Any, Optional, List, Union
from bs4 import BeautifulSoup, Tag
from Core.config_manager import ConfigManager


class PageStructureExtractor:
    """
    Flexible page structure extraction based on configurable patterns.
    Allows site-specific extraction rules for title, author, download links, etc.
    """
    
    def __init__(self, config_manager: ConfigManager):
        """Initialize the extractor with configuration."""
        self.config_manager = config_manager
        self.logger = logging.getLogger('PageStructureExtractor')
        self.page_mappings = self._load_page_mappings()
        
    def _load_page_mappings(self) -> Dict[str, Any]:
        """Load page structure mappings from configuration."""
        try:
            expression_mapping = self.config_manager.get_expression_mapping()
            return expression_mapping.get('Page Structure Mapping', {})
        except Exception as e:
            self.logger.error(f"Failed to load page structure mappings: {e}")
            return {}
    
    def extract_metadata(self, soup: BeautifulSoup, url: str) -> Dict[str, Any]:
        """
        Extract metadata from a page using configured extraction rules.
        
        Args:
            soup: BeautifulSoup object of the page
            url: URL of the page for site-specific rules
            
        Returns:
            Dictionary containing extracted metadata
        """
        # Get site-specific configuration
        site_config = self._get_site_config(url)
        
        metadata = {}
        
        # Extract each configured field
        for field_name, field_config in site_config.items():
            try:
                if field_name == 'download_link' and 'construct_url' in field_config:
                    # Special handling for constructed URLs - skip for now
                    continue
                
                # Handle derived fields (aliases)
                if 'derived_field' in field_config:
                    source_field = field_config['derived_field']
                    if source_field in metadata:
                        metadata[field_name] = metadata[source_field]
                    continue
                    
                value = self._extract_field(soup, field_config, url)
                if value:
                    metadata[field_name] = value
                    self.logger.debug(f"Extracted {field_name}: {value[:100]}...")
            except Exception as e:
                self.logger.warning(f"Failed to extract {field_name}: {e}")
        
        # Handle constructed download URLs after extracting all fields
        if 'download_link' in site_config and 'construct_url' in site_config['download_link']:
            download_info = self._construct_download_info(site_config['download_link'], metadata)
            if download_info:
                metadata['download_link'] = download_info['url']
                metadata['filename'] = download_info.get('filename', '')
                self.logger.debug(f"Constructed download URL: {download_info['url']}")
                if download_info.get('filename'):
                    self.logger.debug(f"Filename: {download_info['filename']}")
                
        return metadata
    
    def _get_site_config(self, url: str) -> Dict[str, Any]:
        """Get configuration for specific site or fallback to default."""
        try:
            domain = urlparse(url).netloc.lower()
            
            # Try exact domain match
            if domain in self.page_mappings:
                return self.page_mappings[domain]
                
            # Try without www prefix
            if domain.startswith('www.'):
                domain_no_www = domain[4:]
                if domain_no_www in self.page_mappings:
                    return self.page_mappings[domain_no_www]
            
            # Try with www prefix if not present
            if not domain.startswith('www.'):
                domain_www = f"www.{domain}"
                if domain_www in self.page_mappings:
                    return self.page_mappings[domain_www]
            
            # Fall back to default configuration
            return self.page_mappings.get('default', {})
            
        except Exception as e:
            self.logger.warning(f"Failed to get site config for {url}: {e}")
            return self.page_mappings.get('default', {})
    
    def _extract_field(self, soup: BeautifulSoup, config: Dict[str, Any], url: str = "") -> Optional[str]:
        """Extract a specific field using the provided configuration."""
        value = None
        
        # Try CSS selector extraction
        if 'css_selector' in config:
            value = self._extract_by_css_selector(soup, config['css_selector'])
            
            # If no value and fallback CSS exists
            if not value and 'fallback_css' in config:
                value = self._extract_by_css_selector(soup, config['fallback_css'])
        
        # Try text-based extraction
        if not value and ('text_after' in config or 'text_before' in config):
            value = self._extract_by_text_markers(soup, config)
        
        # Get attribute if specified
        if value and 'attribute' in config:
            if hasattr(value, 'get'):
                value = value.get(config['attribute'], '')
            else:
                value = ''
        
        # Convert to string if it's a Tag
        if isinstance(value, Tag):
            value = value.get_text(strip=True)
        
        # Handle title extraction with special processing
        if 'text_split' in config and value:
            parts = str(value).split(config['text_split'])
            if config.get('take_first', False) and parts:
                value = parts[0].strip()
        
        # Handle regex pattern extraction (for groups)
        if value and 'regex_pattern' in config:
            match = re.search(config['regex_pattern'], str(value))
            if match:
                if 'extract_group' in config:
                    try:
                        value = match.group(config['extract_group'])
                    except IndexError:
                        value = match.group(0)
                else:
                    # Use for validation
                    if not match:
                        return None
            else:
                return None
        
        # Apply cleanup regex if specified
        if value and 'regex_cleanup' in config:
            value = re.sub(config['regex_cleanup'], '', str(value))
        
        # Apply length limit if specified
        if value and 'max_length' in config:
            max_len = config['max_length']
            if len(value) > max_len:
                value = value[:max_len].rsplit(' ', 1)[0] + '...'
        
        # Try fallback attribute if no value found
        if not value and 'fallback_attribute' in config:
            title_tag = soup.find('title')
            if title_tag:
                value = title_tag.get_text(strip=True)
        
        # Special handling for amarbooks.org author extraction from title
        if not value and config.get('fallback_title_extraction'):
            title_tag = soup.find('title')
            if title_tag:
                title_text = title_tag.get_text(strip=True)
                # Extract author from title pattern: "Book ❤️ বই ❤️ (Size) ❤️ Author ✔️ Download"
                author_match = re.search(r'❤️\s*\([^)]+\)\s*❤️\s*([^✔️❤️]+?)\s*✔️', title_text)
                if author_match:
                    value = author_match.group(1).strip()
        
        # Special handling for download URL construction
        if not value and 'construct_download_url' in config:
            # Extract ID from current URL and construct download link
            if 'extract_id_from_url' in config and url:
                id_match = re.search(r'id=(\d+)', url)
                if id_match:
                    book_id = id_match.group(1)
                    value = config['construct_download_url'].format(id=book_id)
        
        return value.strip() if value else None
    
    def _extract_by_css_selector(self, soup: BeautifulSoup, selector: str) -> Optional[Union[str, Tag]]:
        """Extract content using CSS selector."""
        try:
            # Handle multiple selectors separated by comma
            selectors = [s.strip() for s in selector.split(',')]
            
            for sel in selectors:
                elements = soup.select(sel)
                if elements:
                    # Return first non-empty element
                    for element in elements:
                        text = element.get_text(strip=True)
                        if text:
                            return element
            
            return None
            
        except Exception as e:
            self.logger.warning(f"CSS selector failed '{selector}': {e}")
            return None
    
    def _extract_by_text_markers(self, soup: BeautifulSoup, config: Dict[str, Any]) -> Optional[str]:
        """Extract content based on text markers (before/after)."""
        try:
            page_text = soup.get_text()
            
            # Find text after marker
            if 'text_after' in config:
                after_marker = config['text_after']
                after_pos = page_text.find(after_marker)
                if after_pos != -1:
                    start_pos = after_pos + len(after_marker)
                    
                    # Find end position
                    end_pos = len(page_text)
                    if 'text_before' in config:
                        before_marker = config['text_before']
                        before_pos = page_text.find(before_marker, start_pos)
                        if before_pos != -1:
                            end_pos = before_pos
                    
                    # Extract and clean the text
                    extracted = page_text[start_pos:end_pos].strip()
                    # Take only the first line/sentence for cleaner results
                    extracted = extracted.split('\n')[0].strip()
                    return extracted if extracted else None
            
            return None
            
        except Exception as e:
            self.logger.warning(f"Text marker extraction failed: {e}")
            return None
    
    def _extract_from_title_pattern(self, soup: BeautifulSoup, config: Dict[str, Any], url: str) -> Optional[str]:
        """Extract content from page title using regex pattern."""
        try:
            title_tag = soup.find('title')
            if not title_tag:
                return None
            
            title_text = title_tag.get_text(strip=True)
            pattern = config['title_pattern']
            
            match = re.search(pattern, title_text)
            if match:
                # Extract specific group if specified
                group_num = config.get('extract_group', 1)
                if group_num <= len(match.groups()):
                    value = match.group(group_num).strip()
                    
                    # Apply cleanup if specified
                    if 'regex_cleanup' in config:
                        value = re.sub(config['regex_cleanup'], '', value)
                    
                    # Remove common suffixes for PDF filename
                    if config.get('remove_pdf_suffix'):
                        value = re.sub(r'\s*pdf\s*$', '', value, flags=re.IGNORECASE)
                    
                    return value.strip()
            
            return None
            
        except Exception as e:
            self.logger.warning(f"Title pattern extraction failed: {e}")
            return None
    
    def _construct_download_info(self, config: Dict[str, Any], metadata: Dict[str, str]) -> Optional[Dict[str, str]]:
        """Construct download URL and filename from template and metadata."""
        try:
            template = config['construct_url']
            
            # Get all required fields for URL construction
            url_fields = {}
            import re
            field_names = re.findall(r'\{([^}]+)\}', template)
            
            for field_name in field_names:
                if field_name not in metadata:
                    self.logger.warning(f"Cannot construct URL: missing field '{field_name}'")
                    return None
                url_fields[field_name] = metadata[field_name]
            
            # URL encode parameters if specified
            if config.get('url_encode_params', False):
                for key, value in url_fields.items():
                    url_fields[key] = quote_plus(value)
            
            # Format the URL template
            url = template.format(**url_fields)
            
            result = {'url': url}
            
            # Generate filename if format is specified
            if 'filename_format' in config:
                filename_template = config['filename_format']
                filename_fields = re.findall(r'\{([^}]+)\}', filename_template)
                
                filename_values = {}
                for field_name in filename_fields:
                    if field_name in metadata:
                        filename_values[field_name] = metadata[field_name]
                    else:
                        self.logger.warning(f"Missing field for filename: {field_name}")
                
                if len(filename_values) == len(filename_fields):
                    result['filename'] = filename_template.format(**filename_values)
            
            return result
            
        except Exception as e:
            self.logger.warning(f"Download info construction failed: {e}")
            return None
    
    def extract_download_links(self, soup: BeautifulSoup, url: str) -> List[str]:
        """Extract all download links from a page."""
        site_config = self._get_site_config(url)
        download_config = site_config.get('download_link', {})
        
        links = []
        
        if 'css_selector' in download_config:
            try:
                elements = soup.select(download_config['css_selector'])
                for element in elements:
                    href = element.get('href', '')
                    if href:
                        # Apply regex pattern if specified
                        if 'regex_pattern' in download_config:
                            if re.search(download_config['regex_pattern'], href, re.IGNORECASE):
                                links.append(href)
                        else:
                            links.append(href)
                
                # Special case: construct download URL if configured
                if not links and 'construct_download_url' in download_config:
                    id_match = re.search(r'id=(\d+)', url)
                    if id_match:
                        book_id = id_match.group(1)
                        constructed_url = download_config['construct_download_url'].format(id=book_id)
                        links.append(constructed_url)
                            
            except Exception as e:
                self.logger.warning(f"Failed to extract download links: {e}")
        
        return links
    
    def is_book_page(self, soup: BeautifulSoup, url: str) -> bool:
        """Determine if a page contains book information."""
        site_config = self._get_site_config(url)
        
        # Check if we can extract basic book metadata
        title = None
        if 'title' in site_config:
            title = self._extract_field(soup, site_config['title'])
        
        download_links = self.extract_download_links(soup, url)
        
        # Consider it a book page if we have a title and download links
        return bool(title and download_links)
    
    def get_supported_sites(self) -> List[str]:
        """Get list of sites with specific configurations."""
        return list(self.page_mappings.keys())


# Helper function to create extractor instance
def create_page_extractor() -> PageStructureExtractor:
    """Create a PageStructureExtractor instance with default configuration."""
    from Core.config_manager import TestConfigManager
    config_manager = TestConfigManager()
    return PageStructureExtractor(config_manager)