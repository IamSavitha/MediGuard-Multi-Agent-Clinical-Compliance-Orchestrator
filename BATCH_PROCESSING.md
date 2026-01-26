# Batch Processing Guide

MediGuard supports processing hundreds of documents in batch with parallel processing for improved performance.

## Features

- ✅ **Parallel Processing**: Process multiple documents simultaneously
- ✅ **Progress Tracking**: Real-time progress updates
- ✅ **Error Handling**: Individual document failures don't stop the batch
- ✅ **Multiple Input Formats**: JSON files or directories of text files
- ✅ **Comprehensive Results**: Summary statistics and detailed results

## Usage Methods

### 1. Command Line Interface (CLI)

#### Process from JSON File

```bash
mediguard batch-process \
  --input data/sample_batch.json \
  --output results.json \
  --workers 4
```

#### Process from Directory

```bash
mediguard batch-process \
  --input data/sample_claims/ \
  --output results.json \
  --format directory \
  --workers 4
```

**Options:**
- `--input, -i`: Input JSON file or directory path (required)
- `--output, -o`: Output JSON file path (required)
- `--workers, -w`: Number of parallel workers (default: 4)
- `--format, -f`: Input format: `json` or `directory` (default: `json`)

### 2. Python API

```python
from mediaguard.orchestrator import MediGuardOrchestrator
import json

# Initialize orchestrator
orchestrator = MediGuardOrchestrator()

# Load documents
with open("documents.json", "r") as f:
    documents = json.load(f)

# Process batch
batch_result = orchestrator.process_batch(
    documents=documents,
    max_workers=4,  # Number of parallel workers
    show_progress=True  # Show progress bar
)

# Access results
print(f"Total: {batch_result['summary']['total']}")
print(f"Successful: {batch_result['summary']['successful']}")
print(f"Failed: {batch_result['summary']['failed']}")

# Individual results
for result in batch_result['results']:
    print(f"Document {result['document_id']}: {result['status']}")
```

### 3. Streamlit UI

1. Open the Streamlit app: `streamlit run app.py`
2. Go to the "📝 Document Processing" tab
3. Select "Batch Processing" mode
4. Choose input method:
   - **JSON File**: Upload a JSON file with documents
   - **Directory**: Enter path to directory containing `.txt` files
5. Adjust parallel workers (1-10)
6. Click "🚀 Process Batch"
7. View results and download JSON output

## Input Format

### JSON File Format

The JSON file should contain a list of documents:

```json
[
  {
    "id": "claim_001",
    "text": "Patient: John Doe\nDOB: 03/15/1980\nTreatment: MRI scan...",
    "document_type": "CLAIM",
    "patient_metadata": {
      "insurance_plan": "Standard Plan"
    }
  },
  {
    "id": "claim_002",
    "text": "Patient: Jane Smith\nDOB: 07/22/1975\nTreatment: Physical exam...",
    "document_type": "CLAIM"
  }
]
```

**Required Fields:**
- `id` (str): Unique identifier for the document
- `text` (str): Document text content

**Optional Fields:**
- `document_type` (str): Pre-classified document type (e.g., "CLAIM", "PATIENT_REPORT")
- `patient_metadata` (dict): Patient information dictionary

### Directory Format

Place `.txt` files in a directory. Each file will be processed as a separate document:
- File name (without extension) becomes the document `id`
- File content becomes the document `text`

## Output Format

The batch processing returns a dictionary with:

```python
{
  "results": [
    {
      "document_id": "claim_001",
      "timestamp": "2026-01-24T14:30:00",
      "document_type": "CLAIM",
      "classification": {...},
      "validation": {...},
      "compliance": {...},
      "status": "completed"
    },
    ...
  ],
  "summary": {
    "total": 100,
    "successful": 98,
    "failed": 2,
    "success_rate": 0.98,
    "timestamp": "2026-01-24T14:35:00"
  },
  "errors": [
    {
      "document_id": "claim_005",
      "status": "error",
      "error": "Error message here",
      "timestamp": "2026-01-24T14:32:00"
    },
    ...
  ]
}
```

## Performance Tips

1. **Parallel Workers**: 
   - Start with 4 workers for most cases
   - Increase to 8-10 for large batches (100+ documents)
   - Don't exceed your system's CPU cores

2. **LLM Provider**:
   - Local Ollama: Limited by your CPU/GPU
   - OpenAI API: Limited by rate limits (use fewer workers)

3. **Batch Size**:
   - Process in batches of 100-500 documents
   - For very large datasets (1000+), split into multiple batches

4. **Error Handling**:
   - Individual document failures don't stop the batch
   - Check `errors` array in results for failed documents
   - Retry failed documents individually if needed

## Example: Processing 100 Documents

```python
from mediaguard.orchestrator import MediGuardOrchestrator
import json

# Initialize
orchestrator = MediGuardOrchestrator()

# Load 100 documents
with open("large_batch.json", "r") as f:
    documents = json.load(f)

# Process with 8 parallel workers
result = orchestrator.process_batch(
    documents=documents,
    max_workers=8,
    show_progress=True
)

# Save results
with open("batch_results.json", "w") as f:
    json.dump(result, f, indent=2)

print(f"Processed {result['summary']['successful']}/{result['summary']['total']} documents")
```

## See Also

- `examples/batch_processing_example.py` - Complete examples
- `data/sample_batch.json` - Sample batch file format
- `QUICKSTART.md` - General usage guide
