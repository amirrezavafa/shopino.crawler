import os
import requests
import yaml
import sqlite3  # Switch to SQLite
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import json  # For saving product details to JSON
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

# Create categories table
cursor.execute('''
    CREATE TABLE IF NOT EXISTS categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        main_category TEXT NOT NULL,
        sub_category TEXT NOT NULL,
        url TEXT,
        UNIQUE (main_category, sub_category)
    );
''')

# Create products table
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

# Helper functions
def get_soup(url):
    response = requests.get(url)
    response.raise_for_status()
    return BeautifulSoup(response.text, 'html.parser')

def sanitize_filename(name):
    return re.sub(r'[^\w\-\_\u0600-\u06FF ]', '_', name)  # Allows Persian/Arabic characters

def decode_text(text):
    try:
        return text.encode('latin1').decode('utf-8')  # Decodes incorrectly displayed characters
    except UnicodeEncodeError:
        return text  # Returns the original text if decoding fails

def save_image(url, folder, filename):
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()
        os.makedirs(folder, exist_ok=True)
        sanitized_filename = sanitize_filename(filename)
        file_path = os.path.join(folder, sanitized_filename)
        with open(file_path, 'wb') as f:
            for chunk in response.iter_content(1024):
                f.write(chunk)
        return file_path
    except requests.exceptions.RequestException as e:
        print(f"Failed to download image: {e}")
        return None

def extract_product_details(product):
    # Extract product link
    product_link = product.find('a', class_='wrapper primary small tonal svelte-atwtro')
    product_url = urljoin(BASE_URL, product_link['href']) if product_link else None

    # Extract title
    title_tag = product.find('h2', class_='title svelte-nicmne')
    title = title_tag.text.strip() if title_tag else "No Title"

    # Extract prices
    price_info = product.find('div', class_='price-info fanum svelte-nicmne')
    new_price = None
    old_price = None
    if price_info:
        new_price_tag = price_info.find('div', class_='price svelte-nicmne')
        new_price = new_price_tag.text.strip() if new_price_tag else None

    # Extract image URL
    image_tag = product.find('img', class_='svelte-13ln6ur')
    image_url = image_tag['src'] if image_tag else None

    # Placeholder for description and seller info (not found in product list page)
    description = "Description not available"
    seller_url = "Seller URL not available"

    return {
        "url": product_url,
        "title": title,
        "old_price": old_price,
        "new_price": new_price,
        "description": description,
        "seller_url": seller_url,
        "image_url": image_url
    }

def crawl_categories():
    print("Crawling categories...")
    soup = get_soup(BASE_URL)

    # Extract the three subcategory sections based on their class
    subcategories_sections = soup.find_all('div', class_='subcategories hidden svelte-cjiu79')
    women_section = soup.find('div', class_='subcategories flex svelte-cjiu79')

    if len(subcategories_sections) < 2 or not women_section:
        print("Error: Could not find all required subcategories sections.")
        return

    # Assign sections explicitly based on their sequence in the HTML
    men_section = subcategories_sections[0]  # First hidden section (for men)
    kids_section = subcategories_sections[1]  # Second hidden section (for kids)

    categories_info = []

    # Process women subcategories
    print("Processing زنانه...")
    women_subcategories = women_section.find_all('a', class_='svelte-cjiu79')
    for subcategory in women_subcategories:
        if subcategory.find('svg'):  # Skip parent category links
            continue
        subcategory_url = urljoin(BASE_URL, subcategory['href'])
        subcategory_name = decode_text(subcategory.text.strip())
        categories_info.append(("زنانه", subcategory_name, subcategory_url))

    # Process men subcategories
    print("Processing مردانه...")
    men_subcategories = men_section.find_all('a', class_='svelte-cjiu79')
    for subcategory in men_subcategories:
        if subcategory.find('svg'):  # Skip parent category links
            continue
        subcategory_url = urljoin(BASE_URL, subcategory['href'])
        subcategory_name = decode_text(subcategory.text.strip())
        categories_info.append(("مردانه", subcategory_name, subcategory_url))

    # Process kids subcategories
    print("Processing بچه گانه...")
    kids_subcategories = kids_section.find_all('a', class_='svelte-cjiu79')
    for subcategory in kids_subcategories:
        if subcategory.find('svg'):  # Skip parent category links
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

            details = extract_product_details(product)
            if details["url"]:
                print(f"    Crawling Product: {details['url']}")
                save_product(main_category, sub_category, details)
                crawled_products += 1

        page += 1

def save_product(main_category, sub_category, details):
    product_id = details['url'].split('/')[-1]  # Extract ID from URL

    # Save images
    if details['image_url']:
        folder = os.path.join(ASSETS_FOLDER, sanitize_filename(main_category), sanitize_filename(sub_category))
        os.makedirs(folder, exist_ok=True)
        save_image(details['image_url'], folder, f"{product_id}.jpg")

    # Save to database
    cursor.execute('''
        INSERT INTO products (
            main_category, sub_category, title, old_price, new_price, description, seller_url, image_folder, json_path
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        main_category,
        sub_category,
        details['title'],
        details['old_price'],
        details['new_price'],
        details['description'],
        details['seller_url'],
        folder,
        os.path.join(folder, f"{product_id}.json")
    ))

    # Save to JSON
    with open(os.path.join(folder, f"{product_id}.json"), 'w') as f:
        json.dump(details, f)

    db_connection.commit()


if __name__ == "__main__":
    crawl_categories()