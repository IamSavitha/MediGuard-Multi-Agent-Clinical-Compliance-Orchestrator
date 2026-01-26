# Streamlit UI Guide

## Quick Start

### 1. Install Streamlit

```bash
source venv/bin/activate
pip install streamlit
```

Or install all requirements:
```bash
pip install -r requirements.txt
```

### 2. Run the UI

```bash
streamlit run app.py
```

The app will open in your browser at `http://localhost:8501`

## Features

### 📝 Document Processing Tab

- **Text Input**: Enter medical documents directly
- **File Upload**: Upload `.txt` or `.json` files
- **Auto-classification**: Automatically detects document type
- **Real-time Results**: See classification, validation, and compliance results
- **Download Results**: Export results as JSON

### 📚 Policy Management Tab

- **Add Policies**: Add insurance policies to the vector database
- **Search Policies**: Search for relevant policies using semantic search
- **Metadata Support**: Add custom metadata to policies

### ℹ️ About Tab

- System information
- Configuration details
- Documentation links

## Usage Examples

### Example 1: Process a Medical Claim

1. Go to "Document Processing" tab
2. Click "Sample Claim 1" in the sidebar (or enter your own text)
3. Click "🚀 Process Document"
4. View results:
   - Classification (document type, confidence)
   - Policy Validation (coverage, co-pay)
   - Compliance Audit (PHI detection, bias detection)

### Example 2: Add a Policy

1. Go to "Policy Management" tab
2. Enter Policy ID: `POL-001`
3. Enter policy text
4. (Optional) Add metadata as JSON
5. Click "➕ Add Policy"

### Example 3: Search Policies

1. Go to "Policy Management" tab
2. Enter search query: "MRI scan coverage"
3. Adjust number of results
4. Click "🔍 Search"

## Configuration

The UI automatically uses your `.env` configuration:

- **LLM Provider**: Shows in sidebar (OpenAI or Ollama)
- **Model**: Shows current model being used
- **Vector Store**: Automatically initializes

## Tips

1. **First Time**: Click "🔄 Initialize System" in sidebar
2. **Sample Documents**: Use sidebar buttons to quickly load sample text
3. **View Details**: Expand sections to see detailed reasoning
4. **Download**: Save results as JSON for later analysis

## Troubleshooting

### UI doesn't load
- Make sure Streamlit is installed: `pip install streamlit`
- Check that port 8501 is available

### Errors initializing
- Check your `.env` file configuration
- Make sure Ollama is running if using Ollama: `ollama serve`
- Check that all dependencies are installed

### Slow responses
- Normal with Ollama (local inference is slower)
- Consider using a smaller model for faster responses

## Screenshots

The UI includes:
- Clean, modern design
- Color-coded metrics
- Expandable sections for details
- Real-time processing feedback
- Downloadable results

Enjoy exploring MediGuard! 🏥
