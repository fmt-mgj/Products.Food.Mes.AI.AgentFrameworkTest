"""Validation CLI tool for BMAD preprocessing format v2.0.

This tool validates preprocessing agent files against the JSON schema and provides 
helpful error messages with correction suggestions.
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional

import jsonschema
import yaml
from jsonschema import ValidationError

try:
    from .parser import parse_agents_directory, parse_markdown_file, ParsingError
except ImportError:
    from parser import parse_agents_directory, parse_markdown_file, ParsingError

# Configure logging
logger = logging.getLogger(__name__)


class ValidationResult:
    """Result of validation operation."""
    
    def __init__(self, success: bool, errors: List[str], warnings: List[str] = None):
        self.success = success
        self.errors = errors or []
        self.warnings = warnings or []


def load_schema(version: str = "2.0") -> Dict[str, Any]:
    """Load JSON schema for specified version."""
    # Map version to file name
    version_map = {"1.0": "1", "2.0": "2"}
    version_suffix = version_map.get(version, version.replace(".", ""))
    schema_file = Path(__file__).parent / "schemas" / f"preprocessing_v{version_suffix}.json"
    
    if not schema_file.exists():
        raise FileNotFoundError(f"Schema file not found: {schema_file}")
    
    with open(schema_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def validate_against_schema(metadata: Dict[str, Any], schema: Dict[str, Any]) -> ValidationResult:
    """Validate metadata against JSON schema."""
    errors = []
    warnings = []
    
    try:
        jsonschema.validate(instance=metadata, schema=schema)
        return ValidationResult(success=True, errors=[], warnings=warnings)
    
    except ValidationError as e:
        error_msg = format_validation_error(e)
        suggestion = get_correction_suggestion(e)
        if suggestion:
            error_msg += f" → Suggestion: {suggestion}"
        errors.append(error_msg)
        
        return ValidationResult(success=False, errors=errors, warnings=warnings)


def format_validation_error(error: ValidationError) -> str:
    """Format validation error with context."""
    path = " → ".join(str(p) for p in error.absolute_path) if error.absolute_path else "root"
    return f"[{path}] {error.message}"


def get_correction_suggestion(error: ValidationError) -> Optional[str]:
    """Get helpful correction suggestion for validation error."""
    message = error.message.lower()
    
    # Common error patterns and suggestions
    suggestions = {
        "is not of type 'string'": "Ensure the value is enclosed in quotes",
        "is not of type 'array'": "Use list format: [item1, item2]",
        "does not match": "Check the pattern requirements in documentation",
        "is too long": f"Reduce to maximum {error.schema.get('maxLength', 'allowed')} characters",
        "additional properties are not allowed": "Remove unknown fields or check spelling",
        "'id' is a required property": "Add required 'id' field with agent identifier",
        "is not one of": f"Use one of: {', '.join(error.schema.get('enum', []))}",
    }
    
    for pattern, suggestion in suggestions.items():
        if pattern in message:
            return suggestion
    
    # Field-specific suggestions
    if error.absolute_path:
        field = str(error.absolute_path[-1])
        field_suggestions = {
            "id": "Use alphanumeric characters, underscores, and hyphens only",
            "persona": "Keep under 200 characters for token efficiency",
            "tasks": "Reference .md files: ['task1.md', 'task2.md']",
            "checklists": "Reference .md files: ['quality.md']",
            "templates": "Reference .md files: ['template.md']", 
            "commands": "Start with asterisk: ['*analyze', '*validate']",
            "memory_scope": "Use 'isolated', 'shared', or 'shared:namespace'",
        }
        
        if field in field_suggestions:
            return field_suggestions[field]
    
    return None


def validate_file_references(metadata: Dict[str, Any], base_path: Path) -> ValidationResult:
    """Validate that referenced files exist."""
    errors = []
    warnings = []
    
    # Check task references
    for task_file in metadata.get("tasks", []):
        task_path = base_path / "tasks" / task_file
        if not task_path.exists():
            errors.append(f"Task file not found: {task_path}")
    
    # Check checklist references  
    for checklist_file in metadata.get("checklists", []):
        checklist_path = base_path / "checklists" / checklist_file
        if not checklist_path.exists():
            errors.append(f"Checklist file not found: {checklist_path}")
    
    # Check template references
    for template_file in metadata.get("templates", []):
        template_path = base_path / "templates" / template_file
        if not template_path.exists():
            errors.append(f"Template file not found: {template_path}")
    
    # Check wait_for document references
    for doc_path in metadata.get("wait_for", {}).get("docs", []):
        full_doc_path = base_path / doc_path
        if not full_doc_path.exists():
            warnings.append(f"Dependency document not found: {full_doc_path}")
    
    success = len(errors) == 0
    return ValidationResult(success=success, errors=errors, warnings=warnings)


def validate_agent_dependencies(all_agents: Dict[str, Any]) -> ValidationResult:
    """Validate inter-agent dependencies."""
    errors = []
    warnings = []
    
    agent_ids = set(all_agents.keys())
    
    for agent_id, (metadata, _) in all_agents.items():
        # Check agent dependencies
        for dep_agent in metadata.wait_for.get("agents", []):
            if dep_agent not in agent_ids:
                errors.append(f"Agent '{agent_id}' depends on unknown agent '{dep_agent}'")
        
        # Check for circular dependencies (basic check)
        if agent_id in metadata.wait_for.get("agents", []):
            errors.append(f"Agent '{agent_id}' has circular dependency on itself")
    
    success = len(errors) == 0
    return ValidationResult(success=success, errors=errors, warnings=warnings)


def validate_single_file(file_path: Path, schema: Dict[str, Any], base_path: Path) -> ValidationResult:
    """Validate a single preprocessing file."""
    try:
        metadata, content = parse_markdown_file(file_path)
        metadata_dict = metadata.model_dump()
        
        # Schema validation
        schema_result = validate_against_schema(metadata_dict, schema)
        if not schema_result.success:
            return schema_result
        
        # File reference validation
        file_ref_result = validate_file_references(metadata_dict, base_path)
        
        # Combine results
        all_errors = schema_result.errors + file_ref_result.errors
        all_warnings = schema_result.warnings + file_ref_result.warnings
        
        success = len(all_errors) == 0
        return ValidationResult(success=success, errors=all_errors, warnings=all_warnings)
        
    except ParsingError as e:
        return ValidationResult(success=False, errors=[str(e)])


def validate_directory(directory_path: Path, schema: Dict[str, Any]) -> ValidationResult:
    """Validate all files in a directory."""
    try:
        all_agents = parse_agents_directory(directory_path)
        
        all_errors = []
        all_warnings = []
        
        # Validate each file
        for agent_id, (metadata, content) in all_agents.items():
            file_path = directory_path / f"{agent_id}.md"
            
            result = validate_single_file(file_path, schema, directory_path.parent)
            
            if not result.success:
                all_errors.extend([f"{agent_id}: {err}" for err in result.errors])
            
            all_warnings.extend([f"{agent_id}: {warn}" for warn in result.warnings])
        
        # Validate inter-agent dependencies
        dep_result = validate_agent_dependencies(all_agents)
        all_errors.extend(dep_result.errors)
        all_warnings.extend(dep_result.warnings)
        
        success = len(all_errors) == 0
        return ValidationResult(success=success, errors=all_errors, warnings=all_warnings)
        
    except ParsingError as e:
        return ValidationResult(success=False, errors=[str(e)])


def auto_fix_common_issues(file_path: Path) -> bool:
    """Attempt to auto-fix common formatting issues.
    
    Following KISS principle: Simple YAML validation only.
    Complex fixes should be done manually with clear error messages.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Simply try to parse and validate - don't attempt complex fixes
        # KISS: Let users fix their own YAML with helpful error messages
        lines = content.split('\n')
        
        # Only fix the most basic issue: missing quotes on id field
        if '---' in content:
            # Find front matter bounds
            start_idx = lines.index('---') if '---' in lines else -1
            end_idx = -1
            for i in range(start_idx + 1, len(lines)):
                if lines[i].strip() == '---':
                    end_idx = i
                    break
            
            if start_idx >= 0 and end_idx > start_idx:
                # Only fix unquoted id field - most common issue
                for i in range(start_idx + 1, end_idx):
                    if lines[i].strip().startswith('id:'):
                        parts = lines[i].split(':', 1)
                        if len(parts) == 2:
                            value = parts[1].strip()
                            # Only add quotes if clearly missing
                            if value and not value[0] in ['"', "'", '[', '{']:
                                lines[i] = f"{parts[0]}: \"{value}\""
                                
                                # Write back only if we made this one fix
                                fixed_content = '\n'.join(lines)
                                if fixed_content != content:
                                    with open(file_path, 'w', encoding='utf-8') as f:
                                        f.write(fixed_content)
                                    return True
        
        return False
        
    except Exception as e:
        logger.error(f"Auto-fix failed for {file_path}: {e}")
        return False


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Validate BMAD preprocessing format files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python validate_preprocessing.py --src ./preprocessing
  python validate_preprocessing.py --file agent.md --schema v2.0  
  python validate_preprocessing.py --src ./preprocessing --fix
  python validate_preprocessing.py --src ./preprocessing --verbose
        """.strip()
    )
    
    parser.add_argument("--src", type=Path, help="Source directory containing agent files")
    parser.add_argument("--file", type=Path, help="Single file to validate")
    parser.add_argument("--schema", default="2.0", choices=["1.0", "2.0"], 
                       help="Schema version to validate against")
    parser.add_argument("--fix", action="store_true", 
                       help="Attempt to auto-fix common issues")
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Show detailed validation output")
    
    args = parser.parse_args()
    
    # Configure logging
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=level, format='%(levelname)s: %(message)s')
    
    if not args.src and not args.file:
        parser.error("Either --src or --file must be specified")
    
    try:
        # Load schema
        schema = load_schema(args.schema)
        logger.debug(f"Loaded schema v{args.schema}")
        
        if args.file:
            # Validate single file
            if not args.file.exists():
                print(f"Error: File not found: {args.file}", file=sys.stderr)
                sys.exit(1)
            
            if args.fix:
                if auto_fix_common_issues(args.file):
                    print(f"✅ Auto-fixed formatting issues in {args.file}")
            
            result = validate_single_file(args.file, schema, args.file.parent)
            
            if result.success:
                print(f"✅ {args.file}: Valid")
            else:
                print(f"❌ {args.file}: Invalid")
                for error in result.errors:
                    print(f"   Error: {error}")
            
            for warning in result.warnings:
                print(f"   Warning: {warning}")
        
        else:
            # Validate directory
            if not args.src.exists():
                print(f"Error: Directory not found: {args.src}", file=sys.stderr)
                sys.exit(1)
            
            if args.fix:
                # Auto-fix all .md files in directory
                fixed_count = 0
                for md_file in args.src.glob("*.md"):
                    if auto_fix_common_issues(md_file):
                        fixed_count += 1
                
                if fixed_count > 0:
                    print(f"✅ Auto-fixed formatting issues in {fixed_count} files")
            
            result = validate_directory(args.src, schema)
            
            if result.success:
                print(f"✅ All files in {args.src} are valid")
            else:
                print(f"❌ Validation failed for {args.src}")
                for error in result.errors:
                    print(f"   Error: {error}")
            
            for warning in result.warnings:
                print(f"   Warning: {warning}")
        
        # Exit with appropriate code
        sys.exit(0 if result.success else 1)
        
    except Exception as e:
        print(f"Validation failed: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()