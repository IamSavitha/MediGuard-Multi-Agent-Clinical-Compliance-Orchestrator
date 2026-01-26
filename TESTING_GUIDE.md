# Testing Guide - MediGuard with Ollama/Llama

This guide explains how to test MediGuard using local Llama models via Ollama instead of OpenAI.

## Prerequisites

### 1. Install Ollama

**macOS:**
```bash
brew install ollama
# or download from https://ollama.ai
```

**Linux:**
```bash
curl -fsSL https://ollama.ai/install.sh | sh
```

**Windows:**
Download from https://ollama.ai

### 2. Start Ollama Service

```bash
ollama serve
```

This starts the Ollama server on `http://localhost:11434` (default).

### 3. Pull a Llama Model

```bash
# Recommended models (choose one):
ollama pull llama3.2        # Fast, good for testing
ollama pull llama3.1:8b    # Better quality
ollama pull mistral        # Alternative option
ollama pull qwen2.5        # Another good option
```

### 4. Install Python Dependencies

```bash
# Activate your virtual environment
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install new dependency
pip install langchain-ollama

# Or reinstall all requirements
pip install -r requirements.txt
```

## Configuration

### Update .env File

Edit your `.env` file (or create from `.env.example`):

```bash
# LLM Provider Configuration
# Options: "openai" or "ollama"
LLM_PROVIDER=ollama

# Ollama Configuration (only needed if LLM_PROVIDER=ollama)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2

# OpenAI Configuration (only needed if LLM_PROVIDER=openai)
# OPENAI_API_KEY=your_key_here
# OPENAI_MODEL=gpt-4o

# Vector Database (optional - falls back to in-memory if not set)
# PINECONE_API_KEY=your_key_here
# PINECONE_ENVIRONMENT=your_env
# PINECONE_INDEX_NAME=mediaguard
```

## Testing

### 1. Test PHI Detector Fix

The PHI detector bug has been fixed. Test it:

```bash
python examples/guardrails_example.py
```

This should now work without the `KeyError: 'ssn_no_dash'` error.

### 2. Test Basic Usage with Ollama

```bash
python examples/basic_usage.py
```

Expected output:
- Should initialize without OpenAI API errors
- Should process the claim using Llama model
- May take longer than OpenAI (local inference)
- Quality may vary depending on model size

### 3. Test RAG Example

```bash
python examples/rag_example.py
```

This tests:
- Vector store initialization
- Policy retrieval
- LLM-based policy validation

### 4. Test CLI

```bash
# Process a claim from file
python -m mediaguard.cli process --file data/sample_claims/claim_001.txt --pretty

# Process text directly
python -m mediaguard.cli process --text "Medical claim: MRI scan, $1,500" --pretty
```

### 5. Test Individual Components

#### Test Triage Agent
```python
from mediaguard.agents.triage_agent import TriageAgent

agent = TriageAgent()
result = agent.classify("Patient: John Doe. Treatment: MRI scan. Cost: $1,500")
print(result)
```

#### Test Policy Validator
```python
from mediaguard.agents.policy_validator import PolicyValidator

validator = PolicyValidator()
result = validator.validate_treatment(
    treatment_description="MRI scan of brain",
    claim_amount=1500.00
)
print(result)
```

#### Test Bias Detector
```python
from mediaguard.guardrails.bias_detector import BiasDetector

detector = BiasDetector()
result = detector.detect_bias({
    "is_covered": False,
    "coverage_percentage": 0
})
print(result)
```

#### Test PHI Detector
```python
from mediaguard.guardrails.phi_detector import PHIDetector

detector = PHIDetector()
text = """
Patient: John Doe
DOB: 01/15/1980
SSN: 123-45-6789
Phone: 555-123-4567
Email: john.doe@email.com
"""

result = detector.detect_phi(text)
print(result)
```

## Troubleshooting

### Issue: "Connection refused" or "Cannot connect to Ollama"

**Solution:**
1. Make sure Ollama is running: `ollama serve`
2. Check the base URL in `.env`: `OLLAMA_BASE_URL=http://localhost:11434`
3. Test connection: `curl http://localhost:11434/api/tags`

### Issue: "Model not found"

**Solution:**
1. List available models: `ollama list`
2. Pull the model: `ollama pull llama3.2`
3. Update `.env` with correct model name: `OLLAMA_MODEL=llama3.2`

### Issue: "langchain-ollama not installed"

**Solution:**
```bash
pip install langchain-ollama
```

### Issue: Slow responses

**Solution:**
- This is normal - local inference is slower than API calls
- Use a smaller/faster model: `ollama pull llama3.2` (instead of larger models)
- Consider using GPU if available

### Issue: Poor quality responses

**Solution:**
- Try a larger model: `ollama pull llama3.1:8b` or `llama3.1:70b`
- Adjust temperature in code (currently 0.1-0.2 for consistency)
- Some tasks may work better with OpenAI for production use

## Switching Back to OpenAI

To switch back to OpenAI:

1. Update `.env`:
```bash
LLM_PROVIDER=openai
OPENAI_API_KEY=your_key_here
OPENAI_MODEL=gpt-4o
```

2. Restart your application

## Performance Comparison

| Provider | Speed | Cost | Quality | Privacy |
|----------|-------|------|---------|---------|
| OpenAI   | Fast  | Paid | High    | API     |
| Ollama   | Slower| Free | Varies  | Local   |

## Next Steps

1. **Test with different models**: Try `llama3.1:8b`, `mistral`, `qwen2.5`
2. **Fine-tune prompts**: Adjust system prompts in agent files for better results
3. **Monitor performance**: Compare accuracy between OpenAI and Ollama
4. **Production considerations**: Use OpenAI for production, Ollama for development/testing

## Quick Ollama Test

With `LLM_PROVIDER=ollama` in `.env`, run:

```bash
python examples/basic_usage.py
```

Or verify setup:

```bash
python verify_installation.py
```
