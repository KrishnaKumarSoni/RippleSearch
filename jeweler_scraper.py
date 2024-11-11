from playwright.sync_api import sync_playwright
import pandas as pd
import time
import re
import os
from tenacity import retry, stop_after_attempt, wait_exponential

INDIAN_STATES = [
    "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh", "Goa", "Gujarat", 
    "Haryana", "Himachal Pradesh", "Jharkhand", "Karnataka", "Kerala", "Madhya Pradesh", 
    "Maharashtra", "Manipur", "Meghalaya", "Mizoram", "Nagaland", "Odisha", "Punjab", 
    "Rajasthan", "Sikkim", "Tamil Nadu", "Telangana", "Tripura", "Uttar Pradesh", 
    "Uttarakhand", "West Bengal"
]

def save_to_csv(businesses, state, page_num, all_businesses):
    all_businesses.extend(businesses)
    df = pd.DataFrame(all_businesses)
    filename = f"jewelers_{state.lower().replace(' ', '_')}.csv"
    file_path = os.path.join('downloads', filename)
    df.to_csv(file_path, index=False, encoding='utf-8-sig')
    return filename

def extract_phone_number(text):
    """
    Extract and format phone number from text.
    Returns formatted phone number or empty string if no valid number found.
    """
    if not text:
        return ''
        
    # Remove all non-numeric characters except + symbol
    cleaned = re.sub(r'[^\d+]', '', text)
    
    # Look for patterns (with or without country code)
    patterns = [
        r'\+?91[6-9]\d{9}',  # Indian numbers with country code
        r'[6-9]\d{9}'        # Indian numbers without country code
    ]
    
    for pattern in patterns:
        match = re.search(pattern, cleaned)
        if match:
            number = match.group(0)
            # Format: Add +91 if not present
            if not number.startswith('+'):
                if number.startswith('91'):
                    number = '+' + number
                else:
                    number = '+91' + number
            
            # Format: XXX XXXXX XXXXX
            formatted = f"{number[:3]} {number[3:8]} {number[8:]}"
            return formatted
            
    return ''

def extract_business_info(page):
    businesses = []
    try:
        # Wait for listings
        page.wait_for_selector('div.rllt__details, div[jscontroller]', timeout=15000)
        
        # Get all business listings
        items = page.query_selector_all('div.rllt__details, div[jscontroller="xkZ6Lb"]')
        print(f"Found {len(items)} business listings")
        
        for item in items:
            try:
                # Name
                name_element = item.query_selector('span.OSrXXb, div.dbg0pd span')
                name = name_element.inner_text() if name_element else ''
                
                # Address
                address_element = item.query_selector('div.rllt__details div:nth-child(2), div[role="heading"] + div')
                address = address_element.inner_text() if address_element else ''
                
                # Phone number - Combined extraction
                phone_raw = item.evaluate('''node => {
                    // Try direct phone elements first
                    const phoneEl = node.querySelector('span[aria-label*="phone" i], a[href^="tel:"]');
                    if (phoneEl) {
                        return phoneEl.textContent || phoneEl.getAttribute('href');
                    }
                    
                    // Look in all divs for phone pattern
                    const divs = node.querySelectorAll('div');
                    for (const div of divs) {
                        const text = div.textContent || '';
                        if (text.includes('·')) {
                            const numbers = text.match(/\d[\d\s-]{8,}/);
                            if (numbers) return numbers[0];
                        }
                    }
                    return '';
                }''')
                
                # Use the existing extract_phone_number function
                phone = extract_phone_number(phone_raw)
                
                # Rating
                rating_element = item.query_selector('span.yi40Hd, span.BTtC6e')
                rating = ''
                if rating_element:
                    rating_text = rating_element.inner_text()
                    rating_match = re.search(r'(\d+(\.\d+)?)', rating_text)
                    rating = rating_match.group(1) if rating_match else ''

                if name:
                    businesses.append({
                        'name': name.strip(),
                        'address': address.strip(),
                        'phone': phone,
                        'rating': rating
                    })
                    
            except Exception as e:
                print(f"Error extracting business: {str(e)}")
                continue

        return businesses
        
    except Exception as e:
        print(f"Extraction error: {str(e)}")
        raise

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def scrape_jewelers_for_state(location, search, send_message=None):
    all_businesses = []
    page_num = 1  # Initialize page counter
    
    with sync_playwright() as p:
        try:
            # Launch with debugging
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'
            )
            
            page = context.new_page()
            page.set_default_timeout(30000)
            
            # Send initial status
            if send_message:
                send_message({
                    'type': 'update',
                    'message': f"Starting scrape for {search} in {location}",
                    'total_leads': 0,
                    'pages_scraped': 0
                })
            
            while page_num <= 10:  # Limit to 10 pages
                if page_num == 1:
                    search_query = f"{search} in {location}"
                    url = f"https://www.google.com/search?tbm=lcl&q={'+'.join(search_query.split())}"
                    print(f"Using URL: {url}")
                    response = page.goto(url)
                else:
                    # Click next page button
                    next_button = page.query_selector('#pnnext')
                    if not next_button:
                        break
                    next_button.click()
                
                page.wait_for_load_state('networkidle')
                
                businesses = extract_business_info(page)
                if businesses:
                    all_businesses.extend(businesses)
                    if send_message:
                        send_message({
                            'type': 'update',
                            'message': f"Found {len(businesses)} businesses on page {page_num}",
                            'total_leads': len(all_businesses),
                            'pages_scraped': page_num,
                            'results': all_businesses  # Add current results
                        })
                else:
                    break
                
                page_num += 1
                time.sleep(2)  # Add delay between pages
            
            return all_businesses
            
        except Exception as e:
            print(f"Scraping error: {str(e)}")
            raise
            
        finally:
            if 'browser' in locals():
                browser.close()