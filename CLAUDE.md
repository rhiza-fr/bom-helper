# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

`bom-helper` is a Python CLI tool for fetching information about electronic components from LCSC (a Chinese electronics component distributor). It scrapes product pages to extract part specifications, pricing, images, and datasheets.

## Package Management and Environment

- **Package Manager**: Use `uv` for all dependency management
- **Python Version**: 3.12.2 (specified in `.python-version`)
- **Key Dependencies**:
  - `typer` - CLI framework
  - `rich` - Terminal formatting and progress bars
  - `beautifulsoup4` - HTML parsing for web scraping
  - `requests` - HTTP client
  - `easyeda2kicad` - KiCad library generation (wrapped by kicad.py)

## Commands

### Running the CLI

The CLI is installed as the `bom` command via entry point in `pyproject.toml`.

**All commands support multiple space-separated part numbers for batch processing:**

```bash
# Install and run in development mode
uv run bom --help

# Get part information (returns JSON) - single or multiple
uv run bom info C124378
uv run bom info C2040 C124378 C100

# Download datasheet PDFs - single or multiple
uv run bom pdf C124378 --dir ./datasheets
uv run bom pdf C2040 C2041 C2042 --dir ./datasheets

# Export to KiCad (symbol + footprint + 3D model) - single or multiple
uv run bom add C2040
uv run bom add C2040 C2041 C2042
uv run bom add C2040 --output ./kicad-libs/lcsc
uv run bom add C2040 --overwrite

# Export individual components - single or multiple
uv run bom symbol C2040
uv run bom symbol C2040 C2041
uv run bom footprint C2040
uv run bom 3d C2040
```

### Testing

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov

# Run specific test file
uv run pytest tests/test_lcsc.py

# Run specific test
uv run pytest tests/test_parsing.py::test_getPartDetails
```

### Linting and Formatting

Uses `ruff` for both linting and formatting:

```bash
# Format code
uv run ruff format

# Lint code
uv run ruff check

# Auto-fix linting issues
uv run ruff check --fix
```

## Architecture

### Code Structure

```
src/bom_helper/
├── cli.py        # CLI commands using Typer
├── main.py       # Core logic for scraping and PDF handling
├── kicad.py      # KiCad library export (wraps easyeda2kicad)
└── __init__.py

tests/
├── test_lcsc.py     # Tests for URL generation and PDF downloading
└── test_parsing.py  # Tests for HTML parsing logic (uses mocks)
```

### Key Functions and Data Flow

**URL Generation** (`main.py`):
- `partToUrl(part)` - Converts LCSC part number (e.g., "C124378") to product detail URL
- `partToPdfUrl(part)` - Converts part number to datasheet PDF URL

**PDF Handling** (`main.py`):
- `savePdf(part, path)` - Downloads datasheet PDF with proper User-Agent headers (LCSC blocks default agents)

**Web Scraping** (`main.py:getPartDetails`):
Scrapes LCSC product pages and returns structured dictionary containing:
1. **Basic Info**: Extracted from `table.tableInfoWrap` - includes Manufacturer (with "Asian Brands" suffix stripped), Mfr. Part #, Description
2. **Datasheet URL**: Extracted from the Datasheet row, handles relative URLs
3. **Specifications**: Parsed from table with "Type" and "Description" headers (Category, Package, etc.)
4. **Pricing**: Extracted from `table.priceTable` - returns list of quantity/price tiers
5. **Images**: Extracted via regex from embedded JavaScript (`productImages:["url1",...]`)

**Special Parsing Notes**:
- Manufacturer field removes the "Asian Brands" badge/suffix using `copy.copy()` and `.decompose()`
- Images are extracted from inline JS using regex: `r'productImages\s*:\s*(\[[^\]]*\])'`
- All HTTP requests include a Chrome User-Agent header to avoid being blocked

**KiCad Library Export** (`kicad.py`):
Wraps the easyeda2kicad Python API to provide a better UX:
1. **Core Functions**:
   - `export_symbol(part, output_path, overwrite)` - Export symbol only
   - `export_footprint(part, output_path, overwrite)` - Export footprint only
   - `export_3d_model(part, output_path, overwrite)` - Export 3D model only
   - `export_full(part, output_path, overwrite)` - Export all three
2. **Workflow**:
   - Validate part number starts with 'C'
   - Use `EasyedaApi().get_cad_data_of_component()` to fetch CAD data
   - Create library directory structure if needed (`.kicad_sym`, `.pretty`, `.3dshapes`)
   - Check if component already exists (using `id_already_in_symbol_lib`, `fp_already_in_footprint_lib`)
   - If exists and not `--overwrite`: return with status "already_exists" (no error!)
   - If exists and `--overwrite`: update component
   - If new: add component to library
   - Use easyeda2kicad importers (`EasyedaSymbolImporter`, `EasyedaFootprintImporter`, `Easyeda3dModelImporter`)
   - Use easyeda2kicad exporters to generate KiCad format
   - Return paths to created files with status (added/updated/already_exists)
3. **Key Behavior**:
   - Default output: `~/Documents/Kicad/easyeda2kicad/easyeda2kicad`
   - Never errors when component exists - just confirms and shows paths
   - Suppresses easyeda2kicad logging (sets to ERROR level only)
   - Handles cases where 3D models might not be available

**CLI Integration** (`cli.py`):
- Uses Typer for command routing
- Commands: `info` (JSON), `pdf` (datasheet), `add` (full export), `symbol`, `footprint`, `3d`
- **All commands support multiple parts**: Uses `List[str] = typer.Argument(...)`
- Multi-part behavior:
  - Shows progress indicator `[1/3] C2040` when processing multiple parts
  - Continues processing if one part fails (error handling with `continue`)
  - Accumulates failed parts and exits with code 1 if any failed
  - Displays results per part
- All KiCad commands support `--output` and `--overwrite` flags
- Uses `rich.progress` for progress feedback
- Uses `rich.table` to display export results
- Version command using `importlib.metadata.version()`

### Testing Strategy

- **Unit Tests**: Mock HTTP responses for parsing tests (`test_parsing.py`)
- **Integration Tests**: Real network calls for basic URL and PDF tests (`test_lcsc.py`)
- Mock HTML includes truncated but representative LCSC page structure with all key elements

## Important Patterns

1. **Part Number Validation**: All commands validate part numbers using `validate_lcsc_part_number()` from `main.py`
   - Must start with 'C' followed by digits only (regex: `^C\d+$`)
   - Rejects paths, special characters, spaces, lowercase
   - Examples: Valid: `C2040`, `C124378`; Invalid: `C:\path`, `C123abc`, `c2040`
2. **User-Agent Required**: All `requests.get()` calls must include Chrome User-Agent header or LCSC will return HTML instead of expected content
3. **Path Handling**: Use `pathlib.Path` throughout; `savePdf` creates directories if they don't exist
4. **Error Handling**: Functions raise exceptions that are caught at CLI level and converted to user-friendly messages with exit code 1
5. **BeautifulSoup Usage**: Import inside function (`getPartDetails`) rather than module-level
