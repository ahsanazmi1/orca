"""AP2-compliant CLI for Orca Core decision engine."""

import json
import sys
from datetime import UTC
from pathlib import Path
from typing import Any

import typer
from rich.console import Console

from ..core.decision_contract import (
    sign_and_hash_decision,
    validate_ap2_contract,
)
from ..core.decision_legacy_adapter import DecisionLegacyAdapter
from ..core.rules_engine import evaluate_ap2_rules
from ..core.versioning import get_content_type
from ..explain.nlg import explain_ap2_decision
from ..mandates.ap2_types import (
    ActorType,
    AgentPresence,
    AuthRequirement,
    CartItem,
    CartMandate,
    ChannelType,
    GeoLocation,
    IntentMandate,
    IntentType,
    PaymentMandate,
    PaymentModality,
)

app = typer.Typer(help="Orca Core AP2 Decision Engine CLI")
console = Console(force_terminal=False, no_color=True)


def write_output_with_headers(
    output_data: dict[str, Any],
    output_file: Path | None,
    use_legacy: bool = False,
    verbose: bool = False,
) -> None:
    """Write output data with appropriate content type headers."""
    content_type = get_content_type(not use_legacy)

    if output_file:
        with open(output_file, "w") as f:
            # Write content type header as comment for JSON files
            f.write(f"# Content-Type: {content_type}\n")
            json.dump(output_data, f, indent=2, default=str)
        if verbose:
            console.print(f"[green]✅ Output written to: {output_file}[/green]")
            console.print(f"[blue]📄 Content-Type: {content_type}[/blue]")
    else:
        # For stdout, we can't add headers, but we can show the content type
        if verbose:
            console.print(f"[blue]📄 Content-Type: {content_type}[/blue]")
        print(json.dumps(output_data, indent=2, default=str))


@app.command()
def decide_file(
    input_file: Path = typer.Argument(..., help="Path to AP2 JSON input file"),
    output_file: Path | None = typer.Option(
        None, "--output", "-o", help="Path to output file (default: stdout)"
    ),
    legacy_json: bool = typer.Option(False, "--legacy-json", help="Output in legacy JSON format"),
    explain: bool = typer.Option(False, "--explain", help="Include human-readable explanation"),
    validate_only: bool = typer.Option(
        False, "--validate-only", help="Only validate input, don't process"
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
) -> None:
    """
    Process an AP2 decision request from a JSON file.

    This command reads an AP2-compliant decision request from a JSON file,
    validates it against the AP2 schema, processes it through the decision engine,
    and outputs the result in AP2 format (or legacy format if requested).
    """
    try:
        # Read and validate input file
        if not input_file.exists():
            console.print(f"[red]Error: Input file '{input_file}' does not exist[/red]")
            raise typer.Exit(1)

        if verbose:
            console.print(f"[blue]Reading AP2 input from: {input_file}[/blue]")

        with open(input_file) as f:
            input_data = json.load(f)

        # Validate AP2 contract
        if verbose:
            console.print("[blue]Validating AP2 contract...[/blue]")

        try:
            ap2_contract = validate_ap2_contract(input_data)
            if verbose:
                console.print("[green]✅ AP2 contract validation successful[/green]")
        except Exception as e:
            console.print(f"[red]❌ AP2 contract validation failed: {e}[/red]")
            raise typer.Exit(1) from e

        if validate_only:
            console.print("[green]✅ AP2 contract is valid[/green]")
            return

        # Process decision
        if verbose:
            console.print("[blue]Processing decision through AP2 rules engine...[/blue]")

        decision_outcome = evaluate_ap2_rules(ap2_contract)

        # Update contract with decision outcome
        ap2_contract.decision = decision_outcome

        # Sign and hash if enabled
        if verbose:
            console.print("[blue]Signing and hashing decision...[/blue]")

        signed_contract = sign_and_hash_decision(ap2_contract)

        # Generate explanation if requested
        explanation = None
        if explain:
            if verbose:
                console.print("[blue]Generating explanation...[/blue]")
            explanation = explain_ap2_decision(signed_contract)

        # Output result
        if legacy_json:
            if verbose:
                console.print("[blue]Converting to legacy format...[/blue]")
            legacy_response = DecisionLegacyAdapter.ap2_contract_to_legacy_response(signed_contract)
            output_data = legacy_response.model_dump()
        else:
            output_data = signed_contract.model_dump()

        # Add explanation if requested
        if explanation:
            output_data["explanation"] = explanation

        # Write output with content type headers
        write_output_with_headers(output_data, output_file, legacy_json, verbose)

        if verbose:
            console.print("[green]✅ Decision processing complete[/green]")

    except Exception as e:
        console.print(f"[red]❌ Error processing decision: {e}[/red]")
        if verbose:
            import traceback

            console.print(f"[red]Traceback: {traceback.format_exc()}[/red]")
        raise typer.Exit(1) from e


@app.command()
def decide_stdin(
    legacy_json: bool = typer.Option(False, "--legacy-json", help="Output in legacy JSON format"),
    explain: bool = typer.Option(False, "--explain", help="Include human-readable explanation"),
    validate_only: bool = typer.Option(
        False, "--validate-only", help="Only validate input, don't process"
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
) -> None:
    """
    Process an AP2 decision request from stdin.

    This command reads an AP2-compliant decision request from stdin,
    validates it against the AP2 schema, processes it through the decision engine,
    and outputs the result in AP2 format (or legacy format if requested).
    """
    try:
        # Read from stdin
        if sys.stdin.isatty():
            console.print("[red]Error: No input provided on stdin[/red]")
            raise typer.Exit(1)

        if verbose:
            console.print("[blue]Reading AP2 input from stdin...[/blue]")

        input_data = json.load(sys.stdin)

        # Validate AP2 contract
        if verbose:
            console.print("[blue]Validating AP2 contract...[/blue]")

        try:
            ap2_contract = validate_ap2_contract(input_data)
            if verbose:
                console.print("[green]✅ AP2 contract validation successful[/green]")
        except Exception as e:
            console.print(f"[red]❌ AP2 contract validation failed: {e}[/red]")
            raise typer.Exit(1) from e

        if validate_only:
            console.print("[green]✅ AP2 contract is valid[/green]")
            return

        # Process decision
        if verbose:
            console.print("[blue]Processing decision through AP2 rules engine...[/blue]")

        decision_outcome = evaluate_ap2_rules(ap2_contract)

        # Update contract with decision outcome
        ap2_contract.decision = decision_outcome

        # Sign and hash if enabled
        if verbose:
            console.print("[blue]Signing and hashing decision...[/blue]")

        signed_contract = sign_and_hash_decision(ap2_contract)

        # Generate explanation if requested
        explanation = None
        if explain:
            if verbose:
                console.print("[blue]Generating explanation...[/blue]")
            explanation = explain_ap2_decision(signed_contract)

        # Output result
        if legacy_json:
            if verbose:
                console.print("[blue]Converting to legacy format...[/blue]")
            legacy_response = DecisionLegacyAdapter.ap2_contract_to_legacy_response(signed_contract)
            output_data = legacy_response.model_dump()
        else:
            output_data = signed_contract.model_dump()

        # Add explanation if requested
        if explanation:
            output_data["explanation"] = explanation

        # Write output to stdout
        print(json.dumps(output_data, indent=2, default=str))

        if verbose:
            console.print("[green]✅ Decision processing complete[/green]")

    except Exception as e:
        console.print(f"[red]❌ Error processing decision: {e}[/red]")
        if verbose:
            import traceback

            console.print(f"[red]Traceback: {traceback.format_exc()}[/red]")
        raise typer.Exit(1) from e


@app.command()
def validate(
    input_file: Path = typer.Argument(..., help="Path to AP2 JSON file to validate"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
) -> None:
    """
    Validate an AP2 JSON file against the schema.

    This command validates an AP2-compliant JSON file against the AP2 schema
    and reports any validation errors.
    """
    try:
        if not input_file.exists():
            console.print(f"[red]Error: Input file '{input_file}' does not exist[/red]")
            raise typer.Exit(1)

        if verbose:
            console.print(f"[blue]Validating AP2 file: {input_file}[/blue]")

        with open(input_file) as f:
            input_data = json.load(f)

        # Validate AP2 contract
        try:
            ap2_contract = validate_ap2_contract(input_data)
            console.print("[green]✅ AP2 contract is valid[/green]")

            if verbose:
                # Show contract summary
                console.print("\n[bold]Contract Summary:[/bold]")
                console.print(f"  AP2 Version: {ap2_contract.ap2_version}")
                console.print(f"  Intent Channel: {ap2_contract.intent.channel.value}")
                console.print(f"  Intent Actor: {ap2_contract.intent.actor.value}")
                console.print(
                    f"  Cart Amount: {ap2_contract.cart.amount} {ap2_contract.cart.currency}"
                )
                console.print(f"  Payment Modality: {ap2_contract.payment.modality.value}")
                if ap2_contract.decision:
                    console.print(f"  Decision Result: {ap2_contract.decision.result}")
                    console.print(f"  Risk Score: {ap2_contract.decision.risk_score}")

        except Exception as e:
            console.print(f"[red]❌ AP2 contract validation failed: {e}[/red]")
            raise typer.Exit(1) from e

    except Exception as e:
        console.print(f"[red]❌ Error validating file: {e}[/red]")
        if verbose:
            import traceback

            console.print(f"[red]Traceback: {traceback.format_exc()}[/red]")
        raise typer.Exit(1) from e


@app.command()
def create_sample(
    output_file: Path = typer.Argument(..., help="Path to output sample AP2 JSON file"),
    amount: float = typer.Option(100.0, "--amount", help="Cart amount"),
    currency: str = typer.Option("USD", "--currency", help="Currency code"),
    channel: str = typer.Option("web", "--channel", help="Intent channel (web, pos, mobile)"),
    modality: str = typer.Option(
        "immediate", "--modality", help="Payment modality (immediate, deferred, real_time)"
    ),
    country: str = typer.Option("US", "--country", help="Geographic country code"),
) -> None:
    """
    Create a sample AP2 decision request JSON file.

    This command creates a sample AP2-compliant decision request that can be used
    for testing and development.
    """
    try:
        # Map string inputs to enums
        channel_map = {
            "web": ChannelType.WEB,
            "pos": ChannelType.POS,
            "mobile": ChannelType.MOBILE,
        }

        modality_map = {
            "immediate": PaymentModality.IMMEDIATE,
            "deferred": PaymentModality.DEFERRED,
            "recurring": PaymentModality.RECURRING,
            "installment": PaymentModality.INSTALLMENT,
        }

        if channel not in channel_map:
            console.print(
                f"[red]Error: Invalid channel '{channel}'. Must be one of: {list(channel_map.keys())}[/red]"
            )
            raise typer.Exit(1)

        if modality not in modality_map:
            console.print(
                f"[red]Error: Invalid modality '{modality}'. Must be one of: {list(modality_map.keys())}[/red]"
            )
            raise typer.Exit(1)

        # Create sample AP2 contract
        from datetime import datetime
        from decimal import Decimal

        intent = IntentMandate(
            actor=ActorType.HUMAN,
            intent_type=IntentType.PURCHASE,
            channel=channel_map[channel],
            agent_presence=AgentPresence.ASSISTED,
            timestamps={
                "created": datetime.now(UTC),
                "expires": datetime.now(UTC).replace(hour=23, minute=59, second=59),
            },
            metadata={},  # Default empty metadata
        )

        cart = CartMandate(
            items=[
                CartItem(
                    id="sample_item_1",
                    name="Sample Product",
                    quantity=1,
                    unit_price=Decimal(str(amount)),
                    total_price=Decimal(str(amount)),
                    description="Sample product for testing",
                    category="software",
                    sku="sample_001",
                )
            ],
            amount=Decimal(str(amount)),
            currency=currency,
            mcc="5733",  # Software stores
            geo=GeoLocation(
                country=country,
                region="",  # Default empty region
                city="",  # Default empty city
                latitude=0.0,  # Default latitude
                longitude=0.0,  # Default longitude
                timezone="UTC",  # Default timezone
            ),
            metadata={},  # Default empty metadata
        )

        payment = PaymentMandate(
            instrument_ref="sample_card_123456789",
            modality=modality_map[modality],
            auth_requirements=[AuthRequirement.PIN],
            instrument_token=None,  # No token for sample
            constraints={},  # Default empty constraints
            metadata={},  # Default empty metadata
        )

        # Create AP2 contract
        from ..core.decision_contract import create_ap2_decision_contract

        ap2_contract = create_ap2_decision_contract(
            intent=intent,
            cart=cart,
            payment=payment,
            result="APPROVE",
            risk_score=0.1,
            reasons=[],
            actions=[],
        )

        # Write to file
        with open(output_file, "w") as f:
            json.dump(ap2_contract.model_dump(), f, indent=2, default=str)

        console.print(f"[green]✅ Sample AP2 contract created: {output_file}[/green]")
        console.print(f"  Amount: {amount} {currency}")
        console.print(f"  Channel: {channel}")
        console.print(f"  Modality: {modality}")
        console.print(f"  Country: {country}")

    except Exception as e:
        console.print(f"[red]❌ Error creating sample file: {e}[/red]")
        raise typer.Exit(1) from e


@app.command()
def explain(
    input_file: Path = typer.Argument(..., help="Path to AP2 decision result file"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
) -> None:
    """
    Generate a human-readable explanation for an AP2 decision result.

    This command reads an AP2 decision result and generates a human-readable
    explanation with AP2 field citations.
    """
    try:
        if not input_file.exists():
            console.print(f"[red]Error: Input file '{input_file}' does not exist[/red]")
            raise typer.Exit(1)

        if verbose:
            console.print(f"[blue]Reading AP2 decision result from: {input_file}[/blue]")

        with open(input_file) as f:
            input_data = json.load(f)

        # Validate and load AP2 contract
        try:
            ap2_contract = validate_ap2_contract(input_data)
            if verbose:
                console.print("[green]✅ AP2 contract validation successful[/green]")
        except Exception as e:
            console.print(f"[red]❌ AP2 contract validation failed: {e}[/red]")
            raise typer.Exit(1) from e

        # Generate explanation
        if verbose:
            console.print("[blue]Generating explanation...[/blue]")

        explanation = explain_ap2_decision(ap2_contract)

        # Display explanation
        console.print("\n[bold blue]Decision Explanation[/bold blue]")
        console.print("=" * 50)
        console.print(explanation)

        if verbose:
            console.print("\n[bold]Decision Summary:[/bold]")
            console.print(f"  Result: {ap2_contract.decision.result}")
            console.print(f"  Risk Score: {ap2_contract.decision.risk_score}")
            console.print(f"  Reasons: {len(ap2_contract.decision.reasons)}")
            console.print(f"  Actions: {len(ap2_contract.decision.actions)}")

    except Exception as e:
        console.print(f"[red]❌ Error generating explanation: {e}[/red]")
        if verbose:
            import traceback

            console.print(f"[red]Traceback: {traceback.format_exc()}[/red]")
        raise typer.Exit(1) from e


def main() -> None:
    """Main CLI entry point."""
    app()


if __name__ == "__main__":
    main()
