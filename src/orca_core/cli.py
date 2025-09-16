"""Command-line interface for Orca Core."""

import csv
import glob
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import orjson
import typer
from rich.console import Console
from rich.table import Table

from .config import decision_mode, get_settings, is_ai_enabled, validate_configuration
from .core.explainer import explain_decision
from .core.ml_hooks import get_model, train_model
from .engine import evaluate_rules
from .llm.explain import get_llm_configuration_status
from .ml.model import get_model_info
from .ml.plotting import plot_xgb_model_evaluation
from .ml.train_xgb import XGBoostTrainer
from .models import DecisionRequest

app = typer.Typer(help="Orca Core Decision Engine CLI")
console = Console()


@app.command()
def config() -> None:
    """Show current configuration status and settings."""
    settings = get_settings()
    current_mode = decision_mode()

    console.print("\n[bold blue]Orca Core Configuration[/bold blue]")
    console.print("=" * 50)

    # Decision mode
    mode_color = "green" if current_mode.value == "RULES_ONLY" else "yellow"
    console.print(f"Decision Mode: [{mode_color}]{current_mode.value}[/{mode_color}]")
    console.print(f"AI Enabled: {'✅ Yes' if is_ai_enabled() else '❌ No'}")

    # Azure OpenAI configuration
    console.print("\n[bold]Azure OpenAI:[/bold]")
    if settings.has_azure_openai_config:
        console.print("  ✅ Configured")
        console.print(f"  Endpoint: {settings.azure_openai_endpoint}")
        console.print(f"  Deployment: {settings.azure_openai_deployment}")
    else:
        console.print("  ❌ Not configured")

    # Azure ML configuration
    console.print("\n[bold]Azure ML:[/bold]")
    if settings.has_azure_ml_config:
        console.print("  ✅ Configured")
        console.print(f"  Endpoint: {settings.azure_ml_endpoint}")
        console.print(f"  Model: {settings.azure_ml_model_name}")
    else:
        console.print("  ❌ Not configured")

    # XGBoost configuration
    console.print("\n[bold]XGBoost Model:[/bold]")
    if settings.use_xgb:
        console.print("  ✅ Enabled")
        if settings.has_xgb_config:
            console.print("  ✅ Model artifacts available")
            console.print(f"  Model Directory: {settings.xgb_model_dir}")
        else:
            console.print("  ⚠️ Model artifacts not found")
            console.print("  Run 'make train-xgb' to train the model")
    else:
        console.print("  ❌ Disabled (using stub)")
        console.print("  Set ORCA_USE_XGB=true to enable")

    # LLM Explanation configuration
    console.print("\n[bold]LLM Explanations:[/bold]")
    llm_status = get_llm_configuration_status()
    if llm_status["status"] == "configured":
        console.print("  ✅ Configured")
        console.print(f"  Endpoint: {llm_status['endpoint']}")
        console.print(f"  Deployment: {llm_status['deployment']}")
    else:
        console.print("  ❌ Not configured")
        console.print(f"  {llm_status['message']}")

    # Explanation settings
    console.print("\n[bold]Explanation Settings:[/bold]")
    console.print(f"  Max Tokens: {settings.explain_max_tokens}")
    console.print(f"  Strict JSON: {settings.explain_strict_json}")
    console.print(f"  Refuse on Uncertainty: {settings.explain_refuse_on_uncertainty}")

    # Debug UI
    console.print("\n[bold]Debug UI:[/bold]")
    console.print(f"  Enabled: {'✅ Yes' if settings.debug_ui_enabled else '❌ No'}")
    if settings.debug_ui_enabled:
        console.print(f"  Port: {settings.debug_ui_port}")

    # Validation
    issues = validate_configuration()
    if issues:
        console.print("\n[bold red]Configuration Issues:[/bold red]")
        for issue in issues:
            console.print(f"  ⚠️ {issue}")
    else:
        console.print("\n[bold green]✅ Configuration is valid[/bold green]")

    console.print()


@app.command()
def train_xgb(
    samples: int = typer.Option(
        10000, "--samples", "-s", help="Number of training samples to generate"
    ),
    model_dir: str = typer.Option(
        "models", "--model-dir", "-d", help="Directory to save model artifacts"
    ),
) -> None:
    """Train XGBoost model for risk prediction."""
    console.print(f"🤖 Training XGBoost model with {samples} samples...")

    try:
        trainer = XGBoostTrainer(model_dir=model_dir)
        metrics = trainer.train_and_save(n_samples=samples)

        console.print("✅ XGBoost training completed successfully!")
        console.print(f"📊 AUC Score: {metrics['auc_score']:.4f}")
        console.print(f"📊 Log Loss: {metrics['log_loss']:.4f}")

        # Show top features
        feature_importance = metrics["feature_importance"]
        top_features = sorted(feature_importance.items(), key=lambda x: x[1], reverse=True)[:5]

        console.print("\n🔝 Top 5 Most Important Features:")
        for feature, importance in top_features:
            console.print(f"   {feature}: {importance:.4f}")

    except Exception as e:
        console.print(f"❌ Training failed: {e}")
        raise typer.Exit(1) from e


@app.command()
def model_info() -> None:
    """Show information about the current ML model."""
    try:
        info = get_model_info()

        console.print("\n[bold blue]ML Model Information[/bold blue]")
        console.print("=" * 50)

        console.print(f"Model Type: {info.get('model_type', 'unknown')}")
        console.print(f"Version: {info.get('version', 'unknown')}")
        console.print(f"Status: {info.get('status', 'unknown')}")

        if info.get("model_type") == "xgboost":
            console.print(f"Features: {info.get('features', 'unknown')}")
            console.print(f"Training Date: {info.get('training_date', 'unknown')}")
            console.print(f"AUC Score: {info.get('auc_score', 'unknown')}")
        else:
            console.print(f"Description: {info.get('description', 'unknown')}")
            console.print(f"Features: {', '.join(info.get('features', []))}")

        console.print()

    except Exception as e:
        console.print(f"❌ Failed to get model info: {e}")
        raise typer.Exit(1) from e


@app.command()
def debug_ui(
    port: int = typer.Option(8501, "--port", "-p", help="Port to run the debug UI on"),
    host: str = typer.Option("localhost", "--host", "-h", help="Host to run the debug UI on"),
) -> None:
    """Launch the Streamlit debug UI for Orca Core."""
    console.print(f"🚀 Launching Orca Core Debug UI on {host}:{port}")
    console.print("📱 Open your browser to the URL shown below")
    console.print("🛑 Press Ctrl+C to stop the server")

    try:
        import subprocess  # nosec B404
        import sys

        # Run streamlit with the debug UI
        cmd = [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            "src/orca_core/ui/debug_ui.py",
            "--server.port",
            str(port),
            "--server.address",
            host,
            "--server.headless",
            "true",
        ]

        subprocess.run(cmd)  # nosec B603

    except KeyboardInterrupt:
        console.print("\n🛑 Debug UI stopped")
    except Exception as e:
        console.print(f"❌ Failed to launch debug UI: {e}")
        raise typer.Exit(1) from e


@app.command()
def decide(
    json_input: str = typer.Argument(
        None, help="JSON string with decision request data (or '-' for stdin)"
    ),
    mode: str = typer.Option(
        None, "--mode", help="Decision mode: rules (RULES_ONLY) or ai (RULES_PLUS_AI)"
    ),
    ml: str = typer.Option(None, "--ml", help="ML engine: stub or xgb (XGBoost)"),
    explain: str = typer.Option(None, "--explain", help="Generate explanations: yes or no"),
    rail: str = typer.Option(None, "--rail", help="Override rail type (Card or ACH)"),
    channel: str = typer.Option(None, "--channel", help="Override channel (online or pos)"),
    output_format: str = typer.Option("json", "--format", "-f", help="Output format: json, table"),
) -> None:
    """
    Evaluate a decision request and return the response.

    Examples:
        orca-core decide '{"cart_total": 750.0, "currency": "USD"}'
        orca-core decide -  # Read from stdin
        echo '{"cart_total": 750.0}' | orca-core decide -
    """
    try:
        # Apply CLI flags to environment
        if mode:
            if mode.lower() == "rules":
                os.environ["ORCA_MODE"] = "RULES_ONLY"
            elif mode.lower() == "ai":
                os.environ["ORCA_MODE"] = "RULES_PLUS_AI"
            else:
                console.print(f"[red]Invalid mode: {mode}. Use 'rules' or 'ai'[/red]")
                raise typer.Exit(1)

        if ml:
            if ml.lower() == "stub":
                os.environ["ORCA_USE_XGB"] = "false"
            elif ml.lower() == "xgb":
                os.environ["ORCA_USE_XGB"] = "true"
            else:
                console.print(f"[red]Invalid ML engine: {ml}. Use 'stub' or 'xgb'[/red]")
                raise typer.Exit(1)

        if explain:
            if explain.lower() in ["yes", "true", "1"]:
                os.environ["ORCA_EXPLAIN_ENABLED"] = "true"
            elif explain.lower() in ["no", "false", "0"]:
                os.environ["ORCA_EXPLAIN_ENABLED"] = "false"
            else:
                console.print(f"[red]Invalid explain value: {explain}. Use 'yes' or 'no'[/red]")
                raise typer.Exit(1)

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

        # Format output based on requested format
        if output_format.lower() == "table":
            _display_decision_table(response)
        else:
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
    mode: str = typer.Option(
        None, "--mode", help="Decision mode: rules (RULES_ONLY) or ai (RULES_PLUS_AI)"
    ),
    ml: str = typer.Option(None, "--ml", help="ML engine: stub or xgb (XGBoost)"),
    explain: str = typer.Option(None, "--explain", help="Generate explanations: yes or no"),
    rail: str = typer.Option(None, "--rail", help="Override rail type (Card or ACH)"),
    channel: str = typer.Option(None, "--channel", help="Override channel (online or pos)"),
    output_format: str = typer.Option("json", "--format", "-f", help="Output format: json, table"),
) -> None:
    """
    Evaluate a decision request from a JSON file and return the response.

    Example:
        orca-core decide-file fixtures/requests/high_ticket_review.json
    """
    try:
        # Apply CLI flags to environment
        if mode:
            if mode.lower() == "rules":
                os.environ["ORCA_MODE"] = "RULES_ONLY"
            elif mode.lower() == "ai":
                os.environ["ORCA_MODE"] = "RULES_PLUS_AI"
            else:
                console.print(f"[red]Invalid mode: {mode}. Use 'rules' or 'ai'[/red]")
                raise typer.Exit(1)

        if ml:
            if ml.lower() == "stub":
                os.environ["ORCA_USE_XGB"] = "false"
            elif ml.lower() == "xgb":
                os.environ["ORCA_USE_XGB"] = "true"
            else:
                console.print(f"[red]Invalid ML engine: {ml}. Use 'stub' or 'xgb'[/red]")
                raise typer.Exit(1)

        if explain:
            if explain.lower() in ["yes", "true", "1"]:
                os.environ["ORCA_EXPLAIN_ENABLED"] = "true"
            elif explain.lower() in ["no", "false", "0"]:
                os.environ["ORCA_EXPLAIN_ENABLED"] = "false"
            else:
                console.print(f"[red]Invalid explain value: {explain}. Use 'yes' or 'no'[/red]")
                raise typer.Exit(1)

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

        # Format output based on requested format
        if output_format.lower() == "table":
            _display_decision_table(response)
        else:
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
    mode: str = typer.Option(
        None, "--mode", help="Decision mode: rules (RULES_ONLY) or ai (RULES_PLUS_AI)"
    ),
    ml: str = typer.Option(None, "--ml", help="ML engine: stub or xgb (XGBoost)"),
    explain: str = typer.Option(None, "--explain", help="Generate explanations: yes or no"),
    output_format: str = typer.Option("csv", "--format", "-f", help="Output format: csv, json"),
    output_file: str = typer.Option(
        None, "--output", "-o", help="Output file path (default: auto-generated)"
    ),
) -> None:
    """
    Evaluate decision requests from multiple JSON files and output results.

    Example:
        orca-core decide-batch --glob "fixtures/requests/*.json"
    """
    try:
        # Apply CLI flags to environment
        if mode:
            if mode.lower() == "rules":
                os.environ["ORCA_MODE"] = "RULES_ONLY"
            elif mode.lower() == "ai":
                os.environ["ORCA_MODE"] = "RULES_PLUS_AI"
            else:
                console.print(f"[red]Invalid mode: {mode}. Use 'rules' or 'ai'[/red]")
                raise typer.Exit(1)

        if ml:
            if ml.lower() == "stub":
                os.environ["ORCA_USE_XGB"] = "false"
            elif ml.lower() == "xgb":
                os.environ["ORCA_USE_XGB"] = "true"
            else:
                console.print(f"[red]Invalid ML engine: {ml}. Use 'stub' or 'xgb'[/red]")
                raise typer.Exit(1)

        if explain:
            if explain.lower() in ["yes", "true", "1"]:
                os.environ["ORCA_EXPLAIN_ENABLED"] = "true"
            elif explain.lower() in ["no", "false", "0"]:
                os.environ["ORCA_EXPLAIN_ENABLED"] = "false"
            else:
                console.print(f"[red]Invalid explain value: {explain}. Use 'yes' or 'no'[/red]")
                raise typer.Exit(1)

        # Find files matching glob pattern
        file_paths = glob.glob(glob_pattern)

        if not file_paths:
            console.print(f"[yellow]No files found matching pattern: {glob_pattern}[/yellow]")
            return

        console.print(f"[blue]Processing {len(file_paths)} files...[/blue]")

        # Create artifacts directory if it doesn't exist
        artifacts_dir = Path(".artifacts")
        artifacts_dir.mkdir(exist_ok=True)

        # Determine output file path
        if output_file:
            output_path = Path(output_file)
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            if output_format.lower() == "csv":
                output_path = artifacts_dir / f"batch_results_{timestamp}.csv"
            else:
                output_path = artifacts_dir / f"batch_results_{timestamp}.json"

        # Prepare data collection
        csv_data = []
        json_data = []

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

                # Collect data for output
                result_data = {
                    "file": file_path,
                    "timestamp": datetime.now().isoformat(),
                    "input": data,
                    "output": response.model_dump(),
                }
                json_data.append(result_data)

                # Prepare CSV row
                ai_data = response.meta.get("ai", {})
                csv_row = {
                    "file": file_path,
                    "timestamp": datetime.now().isoformat(),
                    "decision": response.decision,
                    "status": response.status,
                    "reasons": " | ".join(response.reasons),
                    "actions": " | ".join(response.actions),
                    "risk_score": ai_data.get("risk_score", response.meta.get("risk_score", "N/A")),
                    "model_type": ai_data.get("model_type", "unknown"),
                    "model_version": ai_data.get("version", "unknown"),
                    "reason_codes": " | ".join(ai_data.get("reason_codes", [])),
                    "llm_explanation": (
                        ai_data.get("llm_explanation", {}).get("explanation", "N/A")[:100]
                        if ai_data.get("llm_explanation")
                        else "N/A"
                    ),
                    "llm_confidence": (
                        ai_data.get("llm_explanation", {}).get("confidence", "N/A")
                        if ai_data.get("llm_explanation")
                        else "N/A"
                    ),
                    "cart_total": data.get("cart_total", "N/A"),
                    "currency": data.get("currency", "N/A"),
                    "rail": data.get("rail", "N/A"),
                    "channel": data.get("channel", "N/A"),
                }
                csv_data.append(csv_row)

                # Show progress
                console.print(f"[green]✅ Processed {file_path}[/green]")

            except Exception as e:
                console.print(f"[red]❌ Error processing {file_path}: {e}[/red]")
                # Add error row to CSV
                error_data = {
                    "file": file_path,
                    "timestamp": datetime.now().isoformat(),
                    "input": data if "data" in locals() else {},
                    "output": {"error": str(e)},
                }
                json_data.append(error_data)

                csv_row = {
                    "file": file_path,
                    "timestamp": datetime.now().isoformat(),
                    "decision": "ERROR",
                    "status": "ERROR",
                    "reasons": f"Error: {str(e)}",
                    "actions": "",
                    "risk_score": "N/A",
                    "model_type": "error",
                    "model_version": "N/A",
                    "reason_codes": "",
                    "llm_explanation": "N/A",
                    "llm_confidence": "N/A",
                    "cart_total": "N/A",
                    "currency": "N/A",
                    "rail": "N/A",
                    "channel": "N/A",
                }
                csv_data.append(csv_row)

        # Write output based on format
        if output_format.lower() == "csv":
            # Write CSV output
            with open(output_path, "w", newline="", encoding="utf-8") as csvfile:
                if csv_data:
                    fieldnames = list(csv_data[0].keys())
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(csv_data)

            console.print(f"[green]✅ CSV output written to: {output_path}[/green]")
            console.print(f"[blue]📊 Processed {len(csv_data)} files[/blue]")

        else:
            # Write JSON output with results and summary structure
            output_data = {
                "results": json_data,
                "summary": {
                    "total_files": len(json_data),
                    "successful_files": len(
                        [r for r in json_data if "error" not in r.get("output", {})]
                    ),
                    "failed_files": len([r for r in json_data if "error" in r.get("output", {})]),
                    "timestamp": datetime.now().isoformat(),
                },
            }
            with open(output_path, "w", encoding="utf-8") as jsonfile:
                json.dump(output_data, jsonfile, indent=2, default=str)

            console.print(f"[green]✅ JSON output written to: {output_path}[/green]")
            console.print(f"[blue]📊 Processed {len(json_data)} files[/blue]")

        # Show summary statistics
        if csv_data:
            decisions = [row["decision"] for row in csv_data if row["decision"] != "ERROR"]
            if decisions:
                approve_count = decisions.count("APPROVE")
                decline_count = decisions.count("DECLINE")
                review_count = decisions.count("REVIEW")

                console.print("\n[bold]Summary Statistics:[/bold]")
                console.print(f"  ✅ Approve: {approve_count}")
                console.print(f"  ❌ Decline: {decline_count}")
                console.print(f"  ⚠️  Review: {review_count}")
                console.print(f"  📊 Total: {len(decisions)}")

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

        console.print(f"[green]✅ Generated {len(X)} samples with {y.sum()} high-risk cases[/green]")

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
def generate_plots(
    model_dir: str = typer.Option(
        "models", "--model-dir", "-d", help="Directory containing model artifacts"
    ),
    output_dir: str = typer.Option(
        "validation/phase2/plots", "--output-dir", "-o", help="Directory to save plots"
    ),
) -> None:
    """Generate comprehensive evaluation plots for XGBoost model."""
    console.print("📊 Generating ML model evaluation plots...")

    try:
        plot_paths = plot_xgb_model_evaluation(model_dir=model_dir, output_dir=output_dir)

        if plot_paths:
            console.print("✅ Model evaluation plots generated successfully!")
            console.print(f"📁 Output directory: {output_dir}")

            for plot_type, path in plot_paths.items():
                console.print(f"   📈 {plot_type}: {path}")
        else:
            console.print("❌ Failed to generate evaluation plots.")
            console.print("💡 Make sure the XGBoost model is trained first with 'make train-xgb'")
            raise typer.Exit(1)

    except Exception as e:
        console.print(f"❌ Error generating plots: {e}")
        raise typer.Exit(1) from e


def _display_decision_table(response: Any) -> None:
    """Display decision response in a formatted table."""

    table = Table(title="Decision Result")
    table.add_column("Field", style="cyan")
    table.add_column("Value", style="white")

    # Basic decision info
    table.add_row("Decision", response.decision)
    table.add_row("Status", response.status)

    # Reasons
    if response.reasons:
        table.add_row("Reasons", "; ".join(response.reasons))

    # Actions
    if response.actions:
        table.add_row("Actions", "; ".join(response.actions))

    # AI information
    if "ai" in response.meta:
        ai_data = response.meta["ai"]
        table.add_row("Risk Score", f"{ai_data.get('risk_score', 0.0):.3f}")
        table.add_row("Model Type", ai_data.get("model_type", "unknown"))
        table.add_row("Model Version", ai_data.get("version", "unknown"))

        if "reason_codes" in ai_data:
            table.add_row("Reason Codes", "; ".join(ai_data["reason_codes"]))

        if "llm_explanation" in ai_data:
            llm_data = ai_data["llm_explanation"]
            table.add_row(
                "LLM Explanation",
                (
                    llm_data.get("explanation", "N/A")[:100] + "..."
                    if len(llm_data.get("explanation", "")) > 100
                    else llm_data.get("explanation", "N/A")
                ),
            )
            table.add_row("LLM Confidence", f"{llm_data.get('confidence', 0.0):.2f}")

    console.print(table)


if __name__ == "__main__":
    app()
