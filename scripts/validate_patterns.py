#!/usr/bin/env python3
"""Pattern Validation Tool for BMAD → PocketFlow Generator.

Validates that generated agents follow established cookbook patterns correctly.
This tool implements the pattern validation requirements from Story 5.2.
"""

import argparse
import ast
import logging
import re
import sys
import time
from pathlib import Path
from typing import Dict, List, Set, Tuple, Any

# Add scripts directory to path for imports if needed
script_dir = Path(__file__).parent
if str(script_dir) not in sys.path:
    sys.path.insert(0, str(script_dir))

from parser import parse_agents_directory
from generator import Generator

logger = logging.getLogger(__name__)


class PatternValidationError(Exception):
    """Raised when pattern validation fails."""
    pass


class PatternValidator:
    """Validates cookbook pattern compliance in generated BMAD agents."""
    
    def __init__(self):
        self.validation_rules = self._load_validation_rules()
    
    def _load_validation_rules(self) -> Dict[str, List[Dict[str, Any]]]:
        """Load pattern validation rules based on cookbook patterns."""
        return {
            "stateless_execution": [
                {"pattern": r"class \w+Node\(.*Node\):", "description": "Must inherit from Node or AsyncNode"},
                {"pattern": r"def prep\(self, shared\):", "description": "Must implement prep method"},
                {"pattern": r"def exec\(self, prep_res\):", "description": "Must implement exec method (sync agents)"},
                {"pattern": r"def post\(self, shared, prep_res, exec_res\):", "description": "Must implement post method"},
                {"pattern": r"import yaml", "description": "Must import yaml for structured output"},
                {"pattern": r"yaml\.safe_load", "description": "Must use yaml.safe_load for parsing"},
            ],
            "external_control": [
                {"pattern": r"for dependency in.*:", "description": "Must check dependencies in prep"},
                {"pattern": r"RuntimeError.*Dependency not met", "description": "Must raise RuntimeError for unmet dependencies"},
                {"pattern": r'shared\["\w+_result"\]', "description": "Must store results with agent_result pattern"},
                {"pattern": r'shared\["last_result"\]', "description": "Must update last_result"},
            ],
            "validation_patterns": [
                {"pattern": r"assert.*is not None", "description": "Must validate structured output is not None"},
                {"pattern": r'assert.*"result".*in', "description": "Must validate result field exists"},
                {"pattern": r'assert.*"confidence".*in', "description": "Must validate confidence field exists"},
                {"pattern": r"def exec_fallback\(self, prep_res, exc\):", "description": "Must implement fallback method"},
            ],
            "error_handling": [
                {"pattern": r"max_retries=\d+", "description": "Must set max_retries in constructor"},
                {"pattern": r"super\(\)\.__init__\(", "description": "Must call parent constructor"},
                {"pattern": r"try:.*except.*:", "description": "Must have try/except for LLM calls", "flags": re.DOTALL},
            ],
            "performance": [
                {"pattern": r"AsyncNode", "description": "Parallel agents must use AsyncNode"},
                {"pattern": r"async def exec_async", "description": "Parallel agents must implement exec_async"},
                {"pattern": r"await call_llm_async", "description": "Parallel agents must use async LLM calls"},
            ],
            "memory_management": [
                {"pattern": r"memory_key.*_memory", "description": "Must use memory_key pattern"},
                {"pattern": r"shared\[memory_key\]", "description": "Must access memory through memory_key"},
                {"pattern": r"last_execution", "description": "Must store execution metadata"},
            ]
        }
    
    def validate_agent_code(self, code: str, agent_metadata: Any) -> List[str]:
        """Validate a single agent's generated code against patterns.
        
        Args:
            code: Generated Python code
            agent_metadata: Agent metadata from BMAD file
            
        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []
        
        # Always validate stateless execution patterns
        errors.extend(self._validate_pattern_group(code, "stateless_execution"))
        
        # Validate external control if agent has dependencies
        if agent_metadata.wait_for.agents:
            errors.extend(self._validate_pattern_group(code, "external_control"))
        
        # Always validate validation patterns
        errors.extend(self._validate_pattern_group(code, "validation_patterns"))
        
        # Always validate error handling
        errors.extend(self._validate_pattern_group(code, "error_handling"))
        
        # Validate performance patterns for parallel agents
        if agent_metadata.parallel:
            errors.extend(self._validate_pattern_group(code, "performance"))
        
        # Validate memory management patterns
        errors.extend(self._validate_pattern_group(code, "memory_management"))
        
        return errors
    
    def _validate_pattern_group(self, code: str, group_name: str) -> List[str]:
        """Validate a group of related patterns.
        
        Args:
            code: Generated Python code
            group_name: Name of the pattern group to validate
            
        Returns:
            List of validation error messages
        """
        errors = []
        rules = self.validation_rules.get(group_name, [])
        
        for rule in rules:
            pattern = rule["pattern"]
            description = rule["description"]
            flags = rule.get("flags", 0)
            
            if not re.search(pattern, code, flags):
                errors.append(f"{group_name}: {description} - Pattern not found: {pattern}")
        
        return errors
    
    def validate_app_code(self, code: str, has_parallel_agents: bool) -> List[str]:
        """Validate FastAPI application code against orchestrator patterns.
        
        Args:
            code: Generated FastAPI application code
            has_parallel_agents: Whether any agents use parallel execution
            
        Returns:
            List of validation error messages
        """
        errors = []
        
        # Orchestrator pattern validation
        orchestrator_rules = [
            {"pattern": r"orchestrator_state.*Dict", "description": "Must define orchestrator_state"},
            {"pattern": r"update_orchestrator_state", "description": "Must implement state update function"},
            {"pattern": r"/orchestrator/status/", "description": "Must provide status endpoint"},
            {"pattern": r"execution_id", "description": "Must track execution IDs"},
            {"pattern": r"StatusResponse", "description": "Must define StatusResponse model"},
        ]
        
        for rule in orchestrator_rules:
            if not re.search(rule["pattern"], code):
                errors.append(f"orchestrator: {rule['description']} - Pattern not found: {rule['pattern']}")
        
        # Async flow validation for parallel agents
        if has_parallel_agents:
            async_rules = [
                {"pattern": r"AsyncFlow", "description": "Must use AsyncFlow for parallel agents"},
                {"pattern": r"asyncio\.run", "description": "Must use asyncio.run for async execution"},
            ]
            
            for rule in async_rules:
                if not re.search(rule["pattern"], code):
                    errors.append(f"async_flow: {rule['description']} - Pattern not found: {rule['pattern']}")
        
        return errors
    
    def validate_utils_code(self, code: str) -> List[str]:
        """Validate utils code against cookbook utility patterns.
        
        Args:
            code: Generated utils.py code
            
        Returns:
            List of validation error messages
        """
        errors = []
        
        utils_rules = [
            {"pattern": r"def call_llm\(", "description": "Must provide call_llm function"},
            {"pattern": r"async def call_llm_async\(", "description": "Must provide call_llm_async function"},
            {"pattern": r"def get_memory_scoped_data\(", "description": "Must provide memory scoping utilities"},
            {"pattern": r"def check_dependencies_ready\(", "description": "Must provide dependency checking utilities"},
            {"pattern": r"def validate_structured_output\(", "description": "Must provide output validation utilities"},
        ]
        
        for rule in utils_rules:
            if not re.search(rule["pattern"], code):
                errors.append(f"utils: {rule['description']} - Pattern not found: {rule['pattern']}")
        
        return errors


def validate_generation_performance(agents: Dict, template_dir: Path) -> Tuple[float, bool]:
    """Validate that generation completes in under 1 second.
    
    Args:
        agents: Dictionary of agents to generate
        template_dir: Template directory path
        
    Returns:
        Tuple of (generation_time, under_1s_requirement_met)
    """
    # KISS optimization: Initialize generator once and reuse templates
    generator = Generator(template_dir)
    
    # Warm up template cache (not counted in timing)
    generator.render_utils()
    
    # Start timing only the actual generation
    start_time = time.perf_counter()
    
    # Generate all code
    for agent_id, (metadata, prompt) in agents.items():
        generator.render_agent_node(metadata, prompt)
    
    generator.render_fastapi_app(agents)
    generator.render_agents_init(agents)
    
    end_time = time.perf_counter()
    generation_time = end_time - start_time
    
    return generation_time, generation_time < 1.0


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="validate_patterns",
        description="Validate BMAD → PocketFlow pattern compliance",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        "--src",
        type=Path,
        default=Path("./preprocessing"),
        help="Source directory containing BMAD files (default: ./preprocessing)"
    )
    
    parser.add_argument(
        "--templates",
        type=Path,
        default=Path(__file__).parent / "templates",
        help="Template directory (default: ./scripts/templates)"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output"
    )
    
    parser.add_argument(
        "--performance-only",
        action="store_true",
        help="Only validate performance requirements"
    )
    
    args = parser.parse_args()
    
    # Setup logging
    level = logging.INFO if args.verbose else logging.WARNING
    logging.basicConfig(level=level, format="[%(levelname)s] %(message)s")
    
    try:
        print(f"[INFO] Validating pattern compliance for {args.src}")
        
        # Parse BMAD files
        agents = parse_agents_directory(args.src)
        print(f"[INFO] Found {len(agents)} agents to validate")
        
        if args.performance_only:
            # Performance validation only
            generation_time, under_1s = validate_generation_performance(agents, args.templates)
            print(f"[TIME] Generation time: {generation_time:.3f}s")
            
            if under_1s:
                print("[PASS] Performance requirement met (<1s generation)")
                return 0
            else:
                print("[FAIL] Performance requirement failed (>=1s generation)")
                return 1
        
        # Full pattern validation
        validator = PatternValidator()
        generator = Generator(args.templates)
        
        total_errors = 0
        
        # Validate each agent
        for agent_id, (metadata, prompt) in agents.items():
            print(f"\n[AGENT] Validating agent: {agent_id}")
            
            # Generate code
            agent_code = generator.render_agent_node(metadata, prompt)
            
            # Validate patterns
            errors = validator.validate_agent_code(agent_code, metadata)
            
            if errors:
                print(f"  [FAIL] {len(errors)} pattern violations:")
                for error in errors:
                    print(f"    - {error}")
                total_errors += len(errors)
            else:
                print("  [PASS] All patterns valid")
        
        # Validate FastAPI app
        print(f"\n[APP] Validating FastAPI application")
        app_code = generator.render_fastapi_app(agents)
        has_parallel = any(metadata.parallel for metadata, _ in agents.values())
        app_errors = validator.validate_app_code(app_code, has_parallel)
        
        if app_errors:
            print(f"  [FAIL] {len(app_errors)} pattern violations:")
            for error in app_errors:
                print(f"    - {error}")
            total_errors += len(app_errors)
        else:
            print("  [PASS] All patterns valid")
        
        # Validate utils
        print(f"\n[UTILS] Validating utilities")
        utils_code = generator.render_utils()
        utils_errors = validator.validate_utils_code(utils_code)
        
        if utils_errors:
            print(f"  [FAIL] {len(utils_errors)} pattern violations:")
            for error in utils_errors:
                print(f"    - {error}")
            total_errors += len(utils_errors)
        else:
            print("  [PASS] All patterns valid")
        
        # Performance validation
        print(f"\n[PERF] Validating performance requirements")
        generation_time, under_1s = validate_generation_performance(agents, args.templates)
        print(f"  Generation time: {generation_time:.3f}s")
        
        if not under_1s:
            print("  [FAIL] Performance requirement failed (>=1s generation)")
            total_errors += 1
        else:
            print("  [PASS] Performance requirement met (<1s generation)")
        
        # Summary
        print(f"\n[SUMMARY] Validation Summary")
        print(f"  Agents validated: {len(agents)}")
        print(f"  Total violations: {total_errors}")
        
        if total_errors == 0:
            print("[SUCCESS] All pattern validations passed!")
            return 0
        else:
            print(f"[ERROR] {total_errors} pattern violations found")
            return 1
    
    except Exception as e:
        print(f"[ERROR] Validation failed: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())