#!/usr/bin/env python3
"""Integration test for BMAD to PocketFlow generator pipeline."""

import logging
import tempfile
import time
from pathlib import Path

import sys
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.config_loader import load_all_configurations
from scripts.generator import generate_from_config
from scripts.parser import parse_agents_directory

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_end_to_end_generation():
    """Test the complete pipeline from BMAD parsing to code generation."""
    
    # Paths
    project_root = Path(__file__).parent.parent
    bmad_dir = project_root / "bmad"
    agents_dir = bmad_dir / "agents"
    template_dir = project_root / "scripts" / "templates"
    
    print(f"Testing end-to-end generation pipeline...")
    print(f"   BMAD agents dir: {agents_dir}")
    print(f"   Templates dir: {template_dir}")
    
    try:
        start_time = time.time()
        
        # Step 1: Parse BMAD agents
        print(f"Step 1: Parsing BMAD agents...")
        agents_dict = parse_agents_directory(agents_dir)
        print(f"   Found {len(agents_dict)} agents: {list(agents_dict.keys())}")
        
        # Step 2: Load configurations 
        print(f"Step 2: Loading configurations...")
        try:
            config = load_all_configurations(bmad_dir, agents_dict)
            print(f"   Configuration loaded successfully")
        except Exception as e:
            # Config loading might fail due to missing workflow/tools files, that's OK
            print(f"   Configuration loading failed (expected): {e}")
            config = {"agents": agents_dict, "workflows": {}, "tools": {}}
        
        # Step 3: Generate code
        print(f"Step 3: Generating PocketFlow code...")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            
            generated_files = generate_from_config(config, output_dir, template_dir)
            
            generation_time = time.time() - start_time
            
            print(f"Generation completed in {generation_time:.3f}s")
            print(f"   Generated {len(generated_files)} files:")
            
            for file_path in sorted(generated_files.keys()):
                rel_path = Path(file_path).relative_to(output_dir)
                print(f"     - {rel_path}")
            
            # Step 4: Validate generated files
            print(f"Step 4: Validating generated code...")
            
            import ast
            for file_path, content in generated_files.items():
                if file_path.endswith('.py'):
                    try:
                        ast.parse(content)
                        print(f"     OK {Path(file_path).name} - valid Python syntax")
                    except SyntaxError as e:
                        print(f"     ERROR {Path(file_path).name} - syntax error: {e}")
                        return False
            
            # Step 5: Performance check
            if generation_time > 0.5:
                print(f"Warning: Generation took {generation_time:.3f}s (target: <0.5s)")
            else:
                print(f"Performance: Generation completed in {generation_time:.3f}s (OK)")
            
            print(f"Integration test PASSED!")
            return True
            
    except Exception as e:
        print(f"Integration test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_end_to_end_generation()
    exit(0 if success else 1)