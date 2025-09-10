"""Command-line interface for Orca Core."""

from typing import Any

import orjson
import typer
from rich.console import Console

from .engine import evaluate_rules
from .models import DecisionRequest

app = typer.Typer(help="Orca Core Decision Engine CLI")
console = Console()


@app.command()
def decide(
    json_input: str = typer.Argument(..., help="JSON string with decision request data"),
) -> None:
    """
    Evaluate a decision request and return the response.

    Example:
        orca-core decide '{"cart_total": 750.0, "currency": "USD"}'
    """
    try:
        # Parse JSON input
        data: dict[str, Any] = orjson.loads(json_input)

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


if __name__ == "__main__":
    app()
