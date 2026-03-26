# BOM Helper

A Python CLI tool for fetching electronic component information from LCSC (a Chinese electronics component distributor). Quickly retrieve part specifications, pricing, datasheets, and images for your Bill of Materials (BOM) management.

## Features

- **Batch Processing**: All commands support multiple space-separated part numbers
- **Part Information**: Retrieve detailed component specifications in JSON format
- **Datasheet Download**: Automatically download component datasheets as PDFs
- **KiCad Library Export**: Export symbols, footprints, and 3D models for KiCad
- **Comprehensive Data Extraction**:
  - Manufacturer and part numbers
  - Technical specifications (package type, category, etc.)
  - Pricing tiers for different quantities
  - Product images
  - Datasheet URLs

## Installation

This project uses [uv](https://github.com/astral-sh/uv) for package management. Make sure you have Python 3.12+ installed.

```bash
# Clone the repository
git clone https://github.com/rhiza-fr/bom-helper.git
cd bom-helper

# Install the tool (makes `bom` available on your PATH)
uv tool install .
```

After installation, use `bom` directly — no `uv run` prefix needed.

## Usage

### Get Component Information

Retrieve detailed information about one or more components by LCSC part number:

```bash
# Single part
bom info C124378

# Multiple parts
bom info C2040 C124378 C100
```

This returns a JSON object with all available information:
```json
{
  "url": "https://www.lcsc.com/product-detail/C124378.html",
  "Manufacturer": "hanxia",
  "Mfr. Part #": "HX PM2.54-1x7P TP-YQ",
  "Description": "2.54mm 1kV 7P 3A 1 Gold Brass",
  "Datasheet": "https://www.lcsc.com/datasheet/C124378.pdf",
  "Specifications": {
    "Category": "Connectors",
    "Package": "SMD,P=2.54mm"
  },
  "Pricing": [
    {"Qty": "11+", "Unit Price": "€ 0.2071", "Ext. Price": "€ 2.28"},
    {"Qty": "110+", "Unit Price": "€ 0.1639", "Ext. Price": "€ 18.03"}
  ],
  "Images": [
    "https://assets.lcsc.com/images/lcsc/900x900/front.jpg",
    "https://assets.lcsc.com/images/lcsc/900x900/back.jpg"
  ]
}
```

### Download Datasheet

Download datasheets for one or more components:

```bash
# Save to current directory
bom pdf C124378

# Download multiple datasheets
bom pdf C2040 C124378 C100

# Save to a specific directory
bom pdf C124378 --dir ./datasheets

# Batch download to directory
bom pdf C2040 C2041 C2042 --dir ./datasheets
```

### Export to KiCad

Export component symbols, footprints, and 3D models for use in KiCad:

```bash
# Export everything (symbol + footprint + 3D model) for one part
bom add C2040

# Export multiple parts at once
bom add C2040 C2041 C2042

# Export to a custom location
bom add C2040 --output ./kicad-libs/lcsc

# Update existing components
bom add C2040 --overwrite

# Export only specific parts
bom symbol C2040    # Symbol only
bom footprint C2040 # Footprint only
bom 3d C2040        # 3D model only

# All commands support multiple parts
bom symbol C2040 C2041
bom footprint C2040 C2041 C2042
```

**Default location:** `~/Documents/Kicad/easyeda2kicad/`

The tool will:
- Create library files if they don't exist
- Detect existing components and skip them (use `--overwrite` to update)
- Show you the paths to all created files

### Check Version

```bash
bom --version
```

## Development

### Setup

```bash
# Install development dependencies
uv sync --group dev
```

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage report
uv run pytest --cov

# Run specific test file
uv run pytest tests/test_lcsc.py
```

### Code Quality

This project uses [ruff](https://github.com/astral-sh/ruff) for linting and formatting:

```bash
# Format code
uv run ruff format

# Check for linting issues
uv run ruff check

# Auto-fix linting issues
uv run ruff check --fix
```

## How It Works

BOM Helper provides two main capabilities:

### 1. Component Information & Datasheets
Scrapes the LCSC website to extract component information:
- Fetches product page HTML for a given part number
- Parses structured data from tables and embedded JavaScript
- Returns information in a clean, structured format

Edge cases handled:
- Extracting URLs from relative paths
- Cleaning manufacturer names (removes "Asian Brands" badges)
- Parsing pricing tables with quantity tiers
- Extracting product images from embedded JavaScript

### 2. KiCad Library Export
Integrates with [easyeda2kicad](https://github.com/uPesy/easyeda2kicad.py) to generate KiCad library files:
- Fetches CAD data from EasyEDA API
- Converts symbols, footprints, and 3D models to KiCad format
- Manages library files and prevents duplicates
- Built on top of easyeda2kicad with a simpler batch-friendly CLI

## Requirements

- Python 3.12 or higher
- Internet connection (to fetch data from LCSC)

## Part Number Format

All commands require valid LCSC part numbers. LCSC part numbers must:
- Start with 'C' (uppercase)
- Be followed by one or more digits
- Contain no other characters (no spaces, hyphens, paths, etc.)

**Valid examples:** `C2040`, `C124378`, `C999999999`
**Invalid examples:** `C:\path`, `C123abc`, `C-123`, `c2040` (lowercase), `C 123` (space)

## License

MIT — see [LICENSE](LICENSE).

## Disclaimer

This tool is not affiliated with or endorsed by LCSC. It is designed for personal use to help manage Bills of Materials. Please respect LCSC's terms of service and use this tool responsibly.
