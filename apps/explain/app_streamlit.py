"""Streamlit app for Orca Core explanation demo."""

import json
import sys
from pathlib import Path

import orjson
import streamlit as st

# Add the src directory to the path so we can import orca_core
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from orca_core.engine import evaluate_rules  # noqa: E402
from orca_core.models import DecisionRequest  # noqa: E402


def main() -> None:
    """Main Streamlit app."""
    st.set_page_config(page_title="Orca Core Decision Explainer", page_icon="🐋", layout="wide")

    st.title("🐋 Orca Core Decision Explainer")
    st.markdown(
        "Upload a transaction JSON file to see the decision and human-readable explanation."
    )

    # Sidebar with examples
    with st.sidebar:
        st.header("📁 Example Files")
        st.markdown("Try these example files:")

        example_files = [
            ("Card Approve (Small)", "fixtures/week3/requests/card_approve_small.json"),
            ("Card Decline (Velocity)", "fixtures/week3/requests/card_decline_velocity.json"),
            ("ACH Approve (Small)", "fixtures/week3/requests/ach_approve_small.json"),
            ("ACH Decline (Limit)", "fixtures/week3/requests/ach_decline_limit.json"),
        ]

        for name, path in example_files:
            if Path(path).exists():
                with open(path) as f:
                    content = f.read()
                st.download_button(
                    label=f"📄 {name}",
                    data=content,
                    file_name=Path(path).name,
                    mime="application/json",
                )

    # Main content area
    col1, col2 = st.columns([1, 1])

    with col1:
        st.header("📤 Upload Transaction")

        uploaded_file = st.file_uploader(
            "Choose a JSON file",
            type=["json"],
            help="Upload a transaction JSON file with cart_total, rail, channel, and other fields.",
        )

        # Parameters section
        st.header("⚙️ Parameters")

        # Rail and Channel toggles
        col_rail, col_channel = st.columns(2)
        with col_rail:
            rail_override = st.selectbox(
                "Payment Rail", ["Card", "ACH"], help="Override the rail from uploaded file"
            )
        with col_channel:
            channel_override = st.selectbox(
                "Channel", ["online", "pos"], help="Override the channel from uploaded file"
            )

        if uploaded_file is not None:
            try:
                # Read and parse the uploaded file
                content = uploaded_file.read().decode("utf-8")
                data = json.loads(content)

                # Apply rail/channel overrides
                data["rail"] = rail_override
                data["channel"] = channel_override

                # Validate against DecisionRequest schema
                try:
                    request = DecisionRequest(**data)
                    st.success("✅ Valid transaction data!")

                    # Display the input data
                    with st.expander("📋 Input Data", expanded=False):
                        st.json(data)

                except Exception as e:
                    st.error(f"❌ Invalid transaction data: {str(e)}")
                    st.stop()

            except json.JSONDecodeError as e:
                st.error(f"❌ Invalid JSON: {str(e)}")
                st.stop()

    with col2:
        st.header("🎯 Decision Result")

        if uploaded_file is not None and "request" in locals():
            # Process the request
            with st.spinner("Processing decision..."):
                response = evaluate_rules(request)

            # Display decision status with color coding
            status = response.status
            if status == "APPROVE":
                st.success(f"✅ **{status}**")
            elif status == "ROUTE":
                st.warning(f"⚠️ **{status}** (Legacy: {response.decision})")
            else:
                st.error(f"❌ **{status}**")

            # Display key metrics
            col_rail, col_channel, col_amount = st.columns(3)
            with col_rail:
                rail = response.meta_structured.rail if response.meta_structured else response.rail
                st.metric("Payment Rail", rail)
            with col_channel:
                channel = response.meta_structured.channel if response.meta_structured else "N/A"
                st.metric("Channel", channel)
            with col_amount:
                cart_total = (
                    response.meta_structured.cart_total
                    if response.meta_structured
                    else response.cart_total
                )
                st.metric("Cart Total", f"${cart_total:.2f}")

            # Display human explanation prominently
            st.subheader("💬 Human Explanation")
            if response.explanation_human:
                st.info(response.explanation_human)
            else:
                st.warning("No human explanation available")

            # Copy/Download buttons
            col_copy, col_download = st.columns(2)
            with col_copy:
                if response.explanation_human:
                    if st.button(
                        "📋 Copy Explanation", help="Copy the human explanation to clipboard"
                    ):
                        st.success("Explanation copied to clipboard!")

            with col_download:
                decision_json = orjson.dumps(response.model_dump(), option=orjson.OPT_INDENT_2)
                transaction_id = (
                    response.meta_structured.transaction_id
                    if response.meta_structured
                    else response.transaction_id
                )
                st.download_button(
                    label="💾 Download JSON",
                    data=decision_json,
                    file_name=f"decision_{transaction_id}.json",
                    mime="application/json",
                    help="Download the complete decision response as JSON",
                )

            # Display reasons and actions
            col_reasons, col_actions = st.columns(2)

            with col_reasons:
                st.subheader("🔍 Reasons")
                if response.reasons:
                    for reason in response.reasons:
                        st.text(f"• {reason}")
                else:
                    st.text("No specific reasons")

            with col_actions:
                st.subheader("⚡ Actions")
                if response.actions:
                    for action in response.actions:
                        st.text(f"• {action}")
                else:
                    st.text("No specific actions")

            # Raw JSON output
            with st.expander("📄 Raw Decision JSON", expanded=False):
                st.json(response.model_dump())

            # Metadata section
            with st.expander("📊 Decision Metadata", expanded=False):
                if response.meta_structured:
                    st.json(
                        {
                            "transaction_id": response.meta_structured.transaction_id,
                            "timestamp": response.meta_structured.timestamp.isoformat(),
                            "risk_score": response.meta_structured.risk_score,
                            "rules_evaluated": response.meta_structured.rules_evaluated,
                            "approved_amount": response.meta_structured.approved_amount,
                        }
                    )
                else:
                    st.json(response.meta)

    # Footer
    st.markdown("---")
    st.markdown(
        "Built with ❤️ using [Streamlit](https://streamlit.io) | "
        "[Orca Core](https://github.com/ahsanazmi1/orca) | "
        "Week 4 — Polish & Evidence"
    )


if __name__ == "__main__":
    main()
