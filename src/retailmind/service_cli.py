"""CLI dispatcher for train, evaluate, freeze, recommend, monitor, and benchmark subcommands."""

import argparse
import json
import time
from pathlib import Path

import numpy as np

from retailmind.contracts import RecommendationRequest
from retailmind.experiments import (
    freeze_selection,
    run_test_pipeline,
    run_validation_pipeline,
)
from retailmind.monitoring import run_drift_diagnostics
from retailmind.service import RetailMindService


def dispatch_service_cli(args: argparse.Namespace) -> None:
    """Dispatch service and experiment CLI commands."""
    cmd = args.command

    if cmd == "train":
        if args.stage == "validation":
            print("Running training for validation stage...")
            run_validation_pipeline(args.config)
        elif args.stage == "test":
            print("Running training for test stage (refit frozen models)...")
            run_test_pipeline(args.config)

    elif cmd == "evaluate":
        if args.stage == "validation":
            print("Validation stage evaluation results already produced during 'train --stage validation'.")
            val_path = Path("reports/validation_metrics.json")
            if val_path.exists():
                with open(val_path, "r", encoding="utf-8") as f:
                    print(f.read())
            else:
                run_validation_pipeline(args.config)
        elif args.stage == "test":
            test_path = Path("reports/test_metrics.json")
            if test_path.exists():
                with open(test_path, "r", encoding="utf-8") as f:
                    print(f.read())
            else:
                run_test_pipeline(args.config)

    elif cmd == "freeze":
        print("Freezing model selection from validation...")
        freeze_selection(args.config)

    elif cmd == "recommend":
        service = RetailMindService(args.bundle)
        req = RecommendationRequest(
            customer_id=args.customer_id,
            top_k=args.top_k,
            mode=args.mode,
            bundle=args.bundle,
        )
        resp = service.recommend(req)
        print(resp.model_dump_json(indent=2))

    elif cmd == "monitor":
        print(f"Running batch diagnostics: {args.reference} vs {args.current}...")
        diag_report = run_drift_diagnostics(
            ref_path=args.reference,
            cur_path=args.current,
            output_path=args.output,
        )
        print(json.dumps(diag_report, indent=2))

    elif cmd == "benchmark":
        print(f"Benchmarking warm recommendation latency on {args.bundle}...")
        service = RetailMindService(args.bundle)

        # Build mix of active, inactive, and unknown customers
        active_ids = [
            cid
            for cid, prof in service.profile_lookup.items()
            if prof.get("status") == "known_active"
        ][:70]
        inactive_ids = [
            cid
            for cid, prof in service.profile_lookup.items()
            if prof.get("status") == "known_inactive"
        ][:20]
        unknown_ids = [f"BENCH_UNK_{i}" for i in range(10)]

        test_pool = active_ids + inactive_ids + unknown_ids
        if not test_pool:
            test_pool = ["DEMO-001", "DEMO-002", "DEMO-003"]

        # 1. Warm-up requests
        for i in range(args.warmup):
            cid = test_pool[i % len(test_pool)]
            req = RecommendationRequest(
                customer_id=cid,
                top_k=args.top_k,
                mode="repeat_allowed",
                bundle=args.bundle,
            )
            service.recommend(req)

        # 2. Timed benchmark requests
        durations = []
        for i in range(args.calls):
            cid = test_pool[i % len(test_pool)]
            req = RecommendationRequest(
                customer_id=cid,
                top_k=args.top_k,
                mode="repeat_allowed",
                bundle=args.bundle,
            )
            t0 = time.perf_counter()
            service.recommend(req)
            t1 = time.perf_counter()
            durations.append((t1 - t0) * 1000.0)  # ms

        durations_arr = np.array(durations)
        latency_report = {
            "bundle": args.bundle,
            "bundle_version": service.manifest.bundle_version,
            "top_k": args.top_k,
            "num_calls": args.calls,
            "warmup_calls": args.warmup,
            "median_ms": round(float(np.median(durations_arr)), 3),
            "p95_ms": round(float(np.percentile(durations_arr, 95)), 3),
            "p99_ms": round(float(np.percentile(durations_arr, 99)), 3),
            "max_ms": round(float(np.max(durations_arr)), 3),
            "min_ms": round(float(np.min(durations_arr)), 3),
            "mean_ms": round(float(np.mean(durations_arr)), 3),
            "p95_target_met": bool(np.percentile(durations_arr, 95) <= 200.0),
        }

        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(latency_report, f, indent=2)

        print("Latency benchmark complete:")
        print(f"  Calls: {args.calls}")
        print(f"  Median: {latency_report['median_ms']} ms")
        print(f"  P95: {latency_report['p95_ms']} ms (Target <= 200 ms: {latency_report['p95_target_met']})")
        print(f"  Max: {latency_report['max_ms']} ms")
        print(f"Saved latency report to {out_path}")
