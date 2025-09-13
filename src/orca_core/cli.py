"""Command-line interface for Orca Core."""

import csv
import glob
import json
import sys
from pathlib import Path
from typing import Any

import orjson
import typer
from rich.console import Console

from .core.explainer import explain_decision
from .engine import evaluate_rules
from .llm.adapter import explain_decision as llm_explain_decision
from .models import DecisionRequest

app = typer.Typer(help="Orca Core Decision Engine CLI")
console = Console()


@app.command()
def decide(
    json_input: str = typer.Argument(
        None, help="JSON string with decision request data (or '-' for stdin)"
    ),
    rail: str = typer.Option(None, "--rail", help="Override rail type (Card or ACH)"),
    channel: str = typer.Option(None, "--channel", help="Override channel (online or pos)"),
    use_ml: bool = typer.Option(True, "--use-ml/--no-ml", help="Enable/disable ML scoring"),
    explain: str = typer.Option(
        None, "--explain", help="Generate explanation (merchant|developer)"
    ),
) -> None:
    """
    Evaluate a decision request and return the response.

    Examples:
        orca-core decide '{"cart_total": 750.0, "currency": "USD"}'
        orca-core decide -  # Read from stdin
        echo '{"cart_total": 750.0}' | orca-core decide -
    """
    try:
        # Handle stdin input
        if json_input == "-" or json_input is None:
            json_input = sys.stdin.read().strip()

        if not json_input:
            console.print("[red]No JSON input provided[/red]")
            raise typer.Exit(1)

        # Parse JSON input
        data: dict[str, Any] = orjson.loads(json_input)

        # Apply rail and channel overrides if provided
        if rail:
            data["rail"] = rail
        if channel:
            data["channel"] = channel

        # Create request model
        request = DecisionRequest(**data)

        # Evaluate rules
        response = evaluate_rules(request, use_ml=use_ml)

        # Output compact JSON
        output = orjson.dumps(response.model_dump(), option=orjson.OPT_SORT_KEYS)
        console.print(output.decode())

        # Generate explanation if requested
        if explain:
            if explain not in ["merchant", "developer"]:
                console.print(
                    f"[red]Invalid explain style: {explain}. Use 'merchant' or 'developer'[/red]"
                )
                raise typer.Exit(1)

            try:
                explanation = llm_explain_decision(response, explain)  # type: ignore
                console.print(f"\n[bold]Explanation ({explain}):[/bold]")
                console.print(explanation)
            except Exception as e:
                console.print(f"[red]Error generating explanation: {e}[/red]")
                raise typer.Exit(1) from e

    except orjson.JSONDecodeError as e:
        console.print(f"[red]Invalid JSON: {e}[/red]")
        raise typer.Exit(1) from e
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1) from e


@app.command()
def decide_file(
    file_path: str = typer.Argument(..., help="Path to JSON file with decision request data"),
    rail: str = typer.Option(None, "--rail", help="Override rail type (Card or ACH)"),
    channel: str = typer.Option(None, "--channel", help="Override channel (online or pos)"),
    use_ml: bool = typer.Option(True, "--use-ml/--no-ml", help="Enable/disable ML scoring"),
    explain: str = typer.Option(
        None, "--explain", help="Generate explanation (merchant|developer)"
    ),
) -> None:
    """
    Evaluate a decision request from a JSON file and return the response.

    Example:
        orca-core decide-file fixtures/requests/high_ticket_review.json
    """
    try:
        # Read and parse JSON file
        with open(file_path) as f:
            data: dict[str, Any] = json.load(f)

        # Apply rail and channel overrides if provided
        if rail:
            data["rail"] = rail
        if channel:
            data["channel"] = channel

        # Create request model
        request = DecisionRequest(**data)

        # Evaluate rules
        response = evaluate_rules(request, use_ml=use_ml)

        # Output compact JSON
        output = orjson.dumps(response.model_dump(), option=orjson.OPT_SORT_KEYS)
        console.print(output.decode())

        # Generate explanation if requested
        if explain:
            if explain not in ["merchant", "developer"]:
                console.print(
                    f"[red]Invalid explain style: {explain}. Use 'merchant' or 'developer'[/red]"
                )
                raise typer.Exit(1)

            try:
                explanation = llm_explain_decision(response, explain)  # type: ignore
                console.print(f"\n[bold]Explanation ({explain}):[/bold]")
                console.print(explanation)
            except Exception as e:
                console.print(f"[red]Error generating explanation: {e}[/red]")
                raise typer.Exit(1) from e

    except FileNotFoundError:
        console.print(f"[red]File not found: {file_path}[/red]")
        raise typer.Exit(1) from None
    except json.JSONDecodeError as e:
        console.print(f"[red]Invalid JSON in file: {e}[/red]")
        raise typer.Exit(1) from e
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1) from e


@app.command()
def decide_batch(
    glob_pattern: str = typer.Option(
        "fixtures/requests/*.json", "--glob", help="Glob pattern to match JSON files"
    ),
    use_ml: bool = typer.Option(True, "--use-ml/--no-ml", help="Enable/disable ML scoring"),
) -> None:
    """
    Evaluate decision requests from multiple JSON files and output results.

    Example:
        orca-core decide-batch --glob "fixtures/requests/*.json"
    """
    try:
        # Find files matching glob pattern
        file_paths = glob.glob(glob_pattern)

        if not file_paths:
            console.print(f"[yellow]No files found matching pattern: {glob_pattern}[/yellow]")
            return

        console.print(f"[blue]Processing {len(file_paths)} files...[/blue]")

        # Create artifacts directory if it doesn't exist
        artifacts_dir = Path(".artifacts")
        artifacts_dir.mkdir(exist_ok=True)

        # Prepare CSV output
        csv_path = artifacts_dir / "batch_summary.csv"
        csv_data = []

        # Process each file
        for file_path in sorted(file_paths):
            try:
                # Read and parse JSON file
                with open(file_path) as f:
                    data: dict[str, Any] = json.load(f)

                # Create request model
                request = DecisionRequest(**data)

                # Evaluate rules
                response = evaluate_rules(request)

                # Output line-delimited JSON
                output = orjson.dumps(response.model_dump(), option=orjson.OPT_SORT_KEYS)
                console.print(output.decode())

                # Prepare CSV row
                csv_row = {
                    "file": file_path,
                    "decision": response.decision,
                    "reasons_joined": " | ".join(response.reasons),
                    "actions_joined": " | ".join(response.actions),
                    "risk_score": response.meta.get("risk_score", "N/A"),
                }
                csv_data.append(csv_row)

            except Exception as e:
                console.print(f"[red]Error processing {file_path}: {e}[/red]")
                # Add error row to CSV
                csv_row = {
                    "file": file_path,
                    "decision": "ERROR",
                    "reasons_joined": f"Error: {str(e)}",
                    "actions_joined": "",
                    "risk_score": "N/A",
                }
                csv_data.append(csv_row)

        # Write CSV summary
        with open(csv_path, "w", newline="", encoding="utf-8") as csvfile:
            fieldnames = ["file", "decision", "reasons_joined", "actions_joined", "risk_score"]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            writer.writeheader()
            writer.writerows(csv_data)

        console.print(f"[green]CSV summary written to: {csv_path}[/green]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1) from e


@app.command()
def explain(
    request_json: str = typer.Argument(..., help="JSON string with decision request data"),
) -> None:
    """
    Explain a decision request in plain English.

    Parse a JSON request, evaluate it, and provide a natural-language explanation
    of why the decision was made.

    Example:
        orca-core explain '{"cart_total": 750, "features": {"velocity_24h": 4}}'
    """
    try:
        # Parse the JSON string
        data: dict[str, Any] = json.loads(request_json)

        # Create DecisionRequest
        request = DecisionRequest(**data)

        # Evaluate the decision
        response = evaluate_rules(request)

        # Generate explanation
        explanation = explain_decision(response)

        # Print the explanation
        console.print(explanation)

    except json.JSONDecodeError as e:
        console.print(f"[red]Invalid JSON: {e}[/red]")
        raise typer.Exit(1) from e
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1) from e


if __name__ == "__main__":
    app()
