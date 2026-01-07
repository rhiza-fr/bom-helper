import re
import requests
from pathlib import Path


def validate_lcsc_part_number(part: str) -> None:
    r"""
    Validate that the part number is a valid LCSC ID.

    LCSC part numbers must:
    - Start with 'C'
    - Be followed by one or more digits
    - Contain no other characters (no paths, spaces, etc.)

    Args:
        part: The part number to validate

    Raises:
        ValueError: If part number is invalid

    Examples:
        Valid: C2040, C124378, C999999999
        Invalid: C:\path\to\file, C123abc, C-123, just "C"
    """
    if not re.match(r'^C\d+$', part):
        raise ValueError(
            f"Invalid LCSC part number: '{part}'. "
            "LCSC part numbers must start with 'C' followed by digits only (e.g., C2040, C124378)."
        )


def partToUrl(part: str) -> str:
    """
    Convert an LCSC part number to its product detail URL.
    
    Args:
        part: The LCSC part number (e.g., C124378)
        
    Returns:
        The URL to the product detail page.
    """
    return f"https://www.lcsc.com/product-detail/{part}.html"

def partToPdfUrl(part: str) -> str:
    """
    Convert an LCSC part number to its datasheet PDF URL.
    
    Args:
        part: The LCSC part number (e.g., C124378)
        
    Returns:
        The URL to the datasheet PDF.
    """
    return f"https://www.lcsc.com/datasheet/{part}.pdf"

def savePdf(part: str, path: Path) -> str:
    """
    Download the datasheet PDF for a given LCSC part number and save it to the specified path.
    
    Args:
        part: The LCSC part number (e.g., C124378)
        path: The local path to save the PDF to.
        
    Returns:
        The string representation of the local saved path.
        
    Raises:
        requests.RequestException: If the download fails.
    """
    url = partToPdfUrl(part)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    response = requests.get(url, stream=True, headers=headers)
    response.raise_for_status()
    
    # Ensure the directory exists
    if not path.exists():
        path.mkdir(parents=True, exist_ok=True)

    datasheet_path = path / f"{part}.pdf"
    
    with open(datasheet_path, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
            
    return str(datasheet_path)

def getPartDetails(part: str) -> dict:
    """
    Fetch and parse the LCSC product page for a given part number.
    
    Args:
        part: The LCSC part number (e.g., C124378)
        
    Returns:
        A dictionary containing the part details.
    """
    from bs4 import BeautifulSoup
    
    url = partToUrl(part)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    
    soup = BeautifulSoup(response.text, "html.parser")
    
    details = {}
    details['url'] = url
    table = soup.find("table", class_="tableInfoWrap")
    if table:
        for row in table.find_all("tr"):
            cols = row.find_all("td")
            if len(cols) >= 2:
                key = cols[0].get_text(strip=True)
                
                # Special handling for "Datasheet": get URL
                if key == "Datasheet":
                    a_tag = cols[1].find("a")
                    if a_tag and a_tag.has_attr("href"):
                        # Ensure absolute URL if relative
                        href = a_tag["href"]
                        if href.startswith("/"):
                            value = f"https://www.lcsc.com{href}"
                        else:
                            value = href
                    else:
                        value = "N/A"
                elif key == "Manufacturer":
                    # Remove "Asian Brands" suffix from nested div if present
                    # The suffix is in <div class="asianBrandsTagIconWrap ...">
                    # We can clone the tag or remove the nested div
                    import copy
                    td_clone = copy.copy(cols[1])
                    for suffix in td_clone.find_all(class_="asianBrandsTagIconWrap"):
                        suffix.decompose()
                    value = td_clone.get_text(strip=True)
                else:
                    value = cols[1].get_text(strip=True)
                    
                details[key] = value

    # Parse Products Specifications
    # Look for the "Products Specifications" header
    # Usually followed by a table. We'll search for the table directly if possible or by proximity.
    # The snippet shows headers with h2 font-Bold-600 fz-20.
    # We can try to find the table that contains "Category" or "Manufacturer" in td id or text.
    # Or iterate over all tables and check headers.
    
    specs = {}
    # Broad search for all tables
    for tbl in soup.find_all("table"):
        # Check if this table looks like specs (header "Type" and "Description" or similar)
        # Using snippet: headers are Type, Description, and a checkbox column.
        headers = [th.get_text(strip=True) for th in tbl.find_all("th")]
        if "Type" in headers and "Description" in headers:
            for row in tbl.find_all("tr"):
                cols = row.find_all("td")
                # Expected at least 2 cols. 
                # Col 0: Type (e.g. Category), Col 1: Description (value)
                if len(cols) >= 2:
                    key = cols[0].get_text(strip=True)
                    val = cols[1].get_text(strip=True)
                    if key and val:
                        specs[key] = val
            if specs:
                details["Specifications"] = specs
                break # Found the specs table

    # Parse Pricing
    pricing = []
    price_table = soup.find("table", class_="priceTable")
    if price_table:
        # Headers: Qty., Unit Price, Ext. Price
        for row in price_table.find_all("tr"):
            cols = row.find_all("td")
            if len(cols) >= 3:
                qty_text = cols[0].get_text(strip=True)
                unit_price = cols[1].get_text(strip=True)
                ext_price = cols[2].get_text(strip=True)
                
                # Qty often has '+' like '11+'. Clean it if desired, but keeping raw is finding for now.
                pricing.append({
                    "Qty": qty_text,
                    "Unit Price": unit_price,
                    "Ext. Price": ext_price
                })
    
    if pricing:
        details["Pricing"] = pricing

    # Extract Product Images from JS
    import re
    import json
    
    # Regex to find productImages:["url1", "url2", ...]
    # The snippet provided: productImages:["https:...",...]
    # We look for productImages: followed by a bracketed list.
    match = re.search(r'productImages\s*:\s*(\[[^\]]*\])', response.text)
    if match:
        try:
            images_json = match.group(1)
            images = json.loads(images_json)
            if images:
                details["Images"] = images
        except json.JSONDecodeError:
            pass
            
    return details
