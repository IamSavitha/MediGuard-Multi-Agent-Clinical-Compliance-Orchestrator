"""
Command-line interface for MediGuard.
"""

import click
import json
from pathlib import Path
from mediaguard.orchestrator import MediGuardOrchestrator
from mediaguard.rag.vector_store import VectorStore
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.json import JSON

console = Console()


@click.group()
def cli():
    """MediGuard: Multi-Agent Clinical Compliance Orchestrator"""
    pass


@cli.command()
@click.option("--file", "-f", type=click.Path(exists=True), help="Path to document file")
@click.option("--text", "-t", help="Document text directly")
@click.option("--type", "-d", help="Document type (CLAIM, PATIENT_REPORT, etc.)")
@click.option("--output", "-o", type=click.Path(), help="Output file path")
@click.option("--pretty", is_flag=True, help="Pretty print output")
def process(file, text, type, output, pretty):
    """Process a document through the MediGuard system."""
    console.print("[bold blue]MediGuard[/bold blue] - Processing document...")
    
    # Get document text
    if file:
        with open(file, "r") as f:
            document_text = f.read()
    elif text:
        document_text = text
    else:
        console.print("[red]Error:[/red] Either --file or --text must be provided")
        return
    
    # Initialize orchestrator
    try:
        orchestrator = MediGuardOrchestrator()
    except Exception as e:
        console.print(f"[red]Error initializing orchestrator:[/red] {e}")
        return
    
    # Process document
    console.print("[yellow]Processing...[/yellow]")
    result = orchestrator.process_document(
        document_text=document_text,
        document_type=type
    )
    
    # Display results
    if pretty:
        _display_results_pretty(result)
    else:
        console.print(json.dumps(result, indent=2))
    
    # Save to file if requested
    if output:
        with open(output, "w") as f:
            json.dump(result, f, indent=2)
        console.print(f"[green]Results saved to:[/green] {output}")


@cli.command()
@click.option("--file", "-f", type=click.Path(exists=True), required=True, help="Path to policy file")
@click.option("--id", "-i", required=True, help="Policy ID")
@click.option("--metadata", "-m", help="Metadata JSON string")
def add_policy(file, id, metadata):
    """Add a policy to the vector database."""
    console.print(f"[bold blue]Adding policy:[/bold blue] {id}")
    
    # Read policy file
    with open(file, "r") as f:
        policy_text = f.read()
    
    # Parse metadata
    policy_metadata = {}
    if metadata:
        try:
            policy_metadata = json.loads(metadata)
        except json.JSONDecodeError:
            console.print("[red]Error:[/red] Invalid JSON metadata")
            return
    
    # Initialize vector store
    try:
        vector_store = VectorStore()
        vector_store.add_policy(id, policy_text, policy_metadata)
        console.print(f"[green]Policy added successfully:[/green] {id}")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")


@cli.command()
@click.option("--query", "-q", required=True, help="Search query")
@click.option("--top-k", "-k", default=5, help="Number of results")
def search_policies(query, top_k):
    """Search for policies in the vector database."""
    console.print(f"[bold blue]Searching policies:[/bold blue] {query}")
    
    try:
        vector_store = VectorStore()
        results = vector_store.search_similar(query, top_k=top_k)
        
        if not results:
            console.print("[yellow]No results found[/yellow]")
            return
        
        # Display results
        table = Table(title="Search Results")
        table.add_column("Policy ID", style="cyan")
        table.add_column("Score", style="green")
        table.add_column("Metadata", style="yellow")
        
        for result in results:
            metadata_str = json.dumps(result.get("metadata", {}), indent=2)[:100]
            table.add_row(
                result.get("id", "N/A"),
                f"{result.get('score', 0):.4f}",
                metadata_str
            )
        
        console.print(table)
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")


@cli.command()
@click.option("--input", "-i", type=click.Path(exists=True), required=True, help="Input JSON file or directory containing documents")
@click.option("--output", "-o", type=click.Path(), required=True, help="Output JSON file path")
@click.option("--workers", "-w", default=4, help="Number of parallel workers (default: 4)")
@click.option("--format", "-f", type=click.Choice(["json", "directory"]), default="json", help="Input format: 'json' for JSON file, 'directory' for directory of text files")
def batch_process(input, output, workers, format):
    """Process multiple documents in batch."""
    console.print(f"[bold blue]MediGuard[/bold blue] - Batch Processing")
    console.print(f"[yellow]Input:[/yellow] {input}")
    console.print(f"[yellow]Output:[/yellow] {output}")
    console.print(f"[yellow]Workers:[/yellow] {workers}")
    
    # Initialize orchestrator
    try:
        orchestrator = MediGuardOrchestrator()
    except Exception as e:
        console.print(f"[red]Error initializing orchestrator:[/red] {e}")
        return
    
    # Load documents
    documents = []
    
    if format == "json":
        # Load from JSON file
        try:
            with open(input, "r") as f:
                data = json.load(f)
                if isinstance(data, list):
                    documents = data
                elif isinstance(data, dict) and "documents" in data:
                    documents = data["documents"]
                else:
                    console.print("[red]Error:[/red] JSON file must contain a list of documents or a dict with 'documents' key")
                    return
        except json.JSONDecodeError as e:
            console.print(f"[red]Error parsing JSON:[/red] {e}")
            return
        except Exception as e:
            console.print(f"[red]Error reading file:[/red] {e}")
            return
    else:
        # Load from directory
        from pathlib import Path
        input_path = Path(input)
        if not input_path.is_dir():
            console.print(f"[red]Error:[/red] {input} is not a directory")
            return
        
        for file_path in input_path.glob("*.txt"):
            try:
                with open(file_path, "r") as f:
                    doc_text = f.read()
                    documents.append({
                        "id": file_path.stem,
                        "text": doc_text
                    })
            except Exception as e:
                console.print(f"[yellow]Warning:[/yellow] Failed to read {file_path}: {e}")
    
    if not documents:
        console.print("[red]Error:[/red] No documents found to process")
        return
    
    console.print(f"[green]Loaded {len(documents)} documents[/green]")
    
    # Process batch
    console.print("[yellow]Processing...[/yellow]")
    try:
        batch_result = orchestrator.process_batch(
            documents=documents,
            max_workers=workers,
            show_progress=True
        )
        
        # Save results
        with open(output, "w") as f:
            json.dump(batch_result, f, indent=2)
        
        # Display summary
        summary = batch_result["summary"]
        console.print("\n[bold green]Batch Processing Complete![/bold green]")
        console.print(Panel(
            f"[bold]Total:[/bold] {summary['total']}\n"
            f"[bold]Successful:[/bold] {summary['successful']}\n"
            f"[bold]Failed:[/bold] {summary['failed']}\n"
            f"[bold]Success Rate:[/bold] {summary['success_rate']:.2%}",
            title="Summary",
            border_style="green"
        ))
        
        if batch_result["errors"]:
            console.print(f"[yellow]Warning:[/yellow] {len(batch_result['errors'])} documents failed processing")
            for error in batch_result["errors"][:5]:  # Show first 5 errors
                console.print(f"  - {error.get('document_id', 'unknown')}: {error.get('error', 'Unknown error')}")
            if len(batch_result["errors"]) > 5:
                console.print(f"  ... and {len(batch_result['errors']) - 5} more")
        
        console.print(f"[green]Results saved to:[/green] {output}")
        
    except Exception as e:
        console.print(f"[red]Error during batch processing:[/red] {e}")
        import traceback
        console.print(traceback.format_exc())


def _display_results_pretty(result: dict):
    """Display results in a pretty format."""
    # Classification
    if "classification" in result:
        classification = result["classification"]
        console.print(Panel(
            f"[bold]Type:[/bold] {classification.get('document_type_label', 'N/A')}\n"
            f"[bold]Confidence:[/bold] {classification.get('confidence', 0):.2%}\n"
            f"[bold]Reasoning:[/bold] {classification.get('reasoning', 'N/A')}",
            title="Classification",
            border_style="blue"
        ))
    
    # Validation
    if "validation" in result and not result["validation"].get("skipped"):
        validation = result["validation"]
        copay_amount = validation.get('copay_amount')
        copay_str = f"${copay_amount:.2f}" if copay_amount is not None else "N/A"
        console.print(Panel(
            f"[bold]Covered:[/bold] {'Yes' if validation.get('is_covered') else 'No'}\n"
            f"[bold]Coverage:[/bold] {validation.get('coverage_percentage', 0)}%\n"
            f"[bold]Co-pay:[/bold] {copay_str}\n"
            f"[bold]Reasoning:[/bold] {validation.get('reasoning', 'N/A')}",
            title="Policy Validation",
            border_style="green"
        ))
    
    # Compliance
    if "compliance" in result:
        compliance = result["compliance"]
        phi_check = compliance.get("phi_check", {})
        bias_check = compliance.get("bias_check", {})
        
        compliance_text = ""
        
        if phi_check:
            compliance_text += f"[bold]PHI Detected:[/bold] {phi_check.get('total_phi_detections', 0)}\n"
            compliance_text += f"[bold]Risk Level:[/bold] {phi_check.get('risk_level', 'N/A')}\n"
        
        if bias_check:
            compliance_text += f"\n[bold]Bias Detected:[/bold] {'Yes' if bias_check.get('has_bias') else 'No'}\n"
            if bias_check.get("has_bias"):
                compliance_text += f"[bold]Severity:[/bold] {bias_check.get('bias_severity', 'N/A')}\n"
        
        if compliance_text:
            console.print(Panel(
                compliance_text,
                title="Compliance Audit",
                border_style="yellow"
            ))
    
    # Errors
    if "errors" in result and result["errors"]:
        console.print(Panel(
            "\n".join(result["errors"]),
            title="Errors",
            border_style="red"
        ))


if __name__ == "__main__":
    cli()
