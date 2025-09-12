"""Streamlit app for Orca Core explanation demo."""

import json
import sys
from pathlib import Path

# Add the src directory to the path so we can import orca_core
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

import orjson
import streamlit as st

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

        if uploaded_file is not None:
            try:
                # Read and parse the uploaded file
                content = uploaded_file.read().decode("utf-8")
                data = json.loads(content)

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
            status = response.decision
            if status == "APPROVE":
                st.success(f"✅ **{status}**")
            elif status == "REVIEW":
                st.warning(f"⚠️ **{status}**")
            else:
                st.error(f"❌ **{status}**")

            # Display rail and channel
            col_rail, col_channel = st.columns(2)
            with col_rail:
                st.metric("Payment Rail", response.rail or "N/A")
            with col_channel:
                st.metric("Channel", request.channel)

            # Display human explanation prominently
            st.subheader("💬 Human Explanation")
            if response.explanation_human:
                st.info(response.explanation_human)
            else:
                st.warning("No human explanation available")

            # Copy explanation button
            if response.explanation_human:
                st.button("📋 Copy Explanation", help="Copy the human explanation to clipboard")

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

            # Download decision button
            decision_json = orjson.dumps(response.model_dump(), option=orjson.OPT_INDENT_2)
            st.download_button(
                label="💾 Download Decision JSON",
                data=decision_json,
                file_name=f"decision_{response.transaction_id or 'unknown'}.json",
                mime="application/json",
            )

    # Footer
    st.markdown("---")
    st.markdown(
        "Built with ❤️ using [Streamlit](https://streamlit.io) | "
        "[Orca Core](https://github.com/your-org/orca-core) | "
        "Week 3 — Human-Readable Explanations"
    )


if __name__ == "__main__":
    main()
