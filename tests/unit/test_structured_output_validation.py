"""Tests for structured output validation edge cases and scenarios."""

import pytest
from generated.stateless_agent import parse_structured_output, ValidationError


class TestYAMLParsingEdgeCases:
    """Test edge cases for YAML parsing and validation."""
    
    def test_multiple_yaml_blocks_uses_first(self):
        """Test that multiple YAML blocks use the first one."""
        llm_response = """
        First analysis:
        ```yaml
        status: completed
        content: First result
        summary: First analysis
        ```
        
        Alternative analysis:
        ```yaml
        status: failed
        content: Second result
        summary: Second analysis
        ```
        """
        
        result = parse_structured_output(llm_response)
        
        assert result["status"] == "completed"
        assert result["content"] == "First result"
    
    def test_yaml_block_with_comments(self):
        """Test YAML block with comments is parsed correctly."""
        llm_response = """
        ```yaml
        # Status of the execution
        status: completed
        # Main content output
        content: Task completed successfully
        # Brief summary
        summary: Analysis finished
        # Additional metadata
        metadata:
          # Number of items processed
          items_processed: 42
        ```
        """
        
        result = parse_structured_output(llm_response)
        
        assert result["status"] == "completed"
        assert result["content"] == "Task completed successfully"
        assert result["metadata"]["items_processed"] == 42
    
    def test_yaml_with_special_characters(self):
        """Test YAML containing special characters and escaping."""
        llm_response = """
        ```yaml
        status: completed
        content: |
          Analysis contains: quotes "like this"
          And symbols: @ # $ % ^ & * ( )
          Plus newlines and tabs	here
        summary: Special character handling test
        metadata:
          special_chars: "!@#$%^&*()"
          unicode: "café naïve résumé"
        ```
        """
        
        result = parse_structured_output(llm_response)
        
        assert "quotes" in result["content"]
        assert "symbols" in result["content"]
        assert result["metadata"]["special_chars"] == "!@#$%^&*()"
        assert result["metadata"]["unicode"] == "café naïve résumé"
    
    def test_deeply_nested_yaml_structure(self):
        """Test parsing deeply nested YAML structures."""
        llm_response = """
        ```yaml
        status: completed
        content: Complex nested analysis
        summary: Multi-level data structure
        metadata:
          analysis:
            results:
              categories:
                - name: category_a
                  items:
                    - id: 1
                      value: "item1"
                    - id: 2
                      value: "item2"
                - name: category_b
                  items:
                    - id: 3
                      value: "item3"
          statistics:
            total_items: 3
            categories_found: 2
        ```
        """
        
        result = parse_structured_output(llm_response)
        
        assert result["status"] == "completed"
        assert len(result["metadata"]["analysis"]["results"]["categories"]) == 2
        assert result["metadata"]["statistics"]["total_items"] == 3
        
        # Check nested structure
        first_category = result["metadata"]["analysis"]["results"]["categories"][0]
        assert first_category["name"] == "category_a"
        assert len(first_category["items"]) == 2
    
    def test_yaml_with_boolean_and_null_values(self):
        """Test YAML with various data types including booleans and nulls."""
        llm_response = """
        ```yaml
        status: completed
        content: Mixed data types test
        summary: Boolean and null handling
        metadata:
          success: true
          failed: false
          optional_field: null
          empty_field: 
          numeric_field: 3.14159
          integer_field: 42
        ```
        """
        
        result = parse_structured_output(llm_response)
        
        assert result["metadata"]["success"] is True
        assert result["metadata"]["failed"] is False
        assert result["metadata"]["optional_field"] is None
        assert result["metadata"]["empty_field"] is None
        assert result["metadata"]["numeric_field"] == 3.14159
        assert result["metadata"]["integer_field"] == 42
    
    def test_yaml_parsing_with_inconsistent_indentation(self):
        """Test that inconsistent indentation causes parsing error."""
        llm_response = """
        ```yaml
        status: completed
        content: Indentation test
          summary: Bad indentation
        metadata:
            good_field: value
          bad_field: value
        ```
        """
        
        with pytest.raises(ValidationError, match="YAML parsing error"):
            parse_structured_output(llm_response)
    
    def test_yaml_with_duplicate_keys(self):
        """Test behavior with duplicate YAML keys."""
        llm_response = """
        ```yaml
        status: completed
        content: First content
        content: Second content
        summary: Duplicate key test
        ```
        """
        
        result = parse_structured_output(llm_response)
        
        # YAML spec: last value wins for duplicate keys
        assert result["content"] == "Second content"
    
    def test_unterminated_yaml_block(self):
        """Test error handling for unterminated YAML block."""
        llm_response = """
        Here's the analysis:
        ```yaml
        status: completed
        content: This block is not terminated
        summary: Missing closing backticks
        """
        
        with pytest.raises(ValidationError, match="Unterminated YAML code block"):
            parse_structured_output(llm_response)
    
    def test_yaml_block_inside_text(self):
        """Test finding YAML block embedded in larger text."""
        llm_response = """
        Let me analyze this step by step.
        
        First, I'll examine the requirements. Based on my analysis,
        here are the results:
        
        ```yaml
        status: completed
        content: |
          After careful analysis, I found several key points:
          1. The system meets requirements
          2. Performance is within acceptable limits
          3. Security measures are adequate
        summary: Comprehensive analysis completed successfully
        metadata:
          analysis_duration: "5 minutes"
          confidence_level: "high"
        ```
        
        This completes my analysis. Let me know if you need
        any clarification on these results.
        """
        
        result = parse_structured_output(llm_response)
        
        assert result["status"] == "completed"
        assert "key points" in result["content"]
        assert result["metadata"]["confidence_level"] == "high"
    
    def test_yaml_with_very_long_content(self):
        """Test parsing YAML with very long content fields."""
        long_content = "Very long content. " * 1000  # 20,000 characters
        
        llm_response = f"""
        ```yaml
        status: completed
        content: |
          {long_content}
        summary: Long content test
        ```
        """
        
        result = parse_structured_output(llm_response)
        
        assert result["status"] == "completed"
        assert len(result["content"]) > 19000
        assert "Very long content." in result["content"]
    
    def test_yaml_parsing_performance(self):
        """Test that YAML parsing completes quickly for reasonable inputs.""" 
        import time
        
        llm_response = """
        ```yaml
        status: completed
        content: Performance test content
        summary: Speed test
        metadata:
          items: """ + str(list(range(1000))) + """
        ```
        """
        
        start_time = time.time()
        result = parse_structured_output(llm_response)
        end_time = time.time()
        
        parsing_time = end_time - start_time
        assert parsing_time < 0.1  # Should parse in under 100ms
        assert result["status"] == "completed"
        assert len(result["metadata"]["items"]) == 1000


class TestValidationErrorMessages:
    """Test that validation error messages are clear and helpful."""
    
    def test_clear_error_for_missing_yaml_block(self):
        """Test clear error message when YAML block is missing."""
        llm_response = "Just plain text with no YAML formatting."
        
        try:
            parse_structured_output(llm_response)
            assert False, "Should have raised ValidationError"
        except ValidationError as e:
            error_msg = str(e)
            assert "No YAML code block found" in error_msg
            assert "llm response" in error_msg.lower()
    
    def test_clear_error_for_yaml_syntax_issues(self):
        """Test clear error messages for YAML syntax problems."""
        llm_response = """
        ```yaml
        status: completed
        content: "unterminated string
        summary: This will fail
        ```
        """
        
        try:
            parse_structured_output(llm_response)
            assert False, "Should have raised ValidationError"
        except ValidationError as e:
            error_msg = str(e)
            assert "YAML parsing error" in error_msg
    
    def test_clear_error_for_non_dict_result(self):
        """Test clear error when YAML doesn't parse to dictionary."""
        llm_response = """
        ```yaml
        - item1
        - item2
        - item3
        ```
        """
        
        try:
            parse_structured_output(llm_response)
            assert False, "Should have raised ValidationError"
        except ValidationError as e:
            error_msg = str(e)
            assert "YAML must parse to a dictionary" in error_msg
    
    def test_clear_error_for_null_result(self):
        """Test clear error when YAML parsing results in None."""
        llm_response = """
        ```yaml
        # Just a comment, no actual content
        ```
        """
        
        try:
            parse_structured_output(llm_response)
            assert False, "Should have raised ValidationError"
        except ValidationError as e:
            error_msg = str(e)
            assert "YAML parsing resulted in None" in error_msg


class TestRobustnessAndResilience:
    """Test robustness against various malformed inputs."""
    
    def test_handles_mixed_line_endings(self):
        """Test handling different line ending formats."""
        # Mix of \n, \r\n, and \r
        llm_response = "```yaml\nstatus: completed\r\ncontent: Mixed line endings\rsummary: Test\n```"
        
        result = parse_structured_output(llm_response)
        
        assert result["status"] == "completed"
        assert result["content"] == "Mixed line endings"
    
    def test_handles_extra_whitespace_around_yaml(self):
        """Test handling extra whitespace around YAML block."""
        llm_response = """
        
            ```yaml    
            
            status: completed
            content: Extra whitespace test
            summary: Whitespace handling
            
            ```
            
        """
        
        result = parse_structured_output(llm_response)
        
        assert result["status"] == "completed"
        assert result["content"] == "Extra whitespace test"
    
    def test_handles_yaml_with_tabs(self):
        """Test handling YAML with tab characters."""
        llm_response = """
        ```yaml
        status:\tcompleted
        content:\tTab character test
        summary:\tHandling tabs
        metadata:
        \tfield1:\tvalue1
        \tfield2:\tvalue2
        ```
        """
        
        result = parse_structured_output(llm_response)
        
        assert result["status"] == "completed"
        assert "Tab character" in result["content"]
        assert result["metadata"]["field1"] == "value1"
    
    def test_handles_unicode_content(self):
        """Test handling Unicode characters in YAML."""
        llm_response = """
        ```yaml
        status: completed
        content: |
          Unicode test: 🚀 🎯 ✅
          Chinese: 你好世界
          Arabic: مرحبا بالعالم
          Emoji: 😀 😎 🤖
        summary: Unicode character support test
        ```
        """
        
        result = parse_structured_output(llm_response)
        
        assert result["status"] == "completed"
        assert "🚀" in result["content"]
        assert "你好世界" in result["content"]
        assert "مرحبا بالعالم" in result["content"]
        assert "🤖" in result["content"]
    
    def test_handles_very_nested_structures(self):
        """Test handling deeply nested YAML structures."""
        nested_yaml = """
        ```yaml
        status: completed
        content: Deep nesting test
        summary: Nested structure validation
        metadata:
          level1:
            level2:
              level3:
                level4:
                  level5:
                    deep_value: "Found it!"
        ```
        """
        
        result = parse_structured_output(nested_yaml)
        
        deep_value = result["metadata"]["level1"]["level2"]["level3"]["level4"]["level5"]["deep_value"]
        assert deep_value == "Found it!"