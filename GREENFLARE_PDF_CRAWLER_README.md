# GreenFlare-like PDF Site Crawler

A comprehensive website crawler for discovering all PDF documents with intelligent title and author extraction, similar to GreenFlare DB functionality.

## 🚀 Key Features

### **Comprehensive Site Crawling**
- 🌐 **Full Website Crawling**: Systematically crawls entire websites to discover all PDF documents
- 🗺️ **Sitemap Discovery**: Automatically finds and parses XML sitemaps for efficient crawling
- 🤖 **Robots.txt Compliance**: Respects robots.txt rules and crawling guidelines
- 🎯 **Configurable Depth**: Set maximum crawl depth and page limits
- ⚡ **Rate Limiting**: Built-in delays to respect server resources

### **Intelligent PDF Discovery**
- 📄 **Smart PDF Detection**: Identifies PDF links through multiple methods (URL patterns, content-type, query parameters)
- 🔍 **Metadata Extraction**: Automatically extracts title, author, file size, and other metadata
- 📊 **File Validation**: Checks file sizes and validates PDF accessibility
- 🌍 **Domain Analysis**: Tracks which domains host the most PDFs

### **Advanced Title & Author Extraction**
- 📝 **Title Intelligence**: Extracts titles from filenames, link text, and context
- 👤 **Author Detection**: Uses regex patterns to identify author names in URLs and filenames
- 🧹 **Content Cleaning**: Removes common unwanted phrases like "Download PDF", "Click here"
- 🎯 **Context Analysis**: Examines surrounding text for better metadata understanding

### **Comprehensive CSV Export**
- 📊 **Rich Metadata**: Exports 14 columns of detailed information per PDF
- 🌐 **Discovery Context**: Tracks source pages, link text, and discovery timestamps
- 📈 **Statistical Summary**: Provides crawl statistics and domain distribution
- 💾 **UTF-8 Encoding**: Properly handles international characters

## 📊 CSV Export Format

Each discovered PDF is exported with comprehensive metadata:

| Column | Description | Example |
|--------|-------------|---------|
| **URL** | Direct PDF download link | `https://university.edu/research/paper.pdf` |
| **Title** | Extracted document title | `Machine Learning Fundamentals` |
| **Author** | Extracted author name | `Dr. Jane Smith` |
| **File Size (Bytes)** | Exact file size | `2097152` |
| **File Size (MB)** | Human-readable size | `2.00` |
| **Content Type** | HTTP content type | `application/pdf` |
| **Last Modified** | Server modification date | `Wed, 15 Nov 2023 10:30:00 GMT` |
| **Discovered On Page** | Source page URL | `https://university.edu/publications/` |
| **Discovery Date** | When PDF was found | `2024-01-15 14:22:33` |
| **Response Code** | HTTP status code | `200` |
| **Depth** | Crawl depth level | `2` |
| **Link Text** | Original anchor text | `Download Research Paper (PDF)` |
| **Link Context** | Surrounding page text | `Latest research findings in...` |
| **Domain** | PDF hosting domain | `university.edu` |

## 🛠️ Installation & Setup

### 1. Prerequisites
```bash
cd /home/soaad/Documents/Scraper
pip install -r requirements.txt
```

### 2. Configuration
Edit `Configuration/config.ini` to customize crawling behavior:

```ini
[SiteCrawler]
# Maximum pages to crawl per site
max-pages-per-site=1000
# Maximum crawl depth
max-crawl-depth=10
# Delay between requests (seconds)
request-delay=1.0
# Follow external links
follow-external-links=false
# Extract PDF metadata
extract-pdf-content=true
# Minimum PDF file size in KB
min-pdf-size-kb=50
# Maximum PDF file size in MB
max-pdf-size-mb=100

[Filenames]
# Output files
pdf-documents-csv=pdf_documents.csv
sitemap-urls=sitemap_urls.txt
```

## 🚀 Usage

### Command Line Interface

**Basic crawling:**
```bash
python greenflare_crawler.py https://university.edu
```

**Advanced options:**
```bash
python greenflare_crawler.py https://research-site.org \
  --max-pages 500 \
  --max-depth 5 \
  --output my_pdfs.csv \
  --delay 2.0 \
  --follow-external
```

**Available options:**
- `--max-pages N`: Maximum pages to crawl (default: from config)
- `--max-depth N`: Maximum crawl depth (default: from config)  
- `--follow-external`: Follow links to external domains
- `--output FILE`: Custom output CSV file path
- `--delay SECONDS`: Delay between requests

### Programmatic Usage

```python
from Core.config_manager import IniConfigManager
from Core.http_client import RequestsHttpClient
from Core.scraper import Scraper
from Core.pdf_site_crawler import PDFSiteCrawler

# Initialize components
config_manager = IniConfigManager()
http_client = RequestsHttpClient(config_manager.get_user_agent())
scraper = Scraper(config_manager, http_client)
crawler = PDFSiteCrawler(config_manager, http_client, scraper)

# Crawl entire site
pdfs = crawler.crawl_site(
    start_url="https://research-university.edu",
    max_pages=1000,
    max_depth=8,
    follow_external=False
)

# Export results
csv_file = crawler.export_to_csv("university_pdfs.csv")
print(f"Found {len(pdfs)} PDFs, exported to {csv_file}")

# Get detailed statistics
summary = crawler.get_crawl_summary()
print(f"Crawled {summary['crawl_stats']['pages_crawled']} pages")
print(f"Total PDF size: {summary['total_size_mb']:.2f} MB")
print(f"PDFs with authors: {summary['pdfs_with_authors']}")
```

## 📈 Output Examples

### Console Output
```
🌐 GreenFlare-like PDF Site Crawler
==================================================
Target URL: https://university.edu

📋 Initializing crawler components...

🔍 Starting comprehensive site crawl...

✅ Crawl completed!

📚 Found 47 PDF documents:

1. Advanced Machine Learning Techniques
   📄 URL: https://university.edu/cs/papers/ml-advanced.pdf
   👤 Author: Dr. Sarah Johnson
   📊 Size: 3.45 MB
   🌐 Found on: https://university.edu/cs/publications/
   🔗 Link text: Download Full Research Paper (PDF)

2. Quantum Computing Fundamentals
   📄 URL: https://university.edu/physics/quantum-basics.pdf
   👤 Author: Prof. Michael Chen
   📊 Size: 2.12 MB
   🌐 Found on: https://university.edu/physics/courses/
   🔗 Link text: Course Materials - Quantum Computing

... and 45 more PDFs

💾 Exported all PDFs to: pdf_documents.csv

📊 Crawl Statistics:
   🏃 Duration: 157.3 seconds
   📄 Pages crawled: 284
   ⚡ Pages/second: 1.81
   📚 PDFs found: 47
   💽 Total size: 156.78 MB
   📝 PDFs with authors: 31
   🌐 Unique domains: 1

🌐 PDFs by domain:
   university.edu: 47 PDFs

📊 Largest PDFs:
   8.95 MB - Computer Vision Research Compendium
   6.23 MB - Statistical Methods in Data Science
   5.67 MB - Neural Networks Architecture Guide

🎯 All PDF metadata has been saved to: pdf_documents.csv
```

### CSV Output Preview
```csv
URL,Title,Author,File Size (Bytes),File Size (MB),Content Type,Last Modified,Discovered On Page,Discovery Date,Response Code,Depth,Link Text,Link Context,Domain
https://university.edu/cs/ml-paper.pdf,Machine Learning Advances,Dr. Sarah Johnson,3618816,3.45,application/pdf,Wed 15 Nov 2023 10:30:00 GMT,https://university.edu/cs/publications/,2024-01-15 14:22:33,200,2,Download Research Paper (PDF),"Latest research findings in machine learning...",university.edu
https://university.edu/physics/quantum.pdf,Quantum Computing Basics,Prof. Michael Chen,2225152,2.12,application/pdf,Mon 13 Nov 2023 15:45:00 GMT,https://university.edu/physics/courses/,2024-01-15 14:23:15,200,3,Course Materials - Quantum Computing,"Fundamental concepts in quantum mechanics...",university.edu
```

## 🎯 Use Cases

Perfect for discovering PDFs from:

### **Academic Institutions**
- 📚 University digital libraries
- 🔬 Research publication repositories  
- 📖 Course material collections
- 🎓 Thesis and dissertation archives

### **Research Organizations**
- 🧪 Scientific paper databases
- 📊 Technical report collections
- 📋 Policy document repositories
- 📈 Statistical analysis reports

### **Corporate Websites**
- 📄 White paper collections
- 📋 Annual reports and financials
- 🔧 Technical documentation
- 📊 Product specifications and manuals

### **Government Portals**
- 🏛️ Policy documents and legislation
- 📊 Statistical reports and data
- 📋 Public consultation documents
- 🗂️ Administrative guidance materials

## 🔧 Advanced Features

### **Sitemap Integration**
- Automatically discovers sitemap.xml files
- Parses sitemap indexes and individual sitemaps
- Supports both XML and text format sitemaps
- Saves discovered URLs for reference

### **Robots.txt Compliance**
- Downloads and parses robots.txt files
- Respects crawl delays and disallow directives
- Gracefully handles sites without robots.txt
- Logs blocked URLs for transparency

### **Intelligent Link Following**
- Skips binary files (images, videos, executables)
- Avoids admin and login pages
- Filters out CSS, JavaScript, and other assets
- Configurable domain restrictions

### **Error Handling & Logging**
- Comprehensive error tracking and logging
- Failed URL collection and reporting
- Graceful handling of timeouts and connection errors
- Progress reporting every 10 pages

### **Performance Optimization**
- Configurable request delays for rate limiting
- Duplicate URL detection and skipping
- Memory-efficient crawling for large sites
- Interrupt handling for graceful shutdown

## 🧪 Testing

Run the comprehensive test suite:

```bash
python -m unittest Tests.test_pdf_site_crawler -v
```

**Test coverage includes:**
- ✅ PDF document metadata creation and CSV export
- ✅ URL normalization and domain comparison
- ✅ Title and author extraction algorithms
- ✅ Link following and crawling logic
- ✅ Sitemap parsing (XML and text formats)
- ✅ File size validation and filtering
- ✅ Crawl statistics and summary generation

## ⚙️ Configuration Reference

### **Crawling Behavior**
```ini
[SiteCrawler]
max-pages-per-site=1000      # Stop after N pages
max-crawl-depth=10           # Maximum link depth to follow
request-delay=1.0            # Seconds between requests
follow-external-links=false  # Stay within original domain
```

### **PDF Filtering**
```ini
min-pdf-size-kb=50          # Skip very small files
max-pdf-size-mb=100         # Skip very large files  
extract-pdf-content=true    # Extract metadata when possible
```

### **Output Configuration**
```ini
[Filenames]
pdf-documents-csv=pdf_documents.csv  # Main output file
sitemap-urls=sitemap_urls.txt        # Discovered sitemap URLs
```

## 🚦 Performance Guidelines

### **Recommended Settings by Site Size**

**Small sites (< 100 pages):**
```bash
--max-pages 100 --max-depth 5 --delay 0.5
```

**Medium sites (100-1000 pages):**  
```bash
--max-pages 500 --max-depth 7 --delay 1.0
```

**Large sites (1000+ pages):**
```bash
--max-pages 1000 --max-depth 10 --delay 2.0
```

### **Respectful Crawling**
- Use appropriate delays (1-2 seconds minimum)
- Respect robots.txt directives
- Monitor server response times
- Stop if receiving too many errors
- Consider crawling during off-peak hours

## 🤝 Contributing

1. **Add new PDF detection patterns**: Extend `_is_pdf_url()` method
2. **Improve metadata extraction**: Enhance title/author regex patterns  
3. **Add new export formats**: Implement additional output formats beyond CSV
4. **Extend sitemap support**: Add support for sitemap index files
5. **Performance optimizations**: Add parallel processing or caching

## 📄 License

Same as the main Scraper project.

---

**Built for comprehensive PDF discovery across entire websites with enterprise-grade reliability and detailed metadata extraction.**