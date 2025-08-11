# Multi-Model Prompt Engine

A pure Python prompt generation engine that supports multiple LLM formats (DeepSeek-R1, Gemma, Llama3) using JSON-based templates and Jinja2 rendering.

## Features

- **Multi-Model Support**: Unified interface for DeepSeek-R1, Gemma, and Llama3
- **JSON Template Management**: File-based template storage and organization
- **Hierarchical Composition**: Global → Tenant → Application level template merging
- **Jinja2 Rendering**: Flexible prompt formatting with template inheritance
- **Tenant Customization**: Organization-specific template overrides
- **RESTful API**: HTTP interface for prompt generation services
- **Hot Reload**: Development-friendly template reloading

## Quick Start

### Installation

```bash
# Clone repository
git clone <repository-url>
cd prompt_engine

# Create conda environment (Python 3.12 is recommended)
conda create -n prompt-bank python=3.12 -y
conda activate prompt-bank

# Install dependencies
pip install -r requirements.txt

# Run development server
python main.py

# Deactivate when done
# conda deactivate
```

### Usage

```python
from src.engine import PromptEngine
from src.models import PromptRequest, PromptType

# Initialize engine
engine = PromptEngine()

# Generate prompt
request = PromptRequest(
    model_id="deepseek-r1-0528-qwen3-8b",
    user_input="Hello world",
    prompt_type=PromptType.CHAT
)

response = engine.generate_prompt(request)
print(response.formatted_prompt)
```

### API Usage

```bash
# Generate prompt
curl -X POST "http://localhost:8800/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "model_id": "deepseek-r1-0528-qwen3-8b",
    "user_input": "Hello world",
    "prompt_type": "chat"
  }'

# Get supported models
curl "http://localhost:8800/models"

# Health check
curl "http://localhost:8800/health"
```

## Project Structure

```
prompt_engine/
├── src/                    # Source code
│   ├── engine.py          # Main prompt engine
│   ├── loader.py          # Template loader
│   ├── composer.py        # Template composer
│   ├── models.py          # Pydantic models
│   └── utils.py           # Utility functions
├── templates/             # Template files
│   ├── global/           # Global templates
│   ├── models/           # Model configurations
│   └── tenants/          # Tenant customizations
├── tests/                # Test suite
├── main.py               # FastAPI application
├── requirements.txt      # Python dependencies
├── Dockerfile           # Container configuration
└── docker-compose.yml   # Development setup
```

## Supported Models

| Model Family | Model ID | Max Context | Special Features |
|-------------|----------|-------------|------------------|
| DeepSeek-R1 | deepseek-r1-0528-qwen3-8b | 32,768 | Chinese support, reasoning |
| Gemma | gemma-2-9b-it | 8,192 | Instruction following |
| Llama3 | llama3-8b-instruct | 8,192 | Function calling |

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src

# Run specific test file
pytest tests/test_engine.py
```

### Template Development

```bash
# Hot reload templates (development)
curl -X POST "http://localhost:8800/reload"
```

### Docker Development

```bash
# Build and run with Docker Compose
docker-compose up --build

# Run in production mode
docker build -t prompt-engine .
docker run -p 8800:8800 prompt-engine
```

## Configuration

### Environment Variables

```bash
# Application settings
APP_HOST=0.0.0.0
APP_PORT=8800
APP_RELOAD=true

# Template settings
TEMPLATES_DIR=templates

# Logging
LOG_LEVEL=INFO
```

### Template Structure

Templates are organized in a hierarchical structure:

- **Global templates**: Base behavior, safety guidelines
- **Model configurations**: Model-specific tokens and settings
- **Tenant overrides**: Organization-specific customizations

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Run the test suite
6. Submit a pull request

## License

MIT License - see LICENSE file for details.
