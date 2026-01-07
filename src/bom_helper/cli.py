import json
from importlib.metadata import version
from pathlib import Path
from typing import List, Optional

import typer
from rich import print
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from bom_helper.main import getPartDetails, savePdf, validate_lcsc_part_number
from bom_helper.kicad import export_full, export_symbol, export_footprint, export_3d_model

app = typer.Typer()

def version_callback(value: bool):
    if value:
        try:
            ver = version("bom-helper")
            print(f"bom version: {ver}")
        except Exception:
            print("bom version: unknown")
        raise typer.Exit()

@app.callback()
def main(
    version: Optional[bool] = typer.Option(
        None,
        "--version",
        "-v",
        help="Show the application's version and exit.",
        callback=version_callback,
        is_eager=True,
    )
):
    pass

@app.command()
def pdf(
    parts: List[str] = typer.Argument(..., help="One or more LCSC part numbers"),
    dir: Path = typer.Option(".", "--dir", help="Directory to save the PDF"),
):
    """
    Download the datasheet PDF for one or more parts.
    """
    failed_parts = []
    total = len(parts)

    for idx, part in enumerate(parts, 1):
        # Show progress if multiple parts
        if total > 1:
            print(f"\n[bold cyan][{idx}/{total}] {part}[/bold cyan]")

        try:
            validate_lcsc_part_number(part)
            saved_path = savePdf(part, dir)
            print(f"Saved PDF to: {saved_path}")
        except ValueError as e:
            print(f"[red]Error: {e}[/red]")
            failed_parts.append(part)
            continue
        except Exception as e:
            print(f"[red]Error downloading PDF for {part}: {e}[/red]")
            failed_parts.append(part)
            continue

    # Exit with error if any failed
    if failed_parts:
        print(f"\n[red]Failed parts: {', '.join(failed_parts)}[/red]")
        raise typer.Exit(code=1)

@app.command()
def info(parts: List[str] = typer.Argument(..., help="One or more LCSC part numbers")):
    """
    Show info from the parsed web page for one or more parts.
    """
    failed_parts = []
    total = len(parts)

    for idx, part in enumerate(parts, 1):
        # Show progress if multiple parts
        if total > 1:
            print(f"\n[bold cyan][{idx}/{total}] {part}[/bold cyan]")

        try:
            validate_lcsc_part_number(part)
            details = getPartDetails(part)
            print(json.dumps(details, indent=2, ensure_ascii=False))
        except ValueError as e:
            print(f"[red]Error: {e}[/red]")
            failed_parts.append(part)
            continue
        except Exception as e:
            print(f"[red]Error fetching part details for {part}: {e}[/red]")
            failed_parts.append(part)
            continue

    # Exit with error if any failed
    if failed_parts:
        print(f"\n[red]Failed parts: {', '.join(failed_parts)}[/red]")
        raise typer.Exit(code=1)


@app.command()
def add(
    parts: List[str] = typer.Argument(..., help="One or more LCSC part numbers"),
    output: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="Base path for library files (e.g., ./kicad-libs/lcsc)",
    ),
    overwrite: bool = typer.Option(
        False, "--overwrite", help="Overwrite existing components"
    ),
):
    """
    Export symbol, footprint, and 3D model for one or more components.

    This is a shortcut for exporting all KiCad library files at once.
    """
    failed_parts = []
    total = len(parts)

    # Resolve output path once (CLI flag or default)
    output_path = output or (
        Path.home() / "Documents" / "Kicad" / "easyeda2kicad" / "easyeda2kicad"
    )

    for idx, part in enumerate(parts, 1):
        # Show progress if multiple parts
        if total > 1:
            print(f"\n[bold cyan][{idx}/{total}] {part}[/bold cyan]")

        try:
            # Show progress with rich
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                transient=True,
            ) as progress:
                progress.add_task(f"Fetching CAD data for {part}...", total=None)
                result = export_full(part, output_path, overwrite)

            # Show status message
            if result.get("status") == "already_exists":
                print(f"[green]Component {part} already exists in library[/green]")
            elif result.get("status") == "updated":
                print(f"[green]Updated component {part}[/green]")
            else:
                print(f"[green]Added component {part}[/green]")

            # Display results with rich table
            table = Table(title=f"Component {part}")
            table.add_column("Type", style="cyan")
            table.add_column("Path", style="green")

            table.add_row("Symbol", str(result["symbol_lib"]))
            table.add_row("Footprint", str(result["footprint_lib"]))
            table.add_row("3D Model", str(result["model_dir"]))

            print(table)

        except ValueError as e:
            print(f"[red]Error: {e}[/red]")
            failed_parts.append(part)
            continue
        except Exception as e:
            print(f"[red]Error exporting {part}: {e}[/red]")
            failed_parts.append(part)
            continue

    # Exit with error if any failed
    if failed_parts:
        print(f"\n[red]Failed parts: {', '.join(failed_parts)}[/red]")
        raise typer.Exit(code=1)


@app.command()
def symbol(
    parts: List[str] = typer.Argument(..., help="One or more LCSC part numbers"),
    output: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="Base path for library files",
    ),
    overwrite: bool = typer.Option(
        False, "--overwrite", help="Overwrite existing symbol"
    ),
):
    """
    Export only the symbol for one or more components.
    """
    failed_parts = []
    total = len(parts)

    # Resolve output path once (CLI flag or default)
    output_path = output or (
        Path.home() / "Documents" / "Kicad" / "easyeda2kicad" / "easyeda2kicad"
    )

    for idx, part in enumerate(parts, 1):
        # Show progress if multiple parts
        if total > 1:
            print(f"\n[bold cyan][{idx}/{total}] {part}[/bold cyan]")

        try:
            # Show progress
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                transient=True,
            ) as progress:
                progress.add_task(f"Fetching symbol for {part}...", total=None)
                result = export_symbol(part, output_path, overwrite)

            # Show status
            if result.get("status") == "already_exists":
                print(f"[green]Symbol for {part} already exists[/green]")
            elif result.get("status") == "updated":
                print(f"[green]Updated symbol for {part}[/green]")
            else:
                print(f"[green]Added symbol for {part}[/green]")

            print(f"Symbol library: [cyan]{result['symbol_lib']}[/cyan]")
            print(f"Component name: [cyan]{result.get('component_name', 'N/A')}[/cyan]")

        except ValueError as e:
            print(f"[red]Error: {e}[/red]")
            failed_parts.append(part)
            continue
        except Exception as e:
            print(f"[red]Error exporting symbol for {part}: {e}[/red]")
            failed_parts.append(part)
            continue

    # Exit with error if any failed
    if failed_parts:
        print(f"\n[red]Failed parts: {', '.join(failed_parts)}[/red]")
        raise typer.Exit(code=1)


@app.command()
def footprint(
    parts: List[str] = typer.Argument(..., help="One or more LCSC part numbers"),
    output: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="Base path for library files",
    ),
    overwrite: bool = typer.Option(
        False, "--overwrite", help="Overwrite existing footprint"
    ),
):
    """
    Export only the footprint for one or more components.
    """
    failed_parts = []
    total = len(parts)

    # Resolve output path once (CLI flag or default)
    output_path = output or (
        Path.home() / "Documents" / "Kicad" / "easyeda2kicad" / "easyeda2kicad"
    )

    for idx, part in enumerate(parts, 1):
        # Show progress if multiple parts
        if total > 1:
            print(f"\n[bold cyan][{idx}/{total}] {part}[/bold cyan]")

        try:
            # Show progress
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                transient=True,
            ) as progress:
                progress.add_task(f"Fetching footprint for {part}...", total=None)
                result = export_footprint(part, output_path, overwrite)

            # Show status
            if result.get("status") == "already_exists":
                print(f"[green]Footprint for {part} already exists[/green]")
            elif result.get("status") == "updated":
                print(f"[green]Updated footprint for {part}[/green]")
            else:
                print(f"[green]Added footprint for {part}[/green]")

            print(f"Footprint library: [cyan]{result['footprint_lib']}[/cyan]")
            if "footprint_file" in result:
                print(f"Footprint file: [cyan]{result['footprint_file']}[/cyan]")
            print(f"Component name: [cyan]{result.get('component_name', 'N/A')}[/cyan]")

        except ValueError as e:
            print(f"[red]Error: {e}[/red]")
            failed_parts.append(part)
            continue
        except Exception as e:
            print(f"[red]Error exporting footprint for {part}: {e}[/red]")
            failed_parts.append(part)
            continue

    # Exit with error if any failed
    if failed_parts:
        print(f"\n[red]Failed parts: {', '.join(failed_parts)}[/red]")
        raise typer.Exit(code=1)


@app.command(name="3d")
def model_3d(
    parts: List[str] = typer.Argument(..., help="One or more LCSC part numbers"),
    output: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="Base path for library files",
    ),
    overwrite: bool = typer.Option(
        False, "--overwrite", help="Overwrite existing 3D model"
    ),
):
    """
    Export only the 3D model for one or more components.
    """
    failed_parts = []
    total = len(parts)

    # Resolve output path once (CLI flag or default)
    output_path = output or (
        Path.home() / "Documents" / "Kicad" / "easyeda2kicad" / "easyeda2kicad"
    )

    for idx, part in enumerate(parts, 1):
        # Show progress if multiple parts
        if total > 1:
            print(f"\n[bold cyan][{idx}/{total}] {part}[/bold cyan]")

        try:
            # Show progress
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                transient=True,
            ) as progress:
                progress.add_task(f"Fetching 3D model for {part}...", total=None)
                result = export_3d_model(part, output_path, overwrite)

            print(f"[green]Exported 3D model for {part}[/green]")
            print(f"3D model directory: [cyan]{result['model_dir']}[/cyan]")

            if "wrl_file" in result:
                print(f"WRL file: [cyan]{result['wrl_file']}[/cyan]")
            if "step_file" in result:
                print(f"STEP file: [cyan]{result['step_file']}[/cyan]")

        except ValueError as e:
            print(f"[red]Error: {e}[/red]")
            failed_parts.append(part)
            continue
        except Exception as e:
            print(f"[red]Error exporting 3D model for {part}: {e}[/red]")
            failed_parts.append(part)
            continue

    # Exit with error if any failed
    if failed_parts:
        print(f"\n[red]Failed parts: {', '.join(failed_parts)}[/red]")
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
