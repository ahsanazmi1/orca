#!/usr/bin/env python3
"""
OCN Orca Phase Status Audit Script

This script audits the Orca repository against OCN Foundations, Phase 1, and Phase 2 deliverables.
It generates both human-readable and machine-readable reports.

Usage:
    python scripts/audit_orca_phase_status.py

Outputs:
    - AUDIT_REPORT.md (human-readable with checkboxes)
    - audit_report.json (machine-readable structured output)
    - Exit code 0 if all Phase 1 blocking items pass, non-zero otherwise
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from _audit_utils import (
    check_codeowners,
    check_editorconfig,
    check_git_tags,
    check_import_module,
    check_log_redaction,
    find_ocn_common,
    check_pre_commit_hooks,
    check_python_version,
    check_streamlit_app,
    find_files_by_name,
    find_files_by_pattern,
    get_coverage_percentage,
    load_json_file,
    run_pytest_coverage,
    search_in_files,
    validate_cloudevents_basic,
    validate_json_schema,
)


class AuditResult:
    """Represents the result of an audit check."""

    def __init__(self, name: str, phase: str, status: str, evidence: List[str], remedy: str = ""):
        self.name = name
        self.phase = phase
        self.status = status  # "pass", "fail", "warning"
        self.evidence = evidence
        self.remedy = remedy

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "phase": self.phase,
            "status": self.status,
            "evidence": self.evidence,
            "remedy": self.remedy
        }


class OrcaAuditor:
    """Main auditor class for OCN Orca phase status."""

    def __init__(self):
        self.results: List[AuditResult] = []
        self.start_time = datetime.now()

    def add_result(self, result: AuditResult) -> None:
        """Add an audit result."""
        self.results.append(result)

    def run_all_checks(self) -> None:
        """Run all audit checks."""
        print("🔍 Running OCN Orca Phase Status Audit...")
        print("=" * 60)

        # A. Repo hygiene & config
        self.check_repo_hygiene()

        # B. Contracts & schemas (Foundations)
        self.check_contracts_schemas()

        # C. Rules engine (Phase 1)
        self.check_rules_engine()

        # D. Decision contract (Phase 1)
        self.check_decision_contract()

        # E. CloudEvents (Phase 1+)
        self.check_cloudevents()

        # F. CLI & Streamlit demo (Phase 1)
        self.check_cli_streamlit()

        # G. ML stub (Phase 2)
        self.check_ml_stub()

        # H. LLM explanations (Phase 2)
        self.check_llm_explanations()

        # I. Observability & redaction (Foundations/Phase 2)
        self.check_observability_redaction()

        # J. Weave integration hooks (Phase 1 evidence)
        self.check_weave_integration()

        # K. Tests & coverage gates
        self.check_tests_coverage()

        # L. GitHub workflows (Foundations)
        self.check_github_workflows()

        # M. Tags/versions (Phase 1 evidence)
        self.check_tags_versions()

    def check_repo_hygiene(self) -> None:
        """A. Repo hygiene & config checks."""
        print("📁 Checking repo hygiene & config...")

        # Required files
        required_files = [
            'LICENSE', 'README.md', 'CHANGELOG.md', 'CONTRIBUTING.md',
            'pyproject.toml', '.pre-commit-config.yaml'
        ]

        missing_files = []
        for file_name in required_files:
            if not Path(file_name).exists():
                missing_files.append(file_name)

        if missing_files:
            self.add_result(AuditResult(
                name="Required files present",
                phase="Foundations",
                status="fail",
                evidence=[f"Missing files: {', '.join(missing_files)}"],
                remedy="Add missing files to repository root"
            ))
        else:
            self.add_result(AuditResult(
                name="Required files present",
                phase="Foundations",
                status="pass",
                evidence=[f"All required files found: {', '.join(required_files)}"]
            ))

        # Python version check
        python_ok, python_version = check_python_version()
        if python_ok:
            self.add_result(AuditResult(
                name="Python version ≥ 3.12",
                phase="Foundations",
                status="pass",
                evidence=[f"Python version: {python_version}"]
            ))
        else:
            self.add_result(AuditResult(
                name="Python version ≥ 3.12",
                phase="Foundations",
                status="fail",
                evidence=[f"Python version: {python_version}"],
                remedy="Update Python to version 3.12 or higher"
            ))

        # pyproject.toml Python version
        pyproject_path = Path('pyproject.toml')
        if pyproject_path.exists():
            pyproject_data = load_json_file(pyproject_path)
            if pyproject_data and 'project' in pyproject_data:
                requires_python = pyproject_data['project'].get('requires-python', '')
                if '>=3.12' in requires_python or '>=3.11' in requires_python:
                    self.add_result(AuditResult(
                        name="pyproject.toml Python version",
                        phase="Foundations",
                        status="pass",
                        evidence=[f"requires-python: {requires_python}"]
                    ))
                else:
                    self.add_result(AuditResult(
                        name="pyproject.toml Python version",
                        phase="Foundations",
                        status="fail",
                        evidence=[f"requires-python: {requires_python}"],
                        remedy="Update pyproject.toml to require Python >=3.12"
                    ))

        # Pre-commit configuration
        precommit_ok, precommit_evidence = check_pre_commit_hooks()
        if precommit_ok:
            self.add_result(AuditResult(
                name="Pre-commit configured",
                phase="Foundations",
                status="pass",
                evidence=precommit_evidence
            ))
        else:
            self.add_result(AuditResult(
                name="Pre-commit configured",
                phase="Foundations",
                status="warning",
                evidence=precommit_evidence,
                remedy="Install and configure pre-commit hooks"
            ))

        # Optional files
        if check_editorconfig():
            self.add_result(AuditResult(
                name="EditorConfig present",
                phase="Foundations",
                status="pass",
                evidence=["Found .editorconfig"]
            ))
        else:
            self.add_result(AuditResult(
                name="EditorConfig present",
                phase="Foundations",
                status="warning",
                evidence=["No .editorconfig found"],
                remedy="Add .editorconfig for consistent formatting"
            ))

        if check_codeowners():
            self.add_result(AuditResult(
                name="CODEOWNERS present",
                phase="Foundations",
                status="pass",
                evidence=["Found .github/CODEOWNERS"]
            ))
        else:
            self.add_result(AuditResult(
                name="CODEOWNERS present",
                phase="Foundations",
                status="warning",
                evidence=["No CODEOWNERS found"],
                remedy="Add CODEOWNERS file for code review assignment"
            ))

    def check_contracts_schemas(self) -> None:
        """B. Contracts & schemas (Foundations) checks."""
        print("📋 Checking contracts & schemas...")

        # Check for ocn-common
        ocn_ok, ocn_evidence = find_ocn_common()
        if ocn_ok:
            self.add_result(AuditResult(
                name="ocn-common available",
                phase="Foundations",
                status="pass",
                evidence=[ocn_evidence]
            ))
        else:
            self.add_result(AuditResult(
                name="ocn-common available",
                phase="Foundations",
                status="warning",
                evidence=[ocn_evidence],
                remedy="Install ocn-common or add as git submodule"
            ))

        # Check for AP2 content type constant
        content_type_found = False
        content_type_files = find_files_by_pattern('src', '**/*.py')
        for file_path in content_type_files:
            matches = search_in_files(r'AP2_CONTENT_TYPE|application/vnd\.ocn\.ap2', [file_path])
            if matches:
                content_type_found = True
                self.add_result(AuditResult(
                    name="AP2 content type constant",
                    phase="Foundations",
                    status="pass",
                    evidence=[f"Found in {file_path}: {matches[0][2]}"],
                ))
                break

        if not content_type_found:
            self.add_result(AuditResult(
                name="AP2 content type constant",
                phase="Foundations",
                status="fail",
                evidence=["AP2 content type not found in codebase"],
                remedy="Add CONTENT_TYPE constant with value 'application/vnd.ocn.ap2+json; version=1'"
            ))

        # Check for AP2 input fixtures
        ap2_samples = find_files_by_pattern('samples', '**/*.json')
        if ap2_samples:
            # Check for approve, decline, review examples
            sample_names = [f.name.lower() for f in ap2_samples]
            has_approve = any('approve' in name for name in sample_names)
            has_decline = any('decline' in name for name in sample_names)
            has_review = any('review' in name for name in sample_names)

            if has_approve and has_decline and has_review:
                self.add_result(AuditResult(
                    name="AP2 input fixtures",
                    phase="Foundations",
                    status="pass",
                    evidence=[f"Found {len(ap2_samples)} AP2 samples with approve/decline/review examples"]
                ))
            else:
                missing = []
                if not has_approve: missing.append("approve")
                if not has_decline: missing.append("decline")
                if not has_review: missing.append("review")

                self.add_result(AuditResult(
                    name="AP2 input fixtures",
                    phase="Foundations",
                    status="fail",
                    evidence=[f"Missing sample types: {', '.join(missing)}"],
                    remedy="Add AP2 sample files for approve, decline, and review decisions"
                ))
        else:
            self.add_result(AuditResult(
                name="AP2 input fixtures",
                phase="Foundations",
                status="fail",
                evidence=["No AP2 sample files found"],
                remedy="Create AP2 sample files in samples/ directory"
            ))

    def check_rules_engine(self) -> None:
        """C. Rules engine (Phase 1) checks."""
        print("⚖️ Checking rules engine...")

        # Look for rules engine files
        rules_files = find_files_by_name('src', '*rules*.py')
        if rules_files:
            self.add_result(AuditResult(
                name="Rules engine present",
                phase="Phase 1",
                status="pass",
                evidence=[f"Found rules files: {[str(f) for f in rules_files]}"]
            ))

            # Check for deterministic approve/decline/review logic
            has_approve = False
            has_decline = False
            has_review = False

            for rules_file in rules_files:
                matches = search_in_files('("APPROVE"|"DECLINE"|"REVIEW")', [rules_file])
                for _, _, line in matches:
                    if '"APPROVE"' in line or "'APPROVE'" in line: has_approve = True
                    if '"DECLINE"' in line or "'DECLINE'" in line: has_decline = True
                    if '"REVIEW"' in line or "'REVIEW'" in line: has_review = True

            if has_approve and has_decline and has_review:
                self.add_result(AuditResult(
                    name="Deterministic decision logic",
                    phase="Phase 1",
                    status="pass",
                    evidence=["Found APPROVE, DECLINE, and REVIEW decision logic"]
                ))
            else:
                missing = []
                if not has_approve: missing.append("APPROVE")
                if not has_decline: missing.append("DECLINE")
                if not has_review: missing.append("REVIEW")

                self.add_result(AuditResult(
                    name="Deterministic decision logic",
                    phase="Phase 1",
                    status="fail",
                    evidence=[f"Missing decision types: {', '.join(missing)}"],
                    remedy="Implement deterministic logic for all three decision types"
                ))
        else:
            self.add_result(AuditResult(
                name="Rules engine present",
                phase="Phase 1",
                status="fail",
                evidence=["No rules engine files found"],
                remedy="Create rules engine in src/orca/core/rules.py or equivalent"
            ))

        # Check for unit tests
        test_files = find_files_by_pattern('tests', '**/*test*rules*.py')
        if test_files:
            self.add_result(AuditResult(
                name="Rules unit tests",
                phase="Phase 1",
                status="pass",
                evidence=[f"Found rules tests: {[str(f) for f in test_files]}"]
            ))
        else:
            self.add_result(AuditResult(
                name="Rules unit tests",
                phase="Phase 1",
                status="fail",
                evidence=["No rules unit tests found"],
                remedy="Create unit tests for rules engine with >=1 test per outcome"
            ))

    def check_decision_contract(self) -> None:
        """D. Decision contract (Phase 1) checks."""
        print("📄 Checking decision contract...")

        # Look for decision contract files
        contract_files = find_files_by_name('src', '*decision*contract*.py')
        if not contract_files:
            contract_files = find_files_by_name('src', '*models*.py')

        if contract_files:
            self.add_result(AuditResult(
                name="Decision contract present",
                phase="Phase 1",
                status="pass",
                evidence=[f"Found contract files: {[str(f) for f in contract_files]}"]
            ))

            # Check for required fields
            required_fields = [
                'intent', 'cart', 'payment', 'modality', 'agent_presence',
                'trace_id', 'content_type', 'version', 'ml_model_version'
            ]

            found_fields = []
            missing_fields = []

            for contract_file in contract_files:
                for field in required_fields:
                    matches = search_in_files(f'\\b{field}\\b', [contract_file])
                    if matches:
                        found_fields.append(field)
                    else:
                        if field not in missing_fields:
                            missing_fields.append(field)

            if len(missing_fields) == 0:
                self.add_result(AuditResult(
                    name="Decision contract fields",
                    phase="Phase 1",
                    status="pass",
                    evidence=[f"All required fields present: {', '.join(found_fields)}"]
                ))
            else:
                self.add_result(AuditResult(
                    name="Decision contract fields",
                    phase="Phase 1",
                    status="fail",
                    evidence=[f"Missing fields: {', '.join(missing_fields)}"],
                    remedy="Add missing fields to decision contract model"
                ))
        else:
            self.add_result(AuditResult(
                name="Decision contract present",
                phase="Phase 1",
                status="fail",
                evidence=["No decision contract files found"],
                remedy="Create decision contract in src/orca/core/decision_contract.py"
            ))

    def check_cloudevents(self) -> None:
        """E. CloudEvents (Phase 1+) checks."""
        print("☁️ Checking CloudEvents...")

        # Look for CloudEvents emitter
        ce_files = find_files_by_name('src', '*ce*.py')
        if not ce_files:
            ce_files = find_files_by_pattern('src', '**/*event*.py')

        if ce_files:
            self.add_result(AuditResult(
                name="CloudEvents emitter present",
                phase="Phase 1",
                status="pass",
                evidence=[f"Found CE files: {[str(f) for f in ce_files]}"]
            ))

            # Check for ocn.orca.decision.v1 event type
            found_event_type = False
            for ce_file in ce_files:
                matches = search_in_files(r'ocn\.orca\.decision\.v1', [ce_file])
                if matches:
                    found_event_type = True
                    self.add_result(AuditResult(
                        name="Decision CloudEvent type",
                        phase="Phase 1",
                        status="pass",
                        evidence=[f"Found in {ce_file}: {matches[0][2]}"]
                    ))
                    break

            if not found_event_type:
                self.add_result(AuditResult(
                    name="Decision CloudEvent type",
                    phase="Phase 1",
                    status="fail",
                    evidence=["ocn.orca.decision.v1 event type not found"],
                    remedy="Implement CloudEvents with type 'ocn.orca.decision.v1'"
                ))
        else:
            self.add_result(AuditResult(
                name="CloudEvents emitter present",
                phase="Phase 1",
                status="fail",
                evidence=["No CloudEvents emitter found"],
                remedy="Create CloudEvents emitter in src/orca/core/ce.py"
            ))

    def check_cli_streamlit(self) -> None:
        """F. CLI & Streamlit demo (Phase 1) checks."""
        print("🖥️ Checking CLI & Streamlit demo...")

        # Check CLI
        cli_files = find_files_by_name('src', '*cli*.py')
        if cli_files:
            # Check for decide command
            has_decide = False
            for cli_file in cli_files:
                matches = search_in_files('def decide', [cli_file])
                if matches:
                    has_decide = True
                    break

            if has_decide:
                self.add_result(AuditResult(
                    name="CLI decide command",
                    phase="Phase 1",
                    status="pass",
                    evidence=[f"Found decide command in {[str(f) for f in cli_files]}"]
                ))
            else:
                self.add_result(AuditResult(
                    name="CLI decide command",
                    phase="Phase 1",
                    status="fail",
                    evidence=["CLI files found but no decide command"],
                    remedy="Implement 'orca decide --input <file.json>' command"
                ))
        else:
            self.add_result(AuditResult(
                name="CLI decide command",
                phase="Phase 1",
                status="fail",
                evidence=["No CLI files found"],
                remedy="Create CLI in src/orca/cli.py"
            ))

        # Check Streamlit app
        streamlit_ok, streamlit_evidence = check_streamlit_app()
        if streamlit_ok:
            self.add_result(AuditResult(
                name="Streamlit demo app",
                phase="Phase 1",
                status="pass",
                evidence=streamlit_evidence
            ))
        else:
            self.add_result(AuditResult(
                name="Streamlit demo app",
                phase="Phase 1",
                status="fail",
                evidence=streamlit_evidence,
                remedy="Create Streamlit app in src/orca/ui/app.py or examples/"
            ))

    def check_ml_stub(self) -> None:
        """G. ML stub (Phase 2) checks."""
        print("🤖 Checking ML stub...")

        # Look for ML prediction files
        ml_files = find_files_by_pattern('src', '**/*predict*risk*.py')
        if not ml_files:
            ml_files = find_files_by_pattern('src', '**/*ml*/*.py')

        if ml_files:
            self.add_result(AuditResult(
                name="ML prediction module",
                phase="Phase 2",
                status="pass",
                evidence=[f"Found ML files: {[str(f) for f in ml_files]}"]
            ))

            # Check for XGBoost and predict_risk function
            has_xgboost = False
            has_predict_risk = False
            has_random_state = False

            for ml_file in ml_files:
                xgb_matches = search_in_files('xgboost|XGBoost', [ml_file])
                if xgb_matches:
                    has_xgboost = True

                predict_matches = search_in_files('def predict_risk', [ml_file])
                if predict_matches:
                    has_predict_risk = True

                random_matches = search_in_files('random_state', [ml_file])
                if random_matches:
                    has_random_state = True

            if has_xgboost:
                self.add_result(AuditResult(
                    name="XGBoost integration",
                    phase="Phase 2",
                    status="pass",
                    evidence=["XGBoost references found in ML code"]
                ))
            else:
                self.add_result(AuditResult(
                    name="XGBoost integration",
                    phase="Phase 2",
                    status="warning",
                    evidence=["No XGBoost references found"],
                    remedy="Implement XGBoost model integration"
                ))

            if has_predict_risk:
                self.add_result(AuditResult(
                    name="predict_risk function",
                    phase="Phase 2",
                    status="pass",
                    evidence=["predict_risk function found"]
                ))
            else:
                self.add_result(AuditResult(
                    name="predict_risk function",
                    phase="Phase 2",
                    status="fail",
                    evidence=["No predict_risk function found"],
                    remedy="Implement predict_risk(features) function"
                ))

            if has_random_state:
                self.add_result(AuditResult(
                    name="Deterministic ML",
                    phase="Phase 2",
                    status="pass",
                    evidence=["Random state configuration found"]
                ))
            else:
                self.add_result(AuditResult(
                    name="Deterministic ML",
                    phase="Phase 2",
                    status="warning",
                    evidence=["No random state configuration found"],
                    remedy="Add fixed random_state for deterministic results"
                ))
        else:
            self.add_result(AuditResult(
                name="ML prediction module",
                phase="Phase 2",
                status="fail",
                evidence=["No ML prediction files found"],
                remedy="Create ML prediction in src/orca/ml/predict_risk*.py"
            ))

        # Check for feature mapping
        feature_files = find_files_by_pattern('src', '**/*feature*.py')
        if feature_files:
            self.add_result(AuditResult(
                name="Feature mapping",
                phase="Phase 2",
                status="pass",
                evidence=[f"Found feature files: {[str(f) for f in feature_files]}"]
            ))
        else:
            self.add_result(AuditResult(
                name="Feature mapping",
                phase="Phase 2",
                status="warning",
                evidence=["No feature mapping files found"],
                remedy="Implement feature mapping from AP2 to ML features"
            ))

    def check_llm_explanations(self) -> None:
        """H. LLM explanations (Phase 2) checks."""
        print("🧠 Checking LLM explanations...")

        # Look for LLM explainer files
        llm_files = find_files_by_name('src', '*llm*explain*.py')
        if not llm_files:
            llm_files = find_files_by_pattern('src', '**/*explain*.py')

        if llm_files:
            self.add_result(AuditResult(
                name="LLM explainer present",
                phase="Phase 2",
                status="pass",
                evidence=[f"Found LLM files: {[str(f) for f in llm_files]}"]
            ))

            # Check for required explanation keys
            required_keys = ['reason', 'key_signals', 'mitigation', 'confidence']
            found_keys = []

            for llm_file in llm_files:
                for key in required_keys:
                    matches = search_in_files(f'\\b{key}\\b', [llm_file])
                    if matches:
                        found_keys.append(key)

            if len(found_keys) >= 3:  # At least 3 of 4 keys
                self.add_result(AuditResult(
                    name="Explanation schema",
                    phase="Phase 2",
                    status="pass",
                    evidence=[f"Found explanation keys: {', '.join(found_keys)}"]
                ))
            else:
                self.add_result(AuditResult(
                    name="Explanation schema",
                    phase="Phase 2",
                    status="warning",
                    evidence=[f"Found keys: {', '.join(found_keys)}, missing: {', '.join(set(required_keys) - set(found_keys))}"],
                    remedy="Implement explanation with keys: reason, key_signals, mitigation, confidence"
                ))

            # Check for explanation CloudEvent
            has_explanation_event = False
            for llm_file in llm_files:
                matches = search_in_files(r'ocn\.orca\.explanation\.v1', [llm_file])
                if matches:
                    has_explanation_event = True
                    break

            if has_explanation_event:
                self.add_result(AuditResult(
                    name="Explanation CloudEvent",
                    phase="Phase 2",
                    status="pass",
                    evidence=["Found ocn.orca.explanation.v1 event type"]
                ))
            else:
                self.add_result(AuditResult(
                    name="Explanation CloudEvent",
                    phase="Phase 2",
                    status="warning",
                    evidence=["No explanation CloudEvent found"],
                    remedy="Emit CloudEvent ocn.orca.explanation.v1"
                ))
        else:
            self.add_result(AuditResult(
                name="LLM explainer present",
                phase="Phase 2",
                status="fail",
                evidence=["No LLM explainer files found"],
                remedy="Create LLM explainer in src/orca/explain/llm_explainer.py"
            ))

    def check_observability_redaction(self) -> None:
        """I. Observability & redaction (Foundations/Phase 2) checks."""
        print("🔍 Checking observability & redaction...")

        # Check trace_id propagation
        trace_files = find_files_by_pattern('src', '**/*.py')
        trace_matches = search_in_files('trace_id', trace_files)
        if trace_matches:
            self.add_result(AuditResult(
                name="Trace ID propagation",
                phase="Foundations",
                status="pass",
                evidence=[f"Found trace_id usage in {len(trace_matches)} locations"]
            ))
        else:
            self.add_result(AuditResult(
                name="Trace ID propagation",
                phase="Foundations",
                status="fail",
                evidence=["No trace_id usage found"],
                remedy="Implement trace_id propagation utilities"
            ))

        # Check log redaction
        redaction_ok, redaction_evidence = check_log_redaction()
        if redaction_ok:
            self.add_result(AuditResult(
                name="Log redaction",
                phase="Phase 2",
                status="pass",
                evidence=["No PII patterns found in logs"]
            ))
        else:
            self.add_result(AuditResult(
                name="Log redaction",
                phase="Phase 2",
                status="warning",
                evidence=redaction_evidence,
                remedy="Implement log redaction filter for PCI/PII"
            ))

    def check_weave_integration(self) -> None:
        """J. Weave integration hooks (Phase 1 evidence) checks."""
        print("🔗 Checking Weave integration hooks...")

        # Look for HTTP subscriber configuration
        config_files = find_files_by_pattern('src', '**/*config*.py')
        has_http_config = False

        for config_file in config_files:
            matches = search_in_files('(http|subscriber|url|endpoint)', [config_file])
            if matches:
                has_http_config = True
                break

        if has_http_config:
            self.add_result(AuditResult(
                name="HTTP subscriber config",
                phase="Phase 1",
                status="pass",
                evidence=["Found HTTP/subscriber configuration"]
            ))
        else:
            self.add_result(AuditResult(
                name="HTTP subscriber config",
                phase="Phase 1",
                status="warning",
                evidence=["No HTTP subscriber configuration found"],
                remedy="Add configurable HTTP subscriber URL for decision CE"
            ))

    def check_tests_coverage(self) -> None:
        """K. Tests & coverage gates checks."""
        print("🧪 Checking tests & coverage...")

        # Run pytest and coverage
        pytest_ok, pytest_results = run_pytest_coverage()

        if pytest_ok:
            self.add_result(AuditResult(
                name="pytest runs without error",
                phase="Phase 1",
                status="pass",
                evidence=["pytest completed successfully"]
            ))

            # Check coverage
            coverage_percentage = get_coverage_percentage(pytest_results.get('coverage_data'))
            if coverage_percentage >= 80:
                self.add_result(AuditResult(
                    name="Coverage threshold ≥80%",
                    phase="Phase 1",
                    status="pass",
                    evidence=[f"Coverage: {coverage_percentage:.1f}%"]
                ))
            else:
                self.add_result(AuditResult(
                    name="Coverage threshold ≥80%",
                    phase="Phase 1",
                    status="fail",
                    evidence=[f"Coverage: {coverage_percentage:.1f}%"],
                    remedy="Increase test coverage to ≥80%"
                ))
        else:
            self.add_result(AuditResult(
                name="pytest runs without error",
                phase="Phase 1",
                status="fail",
                evidence=[f"pytest failed: {pytest_results.get('error', 'Unknown error')}"],
                remedy="Fix failing tests"
            ))

    def check_github_workflows(self) -> None:
        """L. GitHub workflows (Foundations) checks."""
        print("🔄 Checking GitHub workflows...")

        workflow_files = find_files_by_pattern('.github/workflows', '*.yml')
        required_workflows = ['ci.yml', 'contracts.yml', 'security.yml']

        found_workflows = [f.name for f in workflow_files]
        missing_workflows = [w for w in required_workflows if w not in found_workflows]

        if not missing_workflows:
            self.add_result(AuditResult(
                name="Required GitHub workflows",
                phase="Foundations",
                status="pass",
                evidence=[f"Found workflows: {', '.join(found_workflows)}"]
            ))
        else:
            self.add_result(AuditResult(
                name="Required GitHub workflows",
                phase="Foundations",
                status="fail",
                evidence=[f"Missing workflows: {', '.join(missing_workflows)}"],
                remedy="Add missing workflow files: " + ', '.join(missing_workflows)
            ))

        # Check for specific workflow content
        if Path('.github/workflows/ci.yml').exists():
            ci_content = Path('.github/workflows/ci.yml').read_text()
            if 'black' in ci_content.lower() and 'ruff' in ci_content.lower():
                self.add_result(AuditResult(
                    name="CI workflow linting",
                    phase="Foundations",
                    status="pass",
                    evidence=["CI workflow includes Black and Ruff"]
                ))
            else:
                self.add_result(AuditResult(
                    name="CI workflow linting",
                    phase="Foundations",
                    status="warning",
                    evidence=["CI workflow missing Black/Ruff"],
                    remedy="Add Black and Ruff to CI workflow"
                ))

    def check_tags_versions(self) -> None:
        """M. Tags/versions (Phase 1 evidence) checks."""
        print("🏷️ Checking tags/versions...")

        # Check for version in pyproject.toml
        pyproject_path = Path('pyproject.toml')
        if pyproject_path.exists():
            pyproject_data = load_json_file(pyproject_path)
            if pyproject_data and 'project' in pyproject_data:
                version = pyproject_data['project'].get('version')
                if version:
                    self.add_result(AuditResult(
                        name="Version in pyproject.toml",
                        phase="Phase 1",
                        status="pass",
                        evidence=[f"Version: {version}"]
                    ))
                else:
                    self.add_result(AuditResult(
                        name="Version in pyproject.toml",
                        phase="Phase 1",
                        status="fail",
                        evidence=["No version field in pyproject.toml"],
                        remedy="Add version field to pyproject.toml"
                    ))

        # Check git tags
        git_tags = check_git_tags()
        if git_tags:
            self.add_result(AuditResult(
                name="Git tags available",
                phase="Phase 1",
                status="pass",
                evidence=[f"Found {len(git_tags)} git tags: {', '.join(git_tags[:5])}" + ("..." if len(git_tags) > 5 else "")]
            ))
        else:
            self.add_result(AuditResult(
                name="Git tags available",
                phase="Phase 1",
                status="warning",
                evidence=["No git tags found"],
                remedy="Create version tags (e.g., v0.1.0+ap2.v1+ce.v1)"
            ))

    def generate_reports(self) -> None:
        """Generate both markdown and JSON reports."""
        print("\n📊 Generating audit reports...")

        # Generate summary
        foundations_results = [r for r in self.results if r.phase == "Foundations"]
        phase1_results = [r for r in self.results if r.phase == "Phase 1"]
        phase2_results = [r for r in self.results if r.phase == "Phase 2"]

        foundations_passed = len([r for r in foundations_results if r.status == "pass"])
        phase1_passed = len([r for r in phase1_results if r.status == "pass"])
        phase2_passed = len([r for r in phase2_results if r.status == "pass"])

        # Generate markdown report
        self.generate_markdown_report(foundations_passed, len(foundations_results),
                                    phase1_passed, len(phase1_results),
                                    phase2_passed, len(phase2_results))

        # Generate JSON report
        self.generate_json_report()

        # Determine exit code
        phase1_failures = [r for r in phase1_results if r.status == "fail"]
        if phase1_failures:
            print(f"\n❌ Audit failed: {len(phase1_failures)} Phase 1 blocking items failed")
            for failure in phase1_failures:
                print(f"   - {failure.name}")
            sys.exit(1)
        else:
            print(f"\n✅ Audit passed: All Phase 1 blocking items passed")
            sys.exit(0)

    def generate_markdown_report(self, foundations_passed: int, foundations_total: int,
                               phase1_passed: int, phase1_total: int,
                               phase2_passed: int, phase2_total: int) -> None:
        """Generate markdown audit report."""
        with open('AUDIT_REPORT.md', 'w') as f:
            f.write("# OCN Orca Audit — Foundations / Phase 1 / Phase 2\n\n")
            f.write(f"**Audit Date:** {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")

            # Summary
            f.write("## Summary\n")
            f.write(f"- Foundations: {foundations_passed}/{foundations_total} ✅\n")
            f.write(f"- Phase 1: {phase1_passed}/{phase1_total} ✅\n")
            f.write(f"- Phase 2: {phase2_passed}/{phase2_total} ✅\n\n")

            # Results by phase
            for phase in ["Foundations", "Phase 1", "Phase 2"]:
                phase_results = [r for r in self.results if r.phase == phase]
                if phase_results:
                    f.write(f"## {phase}\n")
                    for result in phase_results:
                        checkbox = "✅" if result.status == "pass" else "❌" if result.status == "fail" else "⚠️"
                        f.write(f"- [{checkbox}] {result.name}")

                        if result.evidence:
                            f.write(f" — {result.evidence[0]}")

                        f.write("\n")

                        if result.remedy:
                            f.write(f"  - **Remedy:** {result.remedy}\n")

                    f.write("\n")

    def generate_json_report(self) -> None:
        """Generate JSON audit report."""
        report_data = {
            "audit_date": self.start_time.isoformat(),
            "summary": {
                "foundations": {
                    "passed": len([r for r in self.results if r.phase == "Foundations" and r.status == "pass"]),
                    "total": len([r for r in self.results if r.phase == "Foundations"])
                },
                "phase1": {
                    "passed": len([r for r in self.results if r.phase == "Phase 1" and r.status == "pass"]),
                    "total": len([r for r in self.results if r.phase == "Phase 1"])
                },
                "phase2": {
                    "passed": len([r for r in self.results if r.phase == "Phase 2" and r.status == "pass"]),
                    "total": len([r for r in self.results if r.phase == "Phase 2"])
                }
            },
            "results": [result.to_dict() for result in self.results]
        }

        with open('audit_report.json', 'w') as f:
            json.dump(report_data, f, indent=2)


def main():
    """Main audit function."""
    auditor = OrcaAuditor()
    auditor.run_all_checks()
    auditor.generate_reports()


if __name__ == "__main__":
    main()
