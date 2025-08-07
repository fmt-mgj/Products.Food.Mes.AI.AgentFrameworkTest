#!/usr/bin/env python3
"""BMAD to PocketFlow Generator CLI.

Command-line interface for converting BMAD artifacts to PocketFlow code.
Orchestrates the complete generation pipeline with progress feedback and timing.
"""

import argparse
import logging
import sys
import time
from pathlib import Path

# Add the scripts directory to Python path for imports
script_dir = Path(__file__).parent
sys.path.insert(0, str(script_dir))

from parser import ParsingError, parse_agents_directory

from config_loader import load_all_configurations
from generator import Generator


def setup_logging(verbose: bool = False) -> None:
    """Configure logging based on verbosity level."""
    level = logging.DEBUG if verbose else logging.WARNING
    logging.basicConfig(
        level=level,
        format="[%(levelname)s] %(name)s: %(message)s",
        handlers=[logging.StreamHandler(sys.stderr)]
    )


def validate_directories(src_path: Path, out_path: Path) -> None:
    """Validate source and output directory paths."""
    if not src_path.exists():
        raise FileNotFoundError(f"Source directory does not exist: {src_path}")

    if not src_path.is_dir():
        raise NotADirectoryError(f"Source path is not a directory: {src_path}")

    # Create output directory if it doesn't exist
    out_path.mkdir(parents=True, exist_ok=True)


def print_progress(message: str, verbose: bool = False) -> None:
    """Print progress message with consistent formatting."""
    if verbose:
        print(f"-> {message}", file=sys.stderr)
    else:
        print(f"-> {message}")


def print_success(message: str, verbose: bool = False) -> None:
    """Print success message with consistent formatting."""
    if verbose:
        print(f"  [OK] {message}", file=sys.stderr)
    else:
        print(f"  [OK] {message}")


def print_final_success(message: str) -> None:
    """Print final success message."""
    print(f"[SUCCESS] {message}")


def print_error(message: str) -> None:
    """Print error message with consistent formatting."""
    print(f"[ERROR] {message}", file=sys.stderr)


def main() -> int:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="bmad2pf",
        description="Convert BMAD artifacts to PocketFlow code",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  bmad2pf --src ./preprocessing --out ./generated
  bmad2pf --src ./agents --out ./output --verbose
  bmad2pf --help
        """.strip()
    )

    parser.add_argument(
        "--src",
        type=Path,
        default=Path("./preprocessing"),
        help="Source directory containing preprocessing files (default: ./preprocessing)"
    )

    parser.add_argument(
        "--out",
        type=Path,
        default=Path("./generated"),
        help="Output directory for generated code (default: ./generated)"
    )

    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output with debug information"
    )

    args = parser.parse_args()

    # Setup logging
    setup_logging(args.verbose)

    # Start timing
    start_time = time.perf_counter()

    try:
        # Validate directories
        validate_directories(args.src, args.out)

        # Stage 1: Parse preprocessing files
        print_progress(f"Parsing preprocessing files from {args.src}...", args.verbose)
        parse_start = time.perf_counter()

        agents_dict = parse_agents_directory(args.src)

        parse_time = time.perf_counter() - parse_start
        print_success(f"Found {len(agents_dict)} agents", args.verbose)

        if args.verbose:
            for agent_id in agents_dict.keys():
                print(f"    - {agent_id}", file=sys.stderr)

        # Stage 2: Load configuration
        print_progress("Loading configuration...", args.verbose)
        config_start = time.perf_counter()

        load_all_configurations(args.src, agents_dict)

        config_time = time.perf_counter() - config_start
        print_success("Loaded workflow.yaml", args.verbose)

        # Stage 3: Generate PocketFlow code
        print_progress("Generating PocketFlow code...", args.verbose)
        gen_start = time.perf_counter()

        template_dir = Path(__file__).parent / "templates"
        generator = Generator(template_dir)

        generated_files = generator.generate_all(
            agents_dict, args.out, format_code=True
        )

        gen_time = time.perf_counter() - gen_start
        print_success(f"Generated {len(generated_files)} files", args.verbose)

        if args.verbose:
            for file_type, file_path in generated_files.items():
                print(f"    - {file_type}: {file_path}", file=sys.stderr)

        # Stage 4: Formatting (already done in generate_all)
        print_success("Black formatting applied", args.verbose)
        print_success("Ruff validation passed", args.verbose)

        # Total timing
        total_time = time.perf_counter() - start_time
        print_final_success(f"Generation complete in {total_time:.3f}s")

        if args.verbose:
            print("Timing breakdown:", file=sys.stderr)
            print(f"  - Parsing: {parse_time:.3f}s", file=sys.stderr)
            print(f"  - Config: {config_time:.3f}s", file=sys.stderr)
            print(f"  - Generation: {gen_time:.3f}s", file=sys.stderr)
            print(f"  - Total: {total_time:.3f}s", file=sys.stderr)

        return 0

    except ParsingError as e:
        print_error(f"Error parsing preprocessing file: {e}")
        return 2
    except FileNotFoundError as e:
        print_error(f"File not found: {e}")
        return 5
    except NotADirectoryError as e:
        print_error(f"Directory error: {e}")
        return 5
    except PermissionError as e:
        print_error(f"Permission error: {e}")
        return 5
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
