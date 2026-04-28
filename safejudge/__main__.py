"""SafeJudge CLI — orchestrates the full evaluation pipeline."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

from safejudge.config import ALL_MODES, EVIDENCE_DIR, MODE_SINGLE, RESULTS_DIR
from safejudge.dataset import load_dataset, validate_dataset, get_summary_stats
from safejudge.evidence_package import build_evidence_package, generate_run_id, get_config_snapshot
from safejudge.gates import evaluate_gates, generate_gate_report
from safejudge.judge import judge_batch, judge_consistency_check
from safejudge.metrics import compute_all_metrics, compute_judge_summary, MetricReport
from safejudge.reports import generate_all_reports
from safejudge.runner import run_batch


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="safejudge",
        description="SafeJudge — Multi-Model LLM-as-a-Judge Evaluation Pipeline",
    )
    parser.add_argument(
        "--dataset-dir",
        type=Path,
        default=Path("datasets"),
        help="Directory containing labeled test cases (default: datasets/)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=RESULTS_DIR,
        help="Directory for raw evaluation results (default: results/)",
    )
    parser.add_argument(
        "--evidence-dir",
        type=Path,
        default=EVIDENCE_DIR,
        help="Directory for generated reports and artifacts (default: evidence/)",
    )
    parser.add_argument(
        "--modes",
        type=str,
        default=MODE_SINGLE,
        help=f"Comma-separated evaluation modes (default: {MODE_SINGLE}). Options: {','.join(ALL_MODES)}",
    )
    parser.add_argument(
        "--skip-judge",
        action="store_true",
        help="Skip LLM-as-a-Judge scoring (faster runs)",
    )
    parser.add_argument(
        "--sut-dir",
        type=Path,
        default=Path("analyze-prompt-intent"),
        help="Path to the analyze-prompt-intent directory (default: analyze-prompt-intent/)",
    )
    parser.add_argument(
        "--sample",
        type=int,
        default=0,
        help="Run on a random sample of N test cases (0 = all)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    modes = [m.strip() for m in args.modes.split(",")]
    run_id = generate_run_id()

    print("=" * 60)
    print("  SafeJudge Evaluation Pipeline")
    print(f"  Run ID: {run_id}")
    print("=" * 60)

    # ── Step 1: Load and validate dataset ─────────────────────────────
    print("\n[1/7] Loading dataset...")
    prompts_dir = args.dataset_dir / "prompts"
    conversations_dir = args.dataset_dir / "conversations"
    dataset = load_dataset(prompts_dir, conversations_dir)

    errors = validate_dataset(dataset)
    if errors:
        print("  Dataset validation warnings:")
        for e in errors:
            print(f"    - {e}")

    if not dataset:
        print("  ERROR: No test cases found. Exiting.")
        return 1

    if args.sample > 0:
        import random
        dataset = random.sample(dataset, min(args.sample, len(dataset)))
        print(f"  Sampled {len(dataset)} test cases")

    stats = get_summary_stats(dataset)
    print(f"  Loaded {stats['total']} test cases "
          f"({stats['malicious']} malicious, {stats['benign']} benign, "
          f"{stats['multi_turn']} multi-turn)")

    # ── Step 2: Run batch evaluation ──────────────────────────────────
    print(f"\n[2/7] Running evaluation (modes: {', '.join(modes)})...")

    # Override SUT_DIR if specified
    if args.sut_dir:
        import safejudge.config as cfg
        cfg.SUT_DIR = args.sut_dir.resolve()

    results = run_batch(dataset, modes=modes, output_dir=args.output_dir)
    succeeded = sum(1 for r in results if r.succeeded)
    print(f"  Completed: {succeeded}/{len(results)} succeeded")

    # ── Step 3: LLM Judge scoring ─────────────────────────────────────
    judge_scores = []
    judge_summary: dict = {"total": 0, "valid": 0, "error_count": 0}

    if not args.skip_judge:
        print("\n[3/7] Running LLM-as-a-Judge scoring...")
        judge_scores = judge_batch(results)
        judge_summary = compute_judge_summary(judge_scores)
        print(f"  Scored: {judge_summary['valid']}/{judge_summary['total']} valid")

        # Save judge scores
        args.output_dir.mkdir(parents=True, exist_ok=True)
        judge_path = args.output_dir / "judge_scores.json"
        with open(judge_path, "w") as f:
            json.dump([asdict(s) for s in judge_scores], f, indent=2)
    else:
        print("\n[3/7] Skipping LLM-as-a-Judge scoring (--skip-judge)")

    # ── Step 4: Compute metrics & evaluate gates ────────────────────
    print("\n[4/7] Computing metrics...")
    metric_report = compute_all_metrics(results)
    gate_result = evaluate_gates(metric_report)
    print(f"  Overall accuracy: {metric_report.overall_accuracy:.1%}")
    print(f"  Jailbreak recall: {metric_report.jailbreak.recall:.1%}")
    print(f"  Harmful recall: {metric_report.harmful_content.recall:.1%}")
    print(f"  Benign FPR: {metric_report.benign_false_positive_rate:.1%}")
    print(f"  Gate verdict: {gate_result.overall_verdict}")

    # Save metrics
    args.evidence_dir.mkdir(parents=True, exist_ok=True)
    metrics_path = args.evidence_dir / "metric_summary.json"
    with open(metrics_path, "w") as f:
        json.dump(metric_report.to_dict(), f, indent=2)

    # ── Step 5: Generate reports ──────────────────────────────────────
    print("\n[5/7] Generating reports...")
    report_paths = generate_all_reports(
        results, metric_report, judge_summary,
        gate_verdict=gate_result.overall_verdict,
        run_id=run_id,
        output_dir=args.evidence_dir,
    )

    # ── Step 6: Evaluate release gates ────────────────────────────────
    print("\n[6/7] Evaluating release gates...")
    gate_path = generate_gate_report(gate_result, args.evidence_dir)

    # ── Step 7: Build evidence package ────────────────────────────────
    print("\n[7/7] Building evidence package...")
    config_snapshot = get_config_snapshot()
    config_snapshot["modes"] = modes
    config_snapshot["sample_size"] = args.sample
    config_snapshot["skip_judge"] = args.skip_judge
    package_path = build_evidence_package(
        run_id=run_id,
        evidence_dir=args.evidence_dir,
        config_snapshot=config_snapshot,
        gate_verdict=gate_result.overall_verdict,
        total_evaluated=len(results),
        total_succeeded=succeeded,
    )

    # ── Summary ───────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print(f"  Run ID: {run_id}")
    print(f"  VERDICT: {gate_result.overall_verdict}")
    print("=" * 60)
    for d in gate_result.decisions:
        status = "PASS" if d.passed else d.severity
        print(f"  {d.gate_name}: {d.metric_value:.1%} "
              f"(threshold: {d.threshold:.0%}) — {status}")
    print(f"\n  Reports generated: {len(report_paths) + 1}")
    print(f"  Evidence directory: {args.evidence_dir}")
    print("=" * 60)

    return 0 if gate_result.all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
