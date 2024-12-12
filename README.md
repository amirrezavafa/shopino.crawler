# Clothing Store Web Scraper

This project is a web scraper designed to crawl a clothing store's website, extract product details, and save the information in a structured format. The scraper uses Python and several libraries such as BeautifulSoup, Requests, and SQLite for its operations.

## Features
- Crawls main categories (`زنانه`, `مردانه`, `بچه گانه`) and their respective subcategories.
- Extracts product details, including:
  - Title
  - Prices (old and new)
  - Description
  - Images
  - Seller URL
- Saves data in an SQLite database.
- Stores product details in JSON format and downloads product images.
- Handles Persian/Arabic text and sanitizes filenames.

## Requirements
- Python 3.7+
- Required Python libraries:
  - `beautifulsoup4`
  - `requests`
  - `sqlite3` (standard library)
  - `pyyaml`

## Setup

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd <repository-directory>
   ```

2. **Set up a virtual environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure the scraper:**
   - Create a `config.yaml` file in the root directory with the following structure:
     ```yaml
     base_url: "<base-url-of-website>"
     products_per_subcategory: 20
     ```

5. **Run the scraper:**
   ```bash
   python clothing_crawler.py
   ```

## Folder Structure
```
.
├── assets/                  # Folder for storing product images
├── config.yaml             # Configuration file
├── clothing_crawler.py     # Main script
├── products.db             # SQLite database
├── requirements.txt        # List of dependencies
├── venv/                   # Virtual environment (ignored in .gitignore)
```

## `.gitignore`
The `.gitignore` file ensures unnecessary files and folders are not tracked by Git:
```
# Byte-compiled files
__pycache__/
*.py[cod]

# Virtual environment
venv/

# SQLite database
*.db

# Configuration files
config.yaml

# Logs
*.log
```

## Usage Notes
- Confirm the categories and subcategories during the scraping process.
- Ensure the `base_url` in the configuration matches the target website.
- Update the `products_per_subcategory` value in `config.yaml` as needed.

## License
This project is licensed under the MIT License. See `LICENSE` for details.

