"""KiCad library export functionality using easyeda2kicad."""

import logging
from pathlib import Path
from textwrap import dedent

from easyeda2kicad.easyeda.easyeda_api import EasyedaApi
from easyeda2kicad.easyeda.easyeda_importer import (
    Easyeda3dModelImporter,
    EasyedaFootprintImporter,
    EasyedaSymbolImporter,
)
from easyeda2kicad.helpers import (
    add_component_in_symbol_lib_file,
    id_already_in_symbol_lib,
    update_component_in_symbol_lib_file,
)
from easyeda2kicad.kicad.export_kicad_3d_model import Exporter3dModelKicad
from easyeda2kicad.kicad.export_kicad_footprint import ExporterFootprintKicad
from easyeda2kicad.kicad.export_kicad_symbol import ExporterSymbolKicad
from easyeda2kicad.kicad.parameters_kicad_symbol import KicadVersion

from bom_helper.main import validate_lcsc_part_number

# Suppress easyeda2kicad logging by default
logging.getLogger("easyeda2kicad").setLevel(logging.ERROR)


def _get_output_paths(base_path: Path) -> dict[str, Path]:
    """Calculate all library paths from a base path."""
    return {
        "symbol_lib": base_path.with_suffix(".kicad_sym"),
        "footprint_lib": Path(str(base_path) + ".pretty"),
        "model_3d_lib": Path(str(base_path) + ".3dshapes"),
    }


def _ensure_library_structure(base_path: Path, lib_name: str) -> None:
    """Create library directories and files if they don't exist."""
    paths = _get_output_paths(base_path)

    # Ensure base directory exists
    base_path.parent.mkdir(parents=True, exist_ok=True)

    # Create footprint directory
    if not paths["footprint_lib"].exists():
        paths["footprint_lib"].mkdir(parents=True, exist_ok=True)

    # Create 3D model directory
    if not paths["model_3d_lib"].exists():
        paths["model_3d_lib"].mkdir(parents=True, exist_ok=True)

    # Create symbol library file with header
    if not paths["symbol_lib"].exists():
        with open(paths["symbol_lib"], "w", encoding="utf-8") as f:
            f.write(
                dedent(
                    """\
                    (kicad_symbol_lib
                      (version 20211014)
                      (generator https://github.com/uPesy/easyeda2kicad.py)
                    )"""
                )
            )


def _fp_already_in_footprint_lib(lib_path: Path, package_name: str) -> bool:
    """Check if footprint already exists in library."""
    footprint_file = lib_path / f"{package_name}.kicad_mod"
    return footprint_file.exists()


def export_symbol(
    part: str, output_path: Path, overwrite: bool = False
) -> dict[str, Path | str]:
    """
    Export KiCad symbol for a given LCSC part number.

    Args:
        part: LCSC part number (e.g., "C2040")
        output_path: Base path for library files
        overwrite: Whether to overwrite existing component

    Returns:
        Dictionary with symbol_lib path and status

    Raises:
        ValueError: If part number is invalid or no CAD data available
    """
    validate_lcsc_part_number(part)

    # Get library name from path
    lib_name = output_path.name
    paths = _get_output_paths(output_path)

    # Ensure library structure exists
    _ensure_library_structure(output_path, lib_name)

    # Fetch CAD data
    api = EasyedaApi()
    cad_data = api.get_cad_data_of_component(lcsc_id=part)

    if not cad_data:
        raise ValueError(
            f"No CAD data found for {part}. "
            "This component may not have KiCad library data available."
        )

    # Import symbol
    importer = EasyedaSymbolImporter(easyeda_cp_cad_data=cad_data)
    easyeda_symbol = importer.get_symbol()

    # Check if already exists
    is_already_in_lib = id_already_in_symbol_lib(
        lib_path=str(paths["symbol_lib"]),
        component_name=easyeda_symbol.info.name,
        kicad_version=KicadVersion.v6,
    )

    # Determine status
    if is_already_in_lib and not overwrite:
        return {
            "symbol_lib": paths["symbol_lib"],
            "component_name": easyeda_symbol.info.name,
            "status": "already_exists",
        }

    # Export symbol
    exporter = ExporterSymbolKicad(symbol=easyeda_symbol, kicad_version=KicadVersion.v6)
    kicad_symbol_lib = exporter.export(footprint_lib_name=lib_name)

    # Add or update in library
    if is_already_in_lib:
        update_component_in_symbol_lib_file(
            lib_path=str(paths["symbol_lib"]),
            component_name=easyeda_symbol.info.name,
            component_content=kicad_symbol_lib,
            kicad_version=KicadVersion.v6,
        )
        status = "updated"
    else:
        add_component_in_symbol_lib_file(
            lib_path=str(paths["symbol_lib"]),
            component_content=kicad_symbol_lib,
            kicad_version=KicadVersion.v6,
        )
        status = "added"

    return {
        "symbol_lib": paths["symbol_lib"],
        "component_name": easyeda_symbol.info.name,
        "status": status,
    }


def export_footprint(
    part: str, output_path: Path, overwrite: bool = False
) -> dict[str, Path | str]:
    """
    Export KiCad footprint for a given LCSC part number.

    Args:
        part: LCSC part number (e.g., "C2040")
        output_path: Base path for library files
        overwrite: Whether to overwrite existing component

    Returns:
        Dictionary with footprint_lib path, footprint_file, and status

    Raises:
        ValueError: If part number is invalid or no CAD data available
    """
    validate_lcsc_part_number(part)

    # Get library name from path
    lib_name = output_path.name
    paths = _get_output_paths(output_path)

    # Ensure library structure exists
    _ensure_library_structure(output_path, lib_name)

    # Fetch CAD data
    api = EasyedaApi()
    cad_data = api.get_cad_data_of_component(lcsc_id=part)

    if not cad_data:
        raise ValueError(
            f"No CAD data found for {part}. "
            "This component may not have KiCad library data available."
        )

    # Import footprint
    importer = EasyedaFootprintImporter(easyeda_cp_cad_data=cad_data)
    easyeda_footprint = importer.get_footprint()

    # Check if already exists
    is_already_in_lib = _fp_already_in_footprint_lib(
        paths["footprint_lib"], easyeda_footprint.info.name
    )

    # Determine status
    if is_already_in_lib and not overwrite:
        footprint_file = paths["footprint_lib"] / f"{easyeda_footprint.info.name}.kicad_mod"
        return {
            "footprint_lib": paths["footprint_lib"],
            "footprint_file": footprint_file,
            "component_name": easyeda_footprint.info.name,
            "status": "already_exists",
        }

    # Export footprint
    ki_footprint = ExporterFootprintKicad(footprint=easyeda_footprint)
    footprint_filename = f"{easyeda_footprint.info.name}.kicad_mod"
    footprint_file = paths["footprint_lib"] / footprint_filename

    # Set 3D model path - use ${EASYEDA2KICAD} for default location
    model_3d_path = f"${{EASYEDA2KICAD}}/{lib_name}.3dshapes"

    ki_footprint.export(
        footprint_full_path=str(footprint_file),
        model_3d_path=model_3d_path,
    )

    status = "updated" if is_already_in_lib else "added"

    return {
        "footprint_lib": paths["footprint_lib"],
        "footprint_file": footprint_file,
        "component_name": easyeda_footprint.info.name,
        "status": status,
    }


def export_3d_model(
    part: str, output_path: Path, overwrite: bool = False
) -> dict[str, Path | str]:
    """
    Export 3D model for a given LCSC part number.

    Args:
        part: LCSC part number (e.g., "C2040")
        output_path: Base path for library files
        overwrite: Whether to overwrite existing files

    Returns:
        Dictionary with model_dir, wrl_file, step_file paths and status

    Raises:
        ValueError: If part number is invalid or no CAD data available
    """
    validate_lcsc_part_number(part)

    # Get library name from path
    lib_name = output_path.name
    paths = _get_output_paths(output_path)

    # Ensure library structure exists
    _ensure_library_structure(output_path, lib_name)

    # Fetch CAD data
    api = EasyedaApi()
    cad_data = api.get_cad_data_of_component(lcsc_id=part)

    if not cad_data:
        raise ValueError(
            f"No CAD data found for {part}. "
            "This component may not have KiCad library data available."
        )

    # Import and export 3D model
    model_importer = Easyeda3dModelImporter(
        easyeda_cp_cad_data=cad_data, download_raw_3d_model=True
    )
    if not model_importer.output:
        raise ValueError(f"No 3D model data found for {part}.")
    exporter = Exporter3dModelKicad(model_3d=model_importer.output)
    exporter.export(lib_path=str(output_path))

    # Build result
    result = {
        "model_dir": paths["model_3d_lib"],
        "status": "added",  # 3D models don't have explicit "already exists" check
    }

    # Check if 3D model output exists and has a name attribute
    if exporter.output and hasattr(exporter.output, "name"):
        result["wrl_file"] = paths["model_3d_lib"] / f"{exporter.output.name}.wrl"
        result["component_name"] = exporter.output.name
    elif exporter.output:
        # If output exists but doesn't have a name, it might be bytes or other type
        # Just indicate success without file paths
        result["component_name"] = "Unknown"

    if exporter.output_step and hasattr(exporter.output_step, "name"):
        result["step_file"] = paths["model_3d_lib"] / f"{exporter.output_step.name}.step"

    return result


def export_full(
    part: str, output_path: Path, overwrite: bool = False
) -> dict[str, Path | str | None]:
    """
    Export symbol, footprint, and 3D model for a given LCSC part number.

    Args:
        part: LCSC part number (e.g., "C2040")
        output_path: Base path for library files
        overwrite: Whether to overwrite existing components

    Returns:
        Dictionary combining all export results

    Raises:
        ValueError: If part number is invalid or no CAD data available
    """
    validate_lcsc_part_number(part)

    # Get library name and paths
    lib_name = output_path.name

    # Ensure library structure exists
    _ensure_library_structure(output_path, lib_name)

    # Fetch CAD data once
    api = EasyedaApi()
    cad_data = api.get_cad_data_of_component(lcsc_id=part)

    if not cad_data:
        raise ValueError(
            f"No CAD data found for {part}. "
            "This component may not have KiCad library data available."
        )

    # Export all three components
    # We'll do individual exports to reuse the logic
    symbol_result = export_symbol(part, output_path, overwrite)
    footprint_result = export_footprint(part, output_path, overwrite)
    model_result = export_3d_model(part, output_path, overwrite)

    # Combine results
    result = {
        "symbol_lib": symbol_result["symbol_lib"],
        "footprint_lib": footprint_result["footprint_lib"],
        "footprint_file": footprint_result.get("footprint_file"),
        "model_dir": model_result["model_dir"],
        "component_name": symbol_result.get("component_name"),
    }

    # Add optional file paths
    if "wrl_file" in model_result:
        result["wrl_file"] = model_result["wrl_file"]
    if "step_file" in model_result:
        result["step_file"] = model_result["step_file"]

    # Determine overall status
    # If all components already exist, status is "already_exists"
    # If any were updated, status is "updated"
    # Otherwise, status is "added"
    statuses = {
        symbol_result.get("status"),
        footprint_result.get("status"),
    }

    if statuses == {"already_exists"}:
        result["status"] = "already_exists"
    elif "updated" in statuses or "already_exists" in statuses:
        if overwrite:
            result["status"] = "updated"
        else:
            result["status"] = "already_exists"
    else:
        result["status"] = "added"

    return result
