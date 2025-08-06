"""BMAD to PocketFlow Code Generator.

This module renders Python code from Jinja templates using parsed BMAD metadata,
following KISS principles for simplicity and speed.
"""

import logging
import subprocess
import time
from pathlib import Path
from typing import Dict, Any, Tuple, List

from jinja2 import Environment, FileSystemLoader, Template
from jinja2.exceptions import TemplateError

try:
    from .parser import AgentMetadata
except ImportError:
    from scripts.parser import AgentMetadata

logger = logging.getLogger(__name__)


class GenerationError(Exception):
    """Raised when code generation fails."""
    pass


class Generator:
    """Template-based code generator for BMAD agents."""
    
    def __init__(self, template_dir: Path):
        """Initialize the generator with template directory.
        
        Args:
            template_dir: Directory containing Jinja2 templates
        """
        self.template_dir = template_dir
        
        if not template_dir.exists():
            raise GenerationError(f"Template directory does not exist: {template_dir}")
        
        # Initialize Jinja environment
        self.env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            trim_blocks=True,
            lstrip_blocks=True
        )
        
        # Add custom filters
        self.env.filters['classname'] = self._to_class_name
        
        logger.info(f"Generator initialized with templates from {template_dir}")
    
    @staticmethod
    def _to_class_name(value: str) -> str:
        """Convert agent ID to proper Python class name."""
        # Convert to title case and remove underscores/hyphens
        parts = value.replace('-', '_').split('_')
        return ''.join(part.capitalize() for part in parts)
    
    def render_agent_node(self, agent_metadata: AgentMetadata, prompt_content: str) -> str:
        """Render a single agent node Python file.
        
        Args:
            agent_metadata: Agent metadata from parser
            prompt_content: The agent's prompt content
            
        Returns:
            Rendered Python code as string
            
        Raises:
            GenerationError: If template rendering fails
        """
        try:
            template = self.env.get_template("agent.py.j2")
            
            # Prepare template context
            context = {
                "agent": {
                    "id": agent_metadata.id,
                    "description": agent_metadata.description,
                    "tools": agent_metadata.tools,
                    "memory_scope": agent_metadata.memory_scope,
                    "wait_for": agent_metadata.wait_for,
                    "parallel": agent_metadata.parallel,
                    "prompt_content": prompt_content.strip()
                }
            }
            
            return template.render(context)
            
        except TemplateError as e:
            raise GenerationError(f"Failed to render agent template for '{agent_metadata.id}': {e}")
    
    def render_fastapi_app(self, agents: Dict[str, Tuple[AgentMetadata, str]]) -> str:
        """Render the FastAPI application file.
        
        Args:
            agents: Dictionary of agent_id -> (metadata, prompt_content)
            
        Returns:
            Rendered Python code as string
            
        Raises:
            GenerationError: If template rendering fails
        """
        try:
            template = self.env.get_template("app.py.j2")
            
            context = {"agents": agents}
            
            return template.render(context)
            
        except TemplateError as e:
            raise GenerationError(f"Failed to render FastAPI app template: {e}")
    
    def render_utils(self) -> str:
        """Render the utils.py file.
        
        Returns:
            Rendered Python code as string
            
        Raises:
            GenerationError: If template rendering fails
        """
        try:
            template = self.env.get_template("utils.py.j2")
            return template.render()
            
        except TemplateError as e:
            raise GenerationError(f"Failed to render utils template: {e}")
    
    def render_agents_init(self, agents: Dict[str, Tuple[AgentMetadata, str]]) -> str:
        """Render the agents/__init__.py file.
        
        Args:
            agents: Dictionary of agent_id -> (metadata, prompt_content)
            
        Returns:
            Rendered Python code as string
            
        Raises:
            GenerationError: If template rendering fails
        """
        try:
            template = self.env.get_template("agents_init.py.j2")
            
            context = {"agents": agents}
            
            return template.render(context)
            
        except TemplateError as e:
            raise GenerationError(f"Failed to render agents __init__.py template: {e}")
    
    def format_code(self, file_paths: List[Path]) -> List[str]:
        """Format generated Python files with black and ruff.
        
        Args:
            file_paths: List of Python files to format
            
        Returns:
            List of formatting issues (empty if all good)
        """
        issues = []
        
        if not file_paths:
            return issues
        
        # Run black formatter
        try:
            result = subprocess.run(
                ["black", "--quiet"] + [str(p) for p in file_paths],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode != 0:
                issues.append(f"Black formatting failed: {result.stderr}")
                logger.warning(f"Black formatting issues: {result.stderr}")
            else:
                logger.info(f"Black formatting completed successfully")
        except subprocess.TimeoutExpired:
            issues.append("Black formatting timed out")
        except FileNotFoundError:
            issues.append("Black not found - install with 'pip install black'")
        except Exception as e:
            issues.append(f"Black formatting error: {e}")
        
        # Run ruff linter
        try:
            result = subprocess.run(
                ["ruff", "check", "--fix"] + [str(p) for p in file_paths],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode != 0:
                # Ruff non-zero exit is normal when it fixes issues
                logger.info(f"Ruff applied fixes: {result.stdout}")
            else:
                logger.info(f"Ruff check completed successfully")
        except subprocess.TimeoutExpired:
            issues.append("Ruff linting timed out")
        except FileNotFoundError:
            issues.append("Ruff not found - install with 'pip install ruff'")
        except Exception as e:
            issues.append(f"Ruff linting error: {e}")
        
        return issues
    
    def generate_all(self, agents: Dict[str, Tuple[AgentMetadata, str]], 
                    output_dir: Path, format_code: bool = True) -> Dict[str, str]:
        """Generate all Python files from templates.
        
        Args:
            agents: Dictionary of agent_id -> (metadata, prompt_content)
            output_dir: Directory to write generated files
            format_code: Whether to format generated code with black/ruff
            
        Returns:
            Dictionary mapping file paths to generated content
            
        Raises:
            GenerationError: If generation fails
        """
        start_time = time.time()
        generated_files = {}
        
        try:
            # Create output directory structure
            output_dir.mkdir(parents=True, exist_ok=True)
            agents_dir = output_dir / "agents"
            agents_dir.mkdir(exist_ok=True)
            
            # Generate individual agent files
            for agent_id, (metadata, prompt_content) in agents.items():
                agent_code = self.render_agent_node(metadata, prompt_content)
                agent_file = agents_dir / f"{agent_id}.py"
                generated_files[str(agent_file)] = agent_code
                
                # Write to file
                with open(agent_file, 'w', encoding='utf-8') as f:
                    f.write(agent_code)
                
                logger.debug(f"Generated agent file: {agent_file}")
            
            # Generate FastAPI app
            app_code = self.render_fastapi_app(agents)
            app_file = output_dir / "app.py"
            generated_files[str(app_file)] = app_code
            
            with open(app_file, 'w', encoding='utf-8') as f:
                f.write(app_code)
            
            # Generate utils
            utils_code = self.render_utils()
            utils_file = output_dir / "utils.py"
            generated_files[str(utils_file)] = utils_code
            
            with open(utils_file, 'w', encoding='utf-8') as f:
                f.write(utils_code)
            
            # Generate agents __init__.py
            init_code = self.render_agents_init(agents)
            init_file = agents_dir / "__init__.py"
            generated_files[str(init_file)] = init_code
            
            with open(init_file, 'w', encoding='utf-8') as f:
                f.write(init_code)
            
            # Format generated code if requested
            if format_code:
                python_files = [Path(path) for path in generated_files.keys() if path.endswith('.py')]
                formatting_issues = self.format_code(python_files)
                
                if formatting_issues:
                    logger.warning(f"Formatting issues: {formatting_issues}")
                else:
                    logger.info("Code formatting completed successfully")
            
            generation_time = time.time() - start_time
            
            logger.info(f"Generated {len(generated_files)} files in {generation_time:.3f}s")
            logger.info(f"Output written to: {output_dir}")
            
            return generated_files
            
        except Exception as e:
            raise GenerationError(f"Failed to generate files: {e}")


def generate_from_config(config: Dict[str, Any], output_dir: Path, 
                        template_dir: Path) -> Dict[str, str]:
    """High-level function to generate code from merged configuration.
    
    Args:
        config: Merged configuration from config_loader
        output_dir: Directory to write generated files
        template_dir: Directory containing Jinja2 templates
        
    Returns:
        Dictionary mapping file paths to generated content
        
    Raises:
        GenerationError: If generation fails
    """
    generator = Generator(template_dir)
    agents = config.get("agents", {})
    
    if not agents:
        logger.warning("No agents found in configuration")
    
    return generator.generate_all(agents, output_dir)


def main():
    """CLI entry point for testing the generator."""
    import sys
    from .parser import parse_agents_directory
    
    if len(sys.argv) != 3:
        print("Usage: python generator.py <agents_dir> <output_dir>")
        sys.exit(1)
    
    agents_dir = Path(sys.argv[1])
    output_dir = Path(sys.argv[2])
    template_dir = Path(__file__).parent / "templates"
    
    try:
        # Parse agents
        agents = parse_agents_directory(agents_dir)
        
        # Generate code
        generator = Generator(template_dir)
        generated_files = generator.generate_all(agents, output_dir)
        
        print(f"Successfully generated {len(generated_files)} files:")
        for file_path in generated_files:
            print(f"  - {file_path}")
            
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()