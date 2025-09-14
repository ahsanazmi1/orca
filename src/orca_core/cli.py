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
from .core.ml_hooks import get_model, train_model
from .engine import evaluate_rules
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
        response = evaluate_rules(request)

        # Output compact JSON
        output = orjson.dumps(response.model_dump(), option=orjson.OPT_SORT_KEYS)

        console.print(output.decode())

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
        response = evaluate_rules(request)

        # Output compact JSON
        output = orjson.dumps(response.model_dump(), option=orjson.OPT_SORT_KEYS)

        console.print(output.decode())

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


@app.command()
def train(
    data_file: str = typer.Option(None, "--data", help="Path to CSV file with training data"),
    model_path: str = typer.Option(
        "models/risk_model.pkl", "--model", help="Path to save the trained model"
    ),
    samples: int = typer.Option(
        2000, "--samples", help="Number of synthetic samples to generate (if no data file)"
    ),
) -> None:
    """
    Train the Random Forest risk prediction model.

    If no data file is provided, generates synthetic training data.

    Examples:
        orca-core train --samples 5000
        orca-core train --data training_data.csv --model custom_model.pkl
    """
    try:
        if data_file:
            console.print(f"[blue]Loading training data from {data_file}...[/blue]")
            # TODO: Implement CSV data loading
            console.print("[red]CSV data loading not yet implemented. Using synthetic data.[/red]")
            raise typer.Exit(1)

        console.print(f"[blue]Generating {samples} synthetic training samples...[/blue]")

        # Generate synthetic data
        import numpy as np
        import pandas as pd

        np.random.seed(42)
        n_samples = samples

        # Generate features
        data = {
            "velocity_24h": np.random.exponential(2.0, n_samples),
            "velocity_7d": np.random.exponential(5.0, n_samples),
            "cart_total": np.random.lognormal(4.0, 1.5, n_samples),
            "customer_age_days": np.random.lognormal(6.0, 1.0, n_samples),
            "loyalty_score": np.random.beta(2, 2, n_samples),
            "chargebacks_12m": np.random.poisson(0.5, n_samples),
            "location_mismatch": np.random.choice([0, 1], n_samples, p=[0.9, 0.1]),
            "high_ip_distance": np.random.choice([0, 1], n_samples, p=[0.85, 0.15]),
            "time_since_last_purchase": np.random.exponential(7.0, n_samples),
            "payment_method_risk": np.random.beta(2, 3, n_samples),
        }

        X = pd.DataFrame(data)

        # Generate target labels
        risk_score = (
            (X["velocity_24h"] > 5) * 0.3
            + (X["cart_total"] > 1000) * 0.2
            + (X["chargebacks_12m"] > 0) * 0.4
            + (X["location_mismatch"] == 1) * 0.3
            + (X["high_ip_distance"] == 1) * 0.2
            + (X["payment_method_risk"] > 0.7) * 0.3
            + np.random.normal(0, 0.1, n_samples)
        )

        y = pd.Series((risk_score > 0.5).astype(int))

        console.print(
            f"[green]✅ Generated {len(X)} samples with {y.sum()} high-risk cases[/green]"
        )

        # Train model
        console.print("[blue]🚀 Training Random Forest model...[/blue]")
        train_model(X, y, model_path)

        # Show feature importance
        model = get_model()
        importance = model.get_feature_importance()

        console.print("\n[blue]🔍 Feature Importance:[/blue]")
        for feature, imp in sorted(importance.items(), key=lambda x: x[1], reverse=True):
            console.print(f"  {feature}: {imp:.3f}")

        console.print(f"\n[green]✅ Model training completed! Saved to {model_path}[/green]")

    except Exception as e:
        console.print(f"[red]Error training model: {e}[/red]")
        raise typer.Exit(1) from e


@app.command()
def model_info() -> None:
    """
    Show information about the current ML model.
    """
    try:
        model = get_model()

        console.print("[blue]🤖 Orca Core ML Model Information[/blue]")
        console.print("=" * 40)

        console.print(f"[green]Model Path:[/green] {model.model_path}")
        console.print("[green]Model Type:[/green] Random Forest Classifier")

        # Check if model is trained
        if model.model is not None:
            console.print("[green]Status:[/green] ✅ Trained")

            # Feature importance
            importance = model.get_feature_importance()
            if importance:
                console.print("\n[blue]🔍 Feature Importance:[/blue]")
                for feature, imp in sorted(importance.items(), key=lambda x: x[1], reverse=True):
                    console.print(f"  {feature}: {imp:.3f}")
        else:
            console.print("[yellow]Status:[/yellow] ⚠️ Not trained (using default values)")

        console.print("\n[green]Supported Features:[/green]")
        for feature in model.feature_columns:
            console.print(f"  • {feature}")

    except Exception as e:
        console.print(f"[red]Error getting model info: {e}[/red]")
        raise typer.Exit(1) from e


if __name__ == "__main__":
    app()
