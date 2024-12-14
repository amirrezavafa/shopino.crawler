import os
import json
from urllib.parse import urljoin
from bs4 import BeautifulSoup
import requests

def get_soup(url):
    """Fetch the content of a URL and parse it into a BeautifulSoup object."""
    response = requests.get(url)
    response.raise_for_status()
    response.encoding = 'utf-8'  # Ensure UTF-8 encoding is used by BeautifulSoup
    return BeautifulSoup(response.text, 'html.parser')

def extract_related_product_names(soup):
    """Extract the related product names from the correct HTML structure."""
    related_names = []
    
    # Find the related products section in the HTML structure
    related_container = soup.find('div', class_='address-container svelte-7lo6ed')
    
    if related_container:
        description_div = related_container.find('div', class_='description svelte-7lo6ed')
        if description_div:
            # Extract all the list items inside the <ul>
            related_list_items = description_div.find_all('li')
            for list_item in related_list_items:
                link_tag = list_item.find('a', class_='hover:underline')
                if link_tag:
                    related_names.append(link_tag.get_text(strip=True))  # Get only the product name text
    return related_names

def extract_product_metadata(product_id, product_url):
    print(f"Extracting metadata for Product ID: {product_id}")

    try:
        # Fetch product page
        soup = get_soup(product_url)

        # Initialize metadata dictionary
        metadata = {
            "product_id": product_id,
            "url": product_url,
            "title": None,
            "description": None,
            "price": None,
            "old_price": None,
            "discount_percentage": None,
            "shop_url": None,
            "shop_name": None,
            "images": [],
            "related_lists": []  # Initialize the related lists as an empty list
        }

        # Extract title
        title_tag = soup.find('h1', class_='svelte-7lo6ed')
        metadata['title'] = title_tag.text.strip() if title_tag else "No Title"

        # Extract description
        description_tag = soup.find('pre', class_='svelte-1j2bv51')
        metadata['description'] = description_tag.text.strip() if description_tag else "No Description"

        # Extract price details
        price_tag = soup.find('div', class_='price discounted svelte-1ldsyi0')
        old_price_tag = soup.find('div', class_='old-price svelte-1ldsyi0')
        discount_tag = soup.find('div', class_='discount-percentage svelte-1ldsyi0')

        metadata['price'] = price_tag.text.strip() if price_tag else "No Price"
        metadata['old_price'] = old_price_tag.text.strip() if old_price_tag else None
        metadata['discount_percentage'] = discount_tag.text.strip() if discount_tag else None

        # Extract shop details
        shop_tag = soup.find('a', class_='shop-info svelte-7lo6ed')
        if shop_tag:
            metadata['shop_url'] = urljoin("https://shopino.app", shop_tag['href'])
            shop_name_tag = shop_tag.find('img')
            if shop_name_tag and 'alt' in shop_name_tag.attrs:
                metadata['shop_name'] = shop_name_tag['alt']
            else:
                metadata['shop_name'] = "No Shop Name"

        # Extract images
        image_tags = soup.find_all('img', class_='svelte-13ln6ur')
        image_urls = set()  # Avoid duplicate images
        for img_tag in image_tags:
            img_url = img_tag['src']
            if img_url and img_url not in image_urls:
                # Save image to product folder
                img_filename = os.path.basename(img_url)
                img_path = os.path.join("assets", product_id, img_filename)
                os.makedirs(os.path.join("assets", product_id), exist_ok=True)
                response = requests.get(img_url, stream=True)
                response.raise_for_status()
                with open(img_path, 'wb') as img_file:
                    for chunk in response.iter_content(1024):
                        img_file.write(chunk)
                metadata['images'].append(img_path)
                image_urls.add(img_url)

        # Extract related product names (without URLs)
        related_names = extract_related_product_names(soup)
        metadata['related_lists'] = [{"name": name} for name in related_names]  # Only the product name, no URLs

        # Save metadata to JSON file
        json_path = os.path.join("assets", product_id, f"{product_id}.json")
        with open(json_path, 'w', encoding='utf-8') as json_file:
            json.dump(metadata, json_file, ensure_ascii=False, indent=4)

        print(f"Metadata and images for Product ID: {product_id} saved successfully.")

    except Exception as e:
        print(f"Failed to extract metadata for Product ID: {product_id}. Error: {e}")

# Example Usage
if __name__ == "__main__":
    BASE_URL = "https://shopino.app"
    product_id = "1101493"
    product_url = urljoin(BASE_URL, f"/product/{product_id}")

    extract_product_metadata(product_id, product_url)
