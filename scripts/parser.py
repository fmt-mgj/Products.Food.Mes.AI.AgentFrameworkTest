"""BMAD Markdown Parser with Front-matter Support.

This module handles parsing BMAD Markdown files and extracting agent metadata
from YAML front-matter, following the KISS principle for simplicity.
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from pydantic import BaseModel, field_validator

# Configure logging
logger = logging.getLogger(__name__)


class AgentMetadata(BaseModel):
    """Agent metadata model with validation for both v1.0 and v2.0 formats."""

    # Core required fields (v1.0 compatibility)
    id: str
    description: Optional[str] = ""
    
    # v2.0 BMAD terminology fields
    persona: Optional[str] = ""
    tasks: List[str] = []
    checklists: List[str] = []
    templates: List[str] = []
    commands: List[str] = []
    
    # Execution configuration
    tools: List[str] = []
    memory_scope: str = "isolated"
    wait_for: Dict[str, List[str]] = {"docs": [], "agents": []}
    parallel: bool = False
    
    # Format version detection
    format_version: str = "1.0"

    @field_validator("memory_scope")
    def validate_memory_scope(cls, v):
        """Validate memory scope is either 'isolated' or 'shared' or 'shared:namespace'."""
        if isinstance(v, str) and (v == "isolated" or v == "shared" or v.startswith("shared:")):
            return v
        raise ValueError("memory_scope must be 'isolated', 'shared', or 'shared:namespace'")

    @field_validator("id")
    def validate_id(cls, v):
        """Validate id is not empty."""
        if not v or not v.strip():
            raise ValueError("Agent id is required and cannot be empty")
        return v.strip()
    
    @field_validator("format_version")
    def validate_format_version(cls, v):
        """Validate format version is supported."""
        if v not in ["1.0", "2.0"]:
            raise ValueError("format_version must be '1.0' or '2.0'")
        return v
    
    def is_v2_format(self) -> bool:
        """Check if this is a v2.0 format with BMAD terminology."""
        return (self.format_version == "2.0" or 
                bool(self.persona or self.tasks or self.checklists or 
                     self.templates or self.commands))


class ParsingError(Exception):
    """Raised when BMAD file parsing fails."""

    def __init__(self, file: str, message: str, line: Optional[int] = None):
        self.file = file
        self.line = line
        if line:
            super().__init__(f"{file}:{line}: {message}")
        else:
            super().__init__(f"{file}: {message}")


def parse_front_matter(content: str) -> tuple[Dict[str, Any], str]:
    """Parse YAML front matter from Markdown content.

    Args:
        content: Raw Markdown content with optional YAML front matter.

    Returns:
        Tuple of (metadata_dict, remaining_markdown_content).

    Raises:
        ParsingError: If YAML parsing fails.
    """
    content = content.strip()

    # Check if content starts with front matter delimiter
    if not content.startswith("---"):
        return {}, content

    try:
        # Find the closing delimiter
        lines = content.split("\n")
        end_delimiter_index = -1

        for i, line in enumerate(lines[1:], 1):  # Skip first line (opening ---)
            if line.strip() == "---":
                end_delimiter_index = i
                break

        if end_delimiter_index == -1:
            # No closing delimiter found, treat as no front matter
            return {}, content

        # Extract YAML content between delimiters
        yaml_lines = lines[1:end_delimiter_index]
        yaml_content = "\n".join(yaml_lines)

        # Parse YAML safely
        metadata = yaml.safe_load(yaml_content) or {}

        # Extract remaining Markdown content
        remaining_lines = lines[end_delimiter_index + 1 :]
        remaining_content = "\n".join(remaining_lines)

        # Strip leading newline if present
        if remaining_content.startswith("\n"):
            remaining_content = remaining_content[1:]

        return metadata, remaining_content

    except yaml.YAMLError as e:
        raise ParsingError("", f"Invalid YAML in front matter: {e}")


def parse_markdown_file(file_path: Path) -> tuple[AgentMetadata, str]:
    """Parse a single BMAD Markdown file.

    Args:
        file_path: Path to the Markdown file.

    Returns:
        Tuple of (agent_metadata, prompt_content).

    Raises:
        ParsingError: If file cannot be read or parsed.
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except IOError as e:
        raise ParsingError(str(file_path), f"Cannot read file: {e}")

    try:
        # Extract front matter and content
        metadata_dict, prompt_content = parse_front_matter(content)

        # If no id in metadata and no front matter, use filename as id
        if not metadata_dict and file_path.stem != file_path.name:
            metadata_dict = {"id": file_path.stem}
        elif not metadata_dict.get("id"):
            metadata_dict["id"] = file_path.stem

        # Auto-detect format version if not specified
        if "format_version" not in metadata_dict:
            has_bmad_fields = any(field in metadata_dict for field in 
                                ["persona", "tasks", "checklists", "templates", "commands"])
            metadata_dict["format_version"] = "2.0" if has_bmad_fields else "1.0"

        # Create validated metadata object
        metadata = AgentMetadata(**metadata_dict)

        return metadata, prompt_content

    except (yaml.YAMLError, ValueError) as e:
        raise ParsingError(str(file_path), f"Parsing failed: {e}")


def parse_agents_directory(
    directory_path: Path,
) -> Dict[str, tuple[AgentMetadata, str]]:
    """Parse all .md files in the agents directory.

    Args:
        directory_path: Path to directory containing agent .md files.

    Returns:
        Dictionary mapping agent_id to (metadata, prompt_content).

    Raises:
        ParsingError: If directory cannot be read or files cannot be parsed.
    """
    if not directory_path.exists():
        raise ParsingError(str(directory_path), "Directory does not exist")

    if not directory_path.is_dir():
        raise ParsingError(str(directory_path), "Path is not a directory")

    agents = {}

    try:
        # Find all .md files
        md_files = list(directory_path.glob("*.md"))

        if not md_files:
            logger.warning(f"No .md files found in {directory_path}")
            return agents

        for file_path in md_files:
            try:
                metadata, prompt_content = parse_markdown_file(file_path)

                # Check for duplicate IDs
                if metadata.id in agents:
                    logger.warning(
                        f"Duplicate agent ID '{metadata.id}' found in {file_path}"
                    )

                agents[metadata.id] = (metadata, prompt_content)
                logger.info(f"Parsed agent '{metadata.id}' from {file_path.name}")

            except ParsingError as e:
                logger.error(f"Failed to parse {file_path}: {e}")
                # Continue with other files instead of failing completely
                continue

    except Exception as e:
        raise ParsingError(str(directory_path), f"Error scanning directory: {e}")

    return agents


# Main entry point for CLI usage
def main():
    """Command-line interface for testing the parser."""
    import sys

    if len(sys.argv) != 2:
        print("Usage: python parser.py <agents_directory>")
        sys.exit(1)

    directory = Path(sys.argv[1])

    try:
        agents = parse_agents_directory(directory)
        print(f"Successfully parsed {len(agents)} agents:")
        for agent_id, (metadata, _) in agents.items():
            print(f"  - {agent_id}: {metadata.description}")
    except ParsingError as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
