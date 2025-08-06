# Development Environment Setup

This project combines PocketFlow (minimalist LLM framework) with additional frameworks for building AI agent applications.

## Quick Start

### Windows
```bash
# 1. Create and activate virtual environment
python -m venv venv
.\venv\Scripts\activate

# Or use the helper script:
activate.bat

# 2. Install dependencies
pip install -r requirements.txt

# 3. Install project in development mode (optional)
pip install -e .
```

### macOS/Linux
```bash
# 1. Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Install project in development mode (optional)
pip install -e .
```

## Running Tests
```bash
# Run all tests
pytest tests/

# Run with coverage
pytest tests/ --cov=pocketflow

# Run specific test
pytest tests/test_flow_basic.py
```

## Adding Dependencies

Edit `requirements.txt` to add your project-specific dependencies. Common additions:

```bash
# For OpenAI
openai>=1.0.0

# For Anthropic Claude
anthropic>=0.20.0

# For Google Gemini
google-generativeai>=0.3.0
```

Then reinstall:
```bash
pip install -r requirements.txt
```

## Project Structure

```
.
├── venv/                 # Virtual environment (git-ignored)
├── pocketflow/          # Core 100-line framework
├── cookbook/            # 40+ example implementations
├── tests/               # Test suite
├── CLAUDE.md           # AI assistant guidance
├── requirements.txt    # Project dependencies
└── activate.bat        # Windows venv helper
```

## Next Steps

1. Choose relevant cookbook examples for your use case
2. Create your project structure following the pattern in CLAUDE.md
3. Start with a simple flow and iterate