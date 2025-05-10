# PDF Link Finder and Downloader

A Python command-line application that uses object-oriented design to identify and download documents from web pages. Given a URL and optional CSS selectors, the tool locates all links pointing to PDF files and provides a list of URLs, with the option to automatically download them.

## Features

- 🧱 Object-oriented architecture for maintainability and scalability
- 🌐 Parses web pages using CSS selectors
- 📎 Extracts links pointing to PDF documents
- 💾 Optionally downloads PDF files directly from extracted links

## Requirements

- Python 3.9+
- [requests](https://pypi.org/project/requests/)
- [beautifulsoup4](https://pypi.org/project/beautifulsoup4/)

Install dependencies:

```bash
pip install -r requirements.txt
