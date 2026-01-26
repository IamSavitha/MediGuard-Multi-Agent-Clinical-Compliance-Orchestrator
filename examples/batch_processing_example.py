"""
Example: Batch Processing Multiple Documents

This example demonstrates how to process hundreds of documents
in batch using the MediGuard orchestrator.
"""

from mediaguard.orchestrator import MediGuardOrchestrator
import json
from pathlib import Path

def example_batch_from_json():
    """Example: Process documents from a JSON file."""
    print("=" * 60)
    print("Batch Processing Example: JSON File")
    print("=" * 60)
    
    # Initialize orchestrator
    orchestrator = MediGuardOrchestrator()
    
    # Load documents from JSON file
    json_path = Path(__file__).parent.parent / "data" / "sample_batch.json"
    
    with open(json_path, "r") as f:
        documents = json.load(f)
    
    print(f"\nLoaded {len(documents)} documents from JSON file")
    
    # Process batch
    print("\nProcessing batch...")
    batch_result = orchestrator.process_batch(
        documents=documents,
        max_workers=4,  # Process 4 documents in parallel
        show_progress=True
    )
    
    # Display summary
    summary = batch_result["summary"]
    print(f"\n{'=' * 60}")
    print("Batch Processing Summary")
    print(f"{'=' * 60}")
    print(f"Total Documents: {summary['total']}")
    print(f"Successful: {summary['successful']}")
    print(f"Failed: {summary['failed']}")
    print(f"Success Rate: {summary['success_rate']:.2%}")
    
    # Display errors if any
    if batch_result["errors"]:
        print(f"\n⚠️  {len(batch_result['errors'])} documents failed:")
        for error in batch_result["errors"]:
            print(f"  - {error.get('document_id')}: {error.get('error')}")
    
    # Save results
    output_path = Path(__file__).parent.parent / "batch_results.json"
    with open(output_path, "w") as f:
        json.dump(batch_result, f, indent=2)
    
    print(f"\n✅ Results saved to: {output_path}")
    
    return batch_result


def example_batch_from_directory():
    """Example: Process documents from a directory of text files."""
    print("\n" + "=" * 60)
    print("Batch Processing Example: Directory")
    print("=" * 60)
    
    # Initialize orchestrator
    orchestrator = MediGuardOrchestrator()
    
    # Load documents from directory
    sample_dir = Path(__file__).parent.parent / "data" / "sample_claims"
    
    documents = []
    for file_path in sample_dir.glob("*.txt"):
        with open(file_path, "r") as f:
            documents.append({
                "id": file_path.stem,
                "text": f.read()
            })
    
    print(f"\nLoaded {len(documents)} documents from directory")
    
    # Process batch
    print("\nProcessing batch...")
    batch_result = orchestrator.process_batch(
        documents=documents,
        max_workers=2,  # Process 2 documents in parallel
        show_progress=True
    )
    
    # Display summary
    summary = batch_result["summary"]
    print(f"\n{'=' * 60}")
    print("Batch Processing Summary")
    print(f"{'=' * 60}")
    print(f"Total Documents: {summary['total']}")
    print(f"Successful: {summary['successful']}")
    print(f"Failed: {summary['failed']}")
    print(f"Success Rate: {summary['success_rate']:.2%}")
    
    return batch_result


def example_large_batch():
    """Example: Process a large batch (100+ documents)."""
    print("\n" + "=" * 60)
    print("Batch Processing Example: Large Batch (100 documents)")
    print("=" * 60)
    
    # Initialize orchestrator
    orchestrator = MediGuardOrchestrator()
    
    # Generate sample documents
    documents = []
    for i in range(100):
        documents.append({
            "id": f"claim_{i+1:03d}",
            "text": f"Patient: Patient {i+1}\nDOB: 01/01/1980\nTreatment: Medical procedure {i+1}\nCost: ${100 + i * 10}.00\nInsurance: Standard Plan",
            "document_type": "CLAIM"
        })
    
    print(f"\nGenerated {len(documents)} sample documents")
    
    # Process batch with more workers for better performance
    print("\nProcessing large batch...")
    batch_result = orchestrator.process_batch(
        documents=documents,
        max_workers=8,  # Use more workers for large batches
        show_progress=True
    )
    
    # Display summary
    summary = batch_result["summary"]
    print(f"\n{'=' * 60}")
    print("Batch Processing Summary")
    print(f"{'=' * 60}")
    print(f"Total Documents: {summary['total']}")
    print(f"Successful: {summary['successful']}")
    print(f"Failed: {summary['failed']}")
    print(f"Success Rate: {summary['success_rate']:.2%}")
    
    return batch_result


if __name__ == "__main__":
    # Example 1: Process from JSON file
    example_batch_from_json()
    
    # Example 2: Process from directory
    # example_batch_from_directory()
    
    # Example 3: Process large batch
    # example_large_batch()
