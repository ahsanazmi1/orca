"""Unit tests for explanation templates and generation."""

from src.orca_core.explanations import (
    EXPLANATION_TEMPLATES,
    FALLBACK_TEMPLATE,
    generate_human_explanation,
    get_explanation_template,
    get_template_coverage,
)


class TestExplanationTemplates:
    """Test explanation template functionality."""

    def test_high_ticket_template(self):
        """Test high_ticket template for different statuses."""
        # Test exact match
        template = get_explanation_template("high_ticket", "DECLINE")
        expected = "Declined: Amount exceeds card threshold of ${threshold}. Please try a smaller amount or contact support."
        assert template == expected

        template = get_explanation_template("high_ticket", "APPROVE")
        expected = "Approved: Card transaction amount within normal limits."
        assert template == expected

    def test_velocity_flag_template(self):
        """Test velocity_flag template."""
        template = get_explanation_template("velocity_flag", "DECLINE")
        expected = "Declined: Too many recent attempts (last 24h: {velocity} transactions). Please wait 2 hours before trying again."
        assert template == expected

        template = get_explanation_template("velocity_flag", "REVIEW")
        expected = "Under review: Unusual transaction frequency detected. Please wait 1 hour before trying again."
        assert template == expected

    def test_ach_limit_exceeded_template(self):
        """Test ACH limit template."""
        template = get_explanation_template("ach_limit_exceeded", "DECLINE")
        expected = "Declined: Amount exceeds ACH limit of ${limit}. Please try an amount under ${limit} or use a credit card instead."
        assert template == expected

    def test_location_mismatch_template(self):
        """Test location mismatch template."""
        template = get_explanation_template("location_mismatch", "DECLINE")
        expected = "Declined: Unusual location compared to profile."
        assert template == expected

        template = get_explanation_template("location_mismatch", "REVIEW")
        expected = "Under review: Location differs from billing address."
        assert template == expected

    def test_fallback_template(self):
        """Test fallback template for unknown reasons."""
        template = get_explanation_template("unknown_reason", "APPROVE")
        assert template == FALLBACK_TEMPLATE

    def test_template_coverage(self):
        """Test that all templates have coverage."""
        coverage = get_template_coverage()

        # Check that we have templates for all three statuses
        assert "APPROVE" in coverage
        assert "DECLINE" in coverage
        assert "REVIEW" in coverage

        # Check that we have reasonable coverage
        assert len(coverage["APPROVE"]) > 0
        assert len(coverage["DECLINE"]) > 0
        assert len(coverage["REVIEW"]) > 0

    def test_pattern_matching(self):
        """Test pattern matching for complex reasons."""
        # Test cart total pattern
        template = get_explanation_template(
            "Cart total $150.00 within approved threshold", "APPROVE"
        )
        assert "Approved" in template

        # Test loyalty pattern
        template = get_explanation_template(
            "LOYALTY_BOOST: Customer has GOLD loyalty tier", "APPROVE"
        )
        assert "loyalty" in template.lower()


class TestHumanExplanationGeneration:
    """Test human explanation generation."""

    def test_single_reason_approve(self):
        """Test explanation generation for single reason with approve."""
        reasons = ["Cart total $150.00 within approved threshold"]
        explanation = generate_human_explanation(reasons, "APPROVE")

        assert "Approved" in explanation
        assert "transaction amount" in explanation.lower()

    def test_single_reason_decline(self):
        """Test explanation generation for single reason with decline."""
        reasons = ["velocity_flag"]
        explanation = generate_human_explanation(reasons, "DECLINE")

        assert "Declined" in explanation
        assert "transactions" in explanation.lower()

    def test_single_reason_review(self):
        """Test explanation generation for single reason with review."""
        reasons = ["high_ticket"]
        explanation = generate_human_explanation(reasons, "REVIEW")

        assert "Under review" in explanation
        assert "high-value" in explanation.lower()

    def test_multiple_reasons(self):
        """Test explanation generation for multiple reasons."""
        reasons = ["velocity_flag", "location_mismatch"]
        explanation = generate_human_explanation(reasons, "REVIEW")

        assert "Under review" in explanation
        # Should contain information about both reasons
        assert len(explanation) > 50  # Should be a substantial explanation

    def test_empty_reasons(self):
        """Test explanation generation for empty reasons."""
        explanation = generate_human_explanation([], "APPROVE")
        expected = "Transaction approved with no specific issues detected."
        assert explanation == expected

    def test_context_variables(self):
        """Test explanation generation with context variables."""
        reasons = ["high_ticket"]
        context = {"threshold": "$10,000", "velocity_24h": 3.5}
        explanation = generate_human_explanation(reasons, "DECLINE", context)

        # Should use context variables if template supports them
        assert "Declined" in explanation

    def test_combined_reasons_case(self):
        """Test combined reasons case as specified in requirements."""
        reasons = [
            "HIGH_TICKET: Cart total $2200.00 exceeds $500.00 threshold",
            "VELOCITY_FLAG: 24h velocity 4.0 exceeds 3.0 threshold",
            "CHARGEBACK_HISTORY: Customer has 1 chargeback(s) in last 12 months",
        ]
        explanation = generate_human_explanation(reasons, "REVIEW")

        assert "Under review" in explanation
        # Should handle multiple reasons without duplication
        assert explanation.count("Under review") <= 2  # Should not be too repetitive

    def test_duplicate_reasons_dedup(self):
        """Test that duplicate explanations are deduplicated."""
        reasons = ["velocity_flag", "VELOCITY_FLAG: 24h velocity 5.0 exceeds 3.0 threshold"]
        explanation = generate_human_explanation(reasons, "REVIEW")

        # Should not have duplicate "Under review" statements
        assert explanation.count("Under review") == 1

    def test_fallback_triggered(self):
        """Test that fallback is triggered for unknown reasons."""
        reasons = ["unknown_reason_123"]
        explanation = generate_human_explanation(reasons, "APPROVE")

        assert "We made this decision based on" in explanation
        assert "More detail coming soon" in explanation

    def test_template_formatting_error(self):
        """Test that template formatting errors are handled gracefully."""
        # Test with a template that actually has a formatting error
        from src.orca_core.explanations import EXPLANATION_TEMPLATES

        reasons = ["high_ticket"]
        context = {"threshold": "test"}

        # Temporarily modify a template to have a formatting error
        original_template = EXPLANATION_TEMPLATES["high_ticket"]["DECLINE"]
        EXPLANATION_TEMPLATES["high_ticket"][
            "DECLINE"
        ] = "Declined: Amount exceeds {invalid_var} threshold."

        try:
            explanation = generate_human_explanation(reasons, "DECLINE", context)
            # Should fall back to FALLBACK_TEMPLATE when formatting fails
            assert "We made this decision based on" in explanation
            assert "More detail coming soon" in explanation
        finally:
            # Restore original template
            EXPLANATION_TEMPLATES["high_ticket"]["DECLINE"] = original_template

    def test_loyalty_reason_patterns(self):
        """Test that loyalty-related reasons are handled correctly."""
        # Test gold pattern
        explanation = generate_human_explanation(["gold_member"], "APPROVE")
        assert "Approved: Customer loyalty tier benefits applied." in explanation

        # Test silver pattern
        explanation = generate_human_explanation(["silver_status"], "DECLINE")
        assert "Declined: Loyalty benefits could not be applied." in explanation

        # Test loyalty pattern
        explanation = generate_human_explanation(["loyalty_program"], "REVIEW")
        assert "Under review: Loyalty tier verification required." in explanation


class TestTemplateVersions:
    """Test template versioning and consistency."""

    def test_all_templates_have_all_statuses(self):
        """Test that all templates have entries for all statuses."""
        for _reason, templates in EXPLANATION_TEMPLATES.items():
            assert "APPROVE" in templates
            assert "DECLINE" in templates
            assert "REVIEW" in templates

    def test_template_consistency(self):
        """Test that templates are consistent in style."""
        for reason, templates in EXPLANATION_TEMPLATES.items():
            for status, template in templates.items():
                # All templates should start with status word (handling "Approved" vs "Approve")
                status_word = status.title()
                if status == "APPROVE":
                    status_word = "Approved"
                elif status == "DECLINE":
                    status_word = "Declined"
                elif status == "REVIEW":
                    status_word = "Under review"

                assert template.startswith(
                    status_word
                ), f"Template for {reason} {status} doesn't start with {status_word}"

                # Templates should not be empty
                assert len(template.strip()) > 10, f"Template for {reason} {status} is too short"

    def test_no_duplicate_templates(self):
        """Test that there are no duplicate templates."""
        all_templates = []
        for templates in EXPLANATION_TEMPLATES.values():
            all_templates.extend(templates.values())

        # Should have unique templates (allowing some reasonable duplication)
        unique_templates = set(all_templates)
        assert len(unique_templates) > len(all_templates) * 0.7  # At least 70% unique
