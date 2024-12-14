import os
import requests
import yaml
import sqlite3
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import json
import re

# Configurations
CONFIG_FILE = "config.yaml"
DB_FILE = "products.db"  # SQLite database
ASSETS_FOLDER = "assets"

# Load configuration
with open(CONFIG_FILE, 'r') as f:
    config = yaml.safe_load(f)

BASE_URL = config['base_url']
PRODUCTS_PER_SUBCATEGORY = config['products_per_subcategory']

# Initialize SQLite database connection
db_connection = sqlite3.connect(DB_FILE)
cursor = db_connection.cursor()

# Create categories and products tables
cursor.execute('''
    CREATE TABLE IF NOT EXISTS categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        main_category TEXT NOT NULL,
        sub_category TEXT NOT NULL,
        url TEXT,
        UNIQUE (main_category, sub_category)
    );
''')

cursor.execute('''
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        main_category TEXT NOT NULL,
        sub_category TEXT NOT NULL,
        title TEXT,
        old_price TEXT,
        new_price TEXT,
        description TEXT,
        seller_url TEXT,
        image_folder TEXT,
        json_path TEXT
    );
''')

def insert_category(main_category_name, subcategory_name, subcategory_url):
    cursor.execute('''
        SELECT COUNT(*) FROM categories WHERE main_category = ? AND sub_category = ?
    ''', (main_category_name, subcategory_name))
    if cursor.fetchone()[0] == 0:
        cursor.execute('''
            INSERT INTO categories (main_category, sub_category, url)
            VALUES (?, ?, ?)
        ''', (main_category_name, subcategory_name, subcategory_url))
        db_connection.commit()

def get_soup(url):
    """Fetch a webpage and parse it into a BeautifulSoup object with proper encoding."""
    response = requests.get(url)
    response.raise_for_status()
    response.encoding = 'utf-8'  # Ensure the response is interpreted as UTF-8
    return BeautifulSoup(response.text, 'html.parser')

def sanitize_filename(name):
    """Sanitize filenames to allow Persian/Arabic characters."""
    return re.sub(r'[^\w\-\_\u0600-\u06FF ]', '_', name)

def decode_text(text):
    """Ensure text is decoded correctly for Persian/Arabic characters."""
    if text:
        return text.encode('utf-8').decode('utf-8', 'ignore')  # Decode as UTF-8
    return None

def save_image(url, folder, filename):
    """Save an image to the specified folder."""
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()
        os.makedirs(folder, exist_ok=True)
        file_path = os.path.join(folder, filename)
        with open(file_path, 'wb') as f:
            for chunk in response.iter_content(1024):
                f.write(chunk)
        return file_path
    except requests.exceptions.RequestException as e:
        print(f"Failed to download image: {e}")
        return None

def extract_product_metadata(main_category, sub_category, product_id, product_url):
    """Extract detailed metadata for a product."""
    print(f"Extracting metadata for Product ID: {product_id}")
    try:
        soup = get_soup(product_url)

        metadata = {
            "product_id": product_id,
            "url": product_url,
            "main_category": main_category,  # Add main category
            "sub_category": sub_category,  # Add subcategory
            "title": None,
            "description": None,
            "price": None,
            "old_price": None,
            "discount_percentage": None,
            "shop_url": None,
            "shop_name": None,
            "images": [],
            "related_lists": []
        }

        # Extract title
        title_tag = soup.find('h1', class_='svelte-7lo6ed')
        metadata['title'] = decode_text(title_tag.text.strip()) if title_tag else "No Title"

        # Extract description
        description_tag = soup.find('pre', class_='svelte-1j2bv51')
        metadata['description'] = decode_text(description_tag.text.strip()) if description_tag else "No Description"

        # Extract price details
        price_tag = soup.find('div', class_='price discounted svelte-1ldsyi0')
        old_price_tag = soup.find('div', class_='old-price svelte-1ldsyi0')
        discount_tag = soup.find('div', class_='discount-percentage svelte-1ldsyi0')

        metadata['price'] = decode_text(price_tag.text.strip()) if price_tag else "No Price"
        metadata['old_price'] = decode_text(old_price_tag.text.strip()) if old_price_tag else None
        metadata['discount_percentage'] = decode_text(discount_tag.text.strip()) if discount_tag else None

        # Extract shop details
        shop_tag = soup.find('a', class_='shop-info svelte-7lo6ed')
        if shop_tag:
            metadata['shop_url'] = urljoin(BASE_URL, shop_tag['href'])
            shop_name_tag = shop_tag.find('img')
            if shop_name_tag and 'alt' in shop_name_tag.attrs:
                metadata['shop_name'] = decode_text(shop_name_tag['alt'])
            else:
                metadata['shop_name'] = "No Shop Name"

        # Extract images
        image_tags = soup.find_all('img', class_='svelte-13ln6ur')
        product_folder = os.path.join(ASSETS_FOLDER, sanitize_filename(main_category), sanitize_filename(sub_category), product_id)
        os.makedirs(product_folder, exist_ok=True)
        for img_tag in image_tags:
            img_url = img_tag['src']
            img_filename = os.path.basename(img_url)
            save_image(img_url, product_folder, img_filename)
            metadata['images'].append(os.path.join(product_folder, img_filename))

        # Save related products (names only)
        related_names = extract_related_product_names(soup)
        metadata['related_lists'] = [{"name": name} for name in related_names]

        # Save to JSON file
        json_path = os.path.join(product_folder, f"{product_id}.json")
        with open(json_path, 'w', encoding='utf-8') as json_file:
            json.dump(metadata, json_file, ensure_ascii=False, indent=4)

        print(f"Metadata and images for Product ID: {product_id} saved successfully.")

    except Exception as e:
        print(f"Failed to extract metadata for Product ID: {product_id}. Error: {e}")

def extract_related_product_names(soup):
    """Extract the names of related products."""
    related_names = []
    related_container = soup.find('div', class_='address-container svelte-7lo6ed')

    if related_container:
        description_div = related_container.find('div', class_='description svelte-7lo6ed')
        if description_div:
            related_list_items = description_div.find_all('li')
            for list_item in related_list_items:
                link_tag = list_item.find('a', class_='hover:underline')
                if link_tag:
                    related_names.append(decode_text(link_tag.get_text(strip=True)))
    return related_names

def crawl_categories():
    """Crawl categories and subcategories."""
    print("Crawling categories...")
    soup = get_soup(BASE_URL)

    subcategories_sections = soup.find_all('div', class_='subcategories hidden svelte-cjiu79')
    women_section = soup.find('div', class_='subcategories flex svelte-cjiu79')

    if len(subcategories_sections) < 2 or not women_section:
        print("Error: Could not find all required subcategories sections.")
        return

    men_section = subcategories_sections[0]
    kids_section = subcategories_sections[1]

    categories_info = []

    print("Processing زنانه...")
    women_subcategories = women_section.find_all('a', class_='svelte-cjiu79')
    for subcategory in women_subcategories:
        if subcategory.find('svg'):
            continue
        subcategory_url = urljoin(BASE_URL, subcategory['href'])
        subcategory_name = decode_text(subcategory.text.strip())
        categories_info.append(("زنانه", subcategory_name, subcategory_url))

    print("Processing مردانه...")
    men_subcategories = men_section.find_all('a', class_='svelte-cjiu79')
    for subcategory in men_subcategories:
        if subcategory.find('svg'):
            continue
        subcategory_url = urljoin(BASE_URL, subcategory['href'])
        subcategory_name = decode_text(subcategory.text.strip())
        categories_info.append(("مردانه", subcategory_name, subcategory_url))

    print("Processing بچه گانه...")
    kids_subcategories = kids_section.find_all('a', class_='svelte-cjiu79')
    for subcategory in kids_subcategories:
        if subcategory.find('svg'):
            continue
        subcategory_url = urljoin(BASE_URL, subcategory['href'])
        subcategory_name = decode_text(subcategory.text.strip())
        categories_info.append(("بچه گانه", subcategory_name, subcategory_url))

    # Confirm categories and subcategories with the user
    print("\nThe following categories and subcategories were found:")
    for main_category_name, subcategory_name, subcategory_url in categories_info:
        print(f"Main Category: {main_category_name}, Subcategory: {subcategory_name}, URL: {subcategory_url}")

    confirm = input("\nIs this information correct? (yes/no): ").strip().lower()
    if confirm != 'yes':
        print("Aborting crawl. Please check the configuration.")
        exit()

    # Save categories to the database
    for main_category_name, subcategory_name, subcategory_url in categories_info:
        insert_category(main_category_name, subcategory_name, subcategory_url)

    # Crawl products for each category
    for main_category_name, subcategory_name, subcategory_url in categories_info:
        print(f"Crawling products for {main_category_name} > {subcategory_name}...")
        crawl_products_for_category(main_category_name, subcategory_name, subcategory_url)

def crawl_products_for_category(main_category, sub_category, category_url):
    """Crawl products for a specific category."""
    page = 1
    crawled_products = 0

    while crawled_products < PRODUCTS_PER_SUBCATEGORY:
        print(f"  Crawling page {page} for {main_category} > {sub_category}...")
        soup = get_soup(f"{category_url}?page={page}")
        products = soup.find_all('article', class_='svelte-nicmne')

        if not products:
            print("  No more products found.")
            break

        for product in products:
            if crawled_products >= PRODUCTS_PER_SUBCATEGORY:
                break

            product_link = product.find('a', class_='wrapper primary small tonal svelte-atwtro')
            if not product_link:
                continue

            product_url = urljoin(BASE_URL, product_link['href'])
            product_id = product_url.split('/')[-1]

            extract_product_metadata(main_category, sub_category, product_id, product_url)
            crawled_products += 1

        page += 1

if __name__ == "__main__":
    crawl_categories()
