# Quick Start Guide

Get up and running with MediGuard in 5 minutes!

## Prerequisites

- Python 3.9 or higher
- OpenAI API key
- (Optional) Pinecone API key for production vector database

## Installation

```bash
# Clone the repository
git clone <repository-url>
cd MediGuard-Multi-Agent-Clinical-Compliance-Orchestrator

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Configuration

1. Copy the example environment file:
```bash
cp .env.example .env
```

2. Edit `.env` and add your API keys:
```env
OPENAI_API_KEY=your_key_here
OPENAI_MODEL=gpt-4o
```

For production use with Pinecone:
```env
PINECONE_API_KEY=your_key_here
PINECONE_ENVIRONMENT=us-east-1
PINECONE_INDEX_NAME=mediguard-policies
```

## Quick Start

### Option 1: Using Python

```python
from mediaguard import MediGuardOrchestrator

# Initialize
orchestrator = MediGuardOrchestrator()

# Process a claim
claim_text = """
Patient: John Doe
Treatment: MRI scan of brain
Amount: $1,500.00
"""

result = orchestrator.process_claim(claim_text)
print(result)
```

### Option 2: Using CLI

```bash
# Process a claim from file
python -m mediaguard.cli process --file data/sample_claims/claim_001.txt --pretty

# Process text directly
python -m mediaguard.cli process --text "Medical claim: MRI scan, $1,500" --pretty
```

### Option 3: Run Examples

```bash
# Basic usage
python examples/basic_usage.py

# RAG example
python examples/rag_example.py

# Guardrails example
python examples/guardrails_example.py
```

## Setting Up Policies (RAG)

To enable policy validation with RAG:

```bash
# Load sample policies into vector database
python setup_policies.py
```

Or use the CLI:
```bash
python -m mediaguard.cli add-policy --file data/sample_policies/policy_001.json --id POL-001
```

## Testing

```bash
# Run all tests
pytest tests/

# Run specific test suite
pytest tests/test_agents.py
```

## Next Steps

1. **Customize Policies**: Add your own insurance policies to `data/sample_policies/`
2. **Extend Agents**: Modify agent behavior in `mediaguard/agents/`
3. **Add Tools**: Create custom tools in `mediaguard/tools/`
4. **Configure Guardrails**: Adjust PHI and bias detection in `mediaguard/guardrails/`

## Troubleshooting

### "OpenAI API key not found"
- Make sure you've set `OPENAI_API_KEY` in your `.env` file
- Or export it: `export OPENAI_API_KEY=your_key`

### "Vector store initialization failed"
- The system will fall back to in-memory storage automatically
- For production, set up Pinecone or Milvus

### Import errors
- Make sure you've activated your virtual environment
- Reinstall dependencies: `pip install -r requirements.txt`

## Support

For issues or questions, please refer to the main README.md or open an issue on GitHub.
