"""Experiment orchestration: validation training, selection freeze, final test refit, and tracking."""

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

import joblib
import mlflow
import numpy as np
import pandas as pd
import yaml
from scipy.sparse import save_npz

from retailmind.contracts import BundleManifest
from retailmind.data import compute_file_sha256
from retailmind.evaluation import (
    evaluate_model_on_cohort,
    extract_evaluation_cohorts,
    paired_bootstrap_ci,
)
from retailmind.features import build_catalog_and_interactions, build_snapshot_rfm
from retailmind.recommenders import (
    GlobalPopularityRecommender,
    ItemItemCollaborativeFiltering,
    SegmentPopularityRecommender,
)
from retailmind.segmentation import (
    evaluate_clustering_candidates,
    fit_and_profile_selected_segmenter,
)


def compute_string_sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest().upper()


def save_bundle(
    bundle_dir: Path | str,
    manifest: BundleManifest,
    segmenter: Any,
    scaler: Optional[Any],
    df_profiles: pd.DataFrame,
    df_segment_summaries: pd.DataFrame,
    catalog_items: list[str],
    item_descriptions: dict[str, str],
    global_pop: GlobalPopularityRecommender,
    seg_pop: SegmentPopularityRecommender,
    cf_model: Optional[ItemItemCollaborativeFiltering],
    interaction_csr: Any,
    customer_to_idx: dict[str, int],
    item_to_idx: dict[str, int],
    purchases_history: pd.DataFrame,
) -> Path:
    """Save an immutable model bundle directory with manifest and artifacts."""
    b_path = Path(bundle_dir)
    b_path.mkdir(parents=True, exist_ok=True)

    # Save manifest
    with open(b_path / "manifest.json", "w", encoding="utf-8") as f:
        f.write(manifest.model_dump_json(indent=2))

    # Save tables
    df_profiles.to_parquet(b_path / "customer_profiles.parquet", index=False)
    df_segment_summaries.to_parquet(b_path / "segment_summaries.parquet", index=False)

    # Save catalog and descriptions
    with open(b_path / "catalog.json", "w", encoding="utf-8") as f:
        json.dump(
            {
                "catalog_items": catalog_items,
                "item_descriptions": item_descriptions,
                "customer_to_idx": customer_to_idx,
                "item_to_idx": item_to_idx,
            },
            f,
            indent=2,
        )

    # Save sparse interactions
    save_npz(b_path / "interaction_csr.npz", interaction_csr)

    # Save joblib models
    joblib.dump(
        {
            "segmenter": segmenter,
            "scaler": scaler,
            "global_pop": global_pop,
            "seg_pop": seg_pop,
            "cf_model": cf_model,
        },
        b_path / "models.joblib",
    )

    # Save raw purchase history lookup for serving mode filters
    hist_lookup = purchases_history.groupby("CustomerID")["StockCode"].unique().to_dict()
    # Convert ndarrays to lists for JSON
    hist_lookup_serializable = {str(k): list(v) for k, v in hist_lookup.items()}
    with open(b_path / "customer_history.json", "w", encoding="utf-8") as f:
        json.dump(hist_lookup_serializable, f)

    return b_path


def run_validation_pipeline(config_path: str | Path) -> Dict[str, Any]:
    """Execute the validation phase: segment comparison, recommender comparison, and metrics."""
    with open(config_path, "r", encoding="utf-8") as f:
        config_text = f.read()
        config = yaml.safe_load(config_text)

    config_sha256 = compute_string_sha256(config_text)
    lock_path = Path("requirements.lock")
    lock_sha256 = compute_file_sha256(lock_path) if lock_path.exists() else "UNLOCKED"

    ds_cfg = config["dataset"]
    temp_cfg = config["temporal"]["validation"]
    seg_cfg = config["segmentation"]
    rec_cfg = config["recommenders"]

    processed_path = Path(ds_cfg["processed_parquet_path"])
    if not processed_path.exists():
        raise FileNotFoundError(
            f"Processed purchases table not found at {processed_path}. Run 'prepare' first."
        )

    df_purchases = pd.read_parquet(processed_path)
    source_sha256 = compute_file_sha256(ds_cfg["raw_xlsx_path"])

    cutoff = pd.to_datetime(temp_cfg["cutoff"])
    future_start = pd.to_datetime(temp_cfg["future_start"])
    future_end = pd.to_datetime(temp_cfg["future_end"])

    print(f"=== Running Validation Stage (Cutoff: {cutoff}) ===")

    # 1. Build RFM profiles strictly before cutoff
    df_profiles, rfm_meta = build_snapshot_rfm(
        df_purchases, cutoff=cutoff, rfm_window_days=180
    )
    df_active = df_profiles[df_profiles["status"] == "known_active"].copy()
    print(
        f"Built RFM snapshot: {len(df_profiles):,} known customers ({len(df_active):,} active)."
    )

    # 2. Compare segmentation candidates
    df_seg_comp, selected_seg_info = evaluate_clustering_candidates(
        df_active,
        seeds=seg_cfg.get("seeds", [42, 43, 44, 45, 46]),
        kmeans_k_candidates=seg_cfg.get("kmeans_k_candidates", [3, 4, 5, 6]),
        gmm_components_candidates=seg_cfg.get("gmm_components_candidates", [3, 4, 5, 6]),
        gmm_covariance_types=seg_cfg.get("gmm_covariance_types", ["full", "diag"]),
        transform_method=seg_cfg.get("transform_method", "yeo_johnson"),
        min_cluster_share=seg_cfg.get("min_cluster_share", 0.03),
        min_median_ari=seg_cfg.get("min_median_ari", 0.80),
        min_mean_silhouette=seg_cfg.get("min_mean_silhouette", 0.30),
        sample_size=seg_cfg.get("silhouette_sample_size", 2000),
    )

    # Save cluster comparison CSV
    reports_dir = Path("reports")
    reports_dir.mkdir(parents=True, exist_ok=True)
    df_seg_comp.to_csv(reports_dir / "cluster_comparison.csv", index=False)
    print("Saved cluster comparison to reports/cluster_comparison.csv")
    print(f"Selected segmentation model: {selected_seg_info}")

    # Fit selected segmenter
    segmenter, scaler, df_segment_summaries, seg_profiles_dict = fit_and_profile_selected_segmenter(
        df_active, selected_seg_info, seed=seg_cfg.get("primary_seed", 42)
    )
    df_segment_summaries.to_csv(reports_dir / "segment_profiles.csv", index=False)

    # Assign segment IDs to all active profiles
    if selected_seg_info.get("is_rule_baseline", False):
        seg_ids, seg_labels = segmenter.predict(df_profiles)
        df_profiles["segment_id"] = seg_ids
        df_profiles["segment_label"] = seg_labels
    else:
        # Predict on active
        from retailmind.segmentation import extract_raw_rfm_matrix
        t_method = selected_seg_info.get("transform_method", "yeo_johnson")
        X_raw_active = extract_raw_rfm_matrix(df_active) if t_method != "log1p" else np.log1p(extract_raw_rfm_matrix(df_active))
        X_active = scaler.transform(X_raw_active)
        raw_preds = segmenter.predict(X_active)
        c_to_s = segmenter.cluster_to_seg_id_
        active_seg_ids = [c_to_s[c] for c in raw_preds]
        active_seg_labels = [seg_profiles_dict[s]["segment_label"] for s in active_seg_ids]

        df_profiles["segment_id"] = None
        df_profiles["segment_label"] = None

        active_indices = df_profiles[df_profiles["status"] == "known_active"].index
        df_profiles.loc[active_indices, "segment_id"] = active_seg_ids
        df_profiles.loc[active_indices, "segment_label"] = active_seg_labels

        inactive_indices = df_profiles[df_profiles["status"] == "known_inactive"].index
        df_profiles.loc[inactive_indices, "segment_id"] = "SG_INACTIVE"
        df_profiles.loc[inactive_indices, "segment_label"] = "Inactive (Outside 180-Day Window)"

    cust_seg_map = dict(zip(df_profiles["customer_id"], df_profiles["segment_id"]))

    # 3. Build catalog and interaction matrix
    history_purchases = df_purchases[df_purchases["InvoiceDate"] < cutoff].copy()
    (
        catalog_items,
        item_descriptions,
        user_items,
        interaction_csr,
        customer_to_idx,
        item_to_idx,
    ) = build_catalog_and_interactions(
        df_purchases,
        cutoff=cutoff,
        min_distinct_buyers=config["catalog"].get("min_distinct_buyers", 5),
        active_window_days=config["catalog"].get("active_window_days", 90),
    )
    print(f"Extracted eligible catalog: {len(catalog_items):,} items.")

    # 4. Fit recommenders
    global_pop = GlobalPopularityRecommender().fit(
        history_purchases, catalog_items, cutoff=cutoff
    )
    seg_pop = SegmentPopularityRecommender().fit(
        history_purchases, cust_seg_map, catalog_items, cutoff=cutoff
    )

    cf_candidates: Dict[int, ItemItemCollaborativeFiltering] = {}
    for n_neighbors in rec_cfg.get("cf_neighbor_candidates", [50, 100]):
        cf_model = ItemItemCollaborativeFiltering(
            top_n_neighbors=n_neighbors,
            min_co_buyers=rec_cfg.get("cf_min_co_buyers", 2),
            block_size=rec_cfg.get("cf_block_size", 256),
        )
        cf_model.fit(
            interaction_csr,
            catalog_items,
            customer_to_idx,
            item_to_idx,
            history_purchases,
        )
        cf_candidates[n_neighbors] = cf_model

    # 5. Extract evaluation cohorts
    cohort_data = extract_evaluation_cohorts(
        df_purchases,
        cutoff=cutoff,
        future_start=future_start,
        future_end=future_end,
        catalog_items=catalog_items,
    )

    primary_users = cohort_data["primary_cohort_users"]
    primary_gt = cohort_data["primary_ground_truth"]
    print(f"Primary evaluation cohort: {len(primary_users):,} known returners.")

    # 6. Evaluate all models on primary cohort
    top_k = rec_cfg.get("top_k", 10)
    results_dict: Dict[str, Any] = {}

    eval_global = evaluate_model_on_cohort(
        global_pop,
        primary_users,
        primary_gt,
        catalog_items,
        cust_seg_map,
        seg_pop,
        global_pop,
        mode="repeat_allowed",
        k=top_k,
        model_name="GlobalPopularity",
    )
    results_dict["GlobalPopularity"] = eval_global

    eval_seg = evaluate_model_on_cohort(
        seg_pop,
        primary_users,
        primary_gt,
        catalog_items,
        cust_seg_map,
        seg_pop,
        global_pop,
        mode="repeat_allowed",
        k=top_k,
        model_name="SegmentPopularity",
    )
    results_dict["SegmentPopularity"] = eval_seg

    # Determine strongest baseline
    if eval_seg["mean_ndcg"] > eval_global["mean_ndcg"]:
        strongest_baseline_name = "SegmentPopularity"
        strongest_baseline_eval = eval_seg
    else:
        strongest_baseline_name = "GlobalPopularity"
        strongest_baseline_eval = eval_global

    # Evaluate CF models
    best_cf_name = None
    best_cf_ndcg = -1.0
    best_cf_model = None

    for n_neighbors, cf_model in cf_candidates.items():
        name = f"ItemItemCF_N{n_neighbors}"
        eval_cf = evaluate_model_on_cohort(
            cf_model,
            primary_users,
            primary_gt,
            catalog_items,
            cust_seg_map,
            seg_pop,
            global_pop,
            mode="repeat_allowed",
            k=top_k,
            model_name=name,
        )
        results_dict[name] = eval_cf
        if eval_cf["mean_ndcg"] > best_cf_ndcg:
            best_cf_ndcg = eval_cf["mean_ndcg"]
            best_cf_name = name
            best_cf_model = cf_model

    # 7. Bootstrap significance check on best CF vs strongest baseline
    best_cf_eval = results_dict[best_cf_name]
    cf_ndcg_scores = np.array([m["ndcg_at_k"] for m in best_cf_eval["per_user_metrics"]])
    base_ndcg_scores = np.array([m["ndcg_at_k"] for m in strongest_baseline_eval["per_user_metrics"]])

    ci_cf, ci_base, ci_diff = paired_bootstrap_ci(
        cf_ndcg_scores,
        base_ndcg_scores,
        n_bootstraps=rec_cfg.get("bootstrap_samples", 1000),
        seed=rec_cfg.get("bootstrap_seed", 42),
    )

    # Relative NDCG gain
    base_ndcg = strongest_baseline_eval["mean_ndcg"]
    rel_gain = (
        (best_cf_eval["mean_ndcg"] - base_ndcg) / base_ndcg if base_ndcg > 0 else 0.0
    )

    min_rel_gain = rec_cfg.get("min_relative_ndcg_gain", 0.10)
    cf_qualifies = (
        (rel_gain >= min_rel_gain)
        and (best_cf_eval["mean_recall"] >= strongest_baseline_eval["mean_recall"])
        and (ci_diff[0] > 0.0)
    )

    if cf_qualifies:
        selected_rec_name = best_cf_name
        selected_rec_algorithm = "ItemItemCollaborativeFiltering"
        selected_rec_params = {"top_n_neighbors": int(best_cf_name.split("_N")[1])}
    else:
        selected_rec_name = strongest_baseline_name
        selected_rec_algorithm = strongest_baseline_name
        selected_rec_params = {}

    print(f"Strongest baseline: {strongest_baseline_name} (NDCG@10: {base_ndcg:.4f})")
    print(f"Best CF: {best_cf_name} (NDCG@10: {best_cf_eval['mean_ndcg']:.4f}, Rel Gain: {rel_gain:.2%}, 95% CI Diff: [{ci_diff[0]:.4f}, {ci_diff[1]:.4f}])")
    print(f"Selected Recommender: {selected_rec_name} (CF Qualifies: {cf_qualifies})")

    # Clean per-user metrics for summary JSON
    summary_results = {}
    for m_name, m_eval in results_dict.items():
        summary_results[m_name] = {k: v for k, v in m_eval.items() if k != "per_user_metrics"}

    validation_report = {
        "stage": "validation",
        "snapshot_cutoff": str(cutoff),
        "holdout_start": str(future_start),
        "holdout_end": str(future_end),
        "catalog_size": len(catalog_items),
        "primary_cohort_size": len(primary_users),
        "future_item_coverage": round(cohort_data["future_item_coverage"], 4),
        "models": summary_results,
        "strongest_baseline": strongest_baseline_name,
        "selected_recommender": selected_rec_name,
        "cf_qualifies": cf_qualifies,
        "relative_ndcg_gain": round(rel_gain, 4),
        "bootstrap_ci_95": {
            "cf_ndcg": [round(ci_cf[0], 4), round(ci_cf[1], 4)],
            "baseline_ndcg": [round(ci_base[0], 4), round(ci_base[1], 4)],
            "difference_ndcg": [round(ci_diff[0], 4), round(ci_diff[1], 4)],
        },
        "selected_segmentation": selected_seg_info,
    }

    with open(reports_dir / "validation_metrics.json", "w", encoding="utf-8") as f:
        json.dump(validation_report, f, indent=2)

    # 8. Save validation bundle
    manifest = BundleManifest(
        bundle_version="0.1.0-val",
        stage="validation",
        snapshot_cutoff=str(cutoff),
        created_at=datetime.now(timezone.utc).isoformat(),
        source_sha256=source_sha256,
        config_sha256=config_sha256,
        lock_sha256=lock_sha256,
        segment_algorithm=selected_seg_info["selected_family"],
        segment_params=selected_seg_info,
        recommender_algorithm=selected_rec_algorithm,
        recommender_params=selected_rec_params,
        catalog_size=len(catalog_items),
        active_customers_count=len(df_active),
        known_customers_count=len(df_profiles),
        reports={"validation_metrics": "reports/validation_metrics.json"},
    )

    save_bundle(
        bundle_dir="artifacts/validation",
        manifest=manifest,
        segmenter=segmenter,
        scaler=scaler,
        df_profiles=df_profiles,
        df_segment_summaries=df_segment_summaries,
        catalog_items=catalog_items,
        item_descriptions=item_descriptions,
        global_pop=global_pop,
        seg_pop=seg_pop,
        cf_model=best_cf_model,
        interaction_csr=interaction_csr,
        customer_to_idx=customer_to_idx,
        item_to_idx=item_to_idx,
        purchases_history=history_purchases,
    )
    print("Saved validation bundle to artifacts/validation.")

    # 9. Real MLflow experiment logging
    try:
        tracking_uri = config.get("tracking", {}).get("mlflow_tracking_uri", "sqlite:///mlflow.db")
        mlflow.set_tracking_uri(tracking_uri)
        mlflow.set_experiment("RetailMind_Segmentation_Recommender")
        with mlflow.start_run(run_name="validation_candidate_comparison"):
            mlflow.log_params({
                "stage": "validation",
                "snapshot_cutoff": str(cutoff),
                "holdout_start": str(future_start),
                "holdout_end": str(future_end),
                "catalog_size": len(catalog_items),
                "active_customers": len(df_active),
                "selected_segment_family": selected_seg_info["selected_family"],
                "selected_recommender": selected_rec_algorithm,
                "transform_method": seg_cfg.get("transform_method", "yeo_johnson"),
                "weighting_method": rec_cfg.get("weighting_method", "binary"),
                "cf_qualifies": validation_report["cf_qualifies"],
            })
            mlflow.log_metrics({
                "val_silhouette": float(selected_seg_info["mean_silhouette"]),
                "val_median_ari": float(selected_seg_info["median_ari"]),
                "val_selected_rec_ndcg10": float(validation_report["models"][selected_rec_algorithm]["mean_ndcg"]),
                "val_selected_rec_recall10": float(validation_report["models"][selected_rec_algorithm]["mean_recall"]),
                "val_selected_rec_hitrate10": float(validation_report["models"][selected_rec_algorithm]["mean_hit_rate"]),
                "val_relative_ndcg_gain": float(validation_report["relative_ndcg_gain"]),
            })
            if (reports_dir / "cluster_comparison.csv").exists():
                mlflow.log_artifact(str(reports_dir / "cluster_comparison.csv"))
            if (reports_dir / "validation_metrics.json").exists():
                mlflow.log_artifact(str(reports_dir / "validation_metrics.json"))
            print("Logged validation run and metrics to MLflow.")
    except Exception as e:
        print(f"Warning: MLflow logging skipped/failed: {e}")

    return validation_report


def freeze_selection(config_path: str | Path) -> Dict[str, Any]:
    """Freeze validation model selection into an immutable reports/selection.json manifest."""
    val_report_path = Path("reports/validation_metrics.json")
    if not val_report_path.exists():
        raise FileNotFoundError("Validation metrics report not found. Run 'train --stage validation' first.")

    with open(val_report_path, "r", encoding="utf-8") as f:
        val_report = json.load(f)

    with open(config_path, "r", encoding="utf-8") as f:
        config_text = f.read()
        config = yaml.safe_load(config_text)

    config_sha256 = compute_string_sha256(config_text)
    lock_path = Path("requirements.lock")
    lock_sha256 = compute_file_sha256(lock_path) if lock_path.exists() else "UNLOCKED"
    source_sha256 = compute_file_sha256(config["dataset"]["raw_xlsx_path"])

    freeze_manifest = {
        "freeze_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "source_sha256": source_sha256,
        "config_sha256": config_sha256,
        "lock_sha256": lock_sha256,
        "validation_cutoff": val_report["snapshot_cutoff"],
        "selected_segmentation": val_report["selected_segmentation"],
        "selected_recommender": val_report["selected_recommender"],
        "cf_qualifies": val_report["cf_qualifies"],
        "relative_ndcg_gain": val_report["relative_ndcg_gain"],
        "validation_ndcg": val_report["models"][val_report["selected_recommender"]]["mean_ndcg"],
        "validation_recall": val_report["models"][val_report["selected_recommender"]]["mean_recall"],
        "bootstrap_diff_ci_95": val_report["bootstrap_ci_95"]["difference_ndcg"],
    }

    selection_path = Path("reports/selection.json")
    with open(selection_path, "w", encoding="utf-8") as f:
        json.dump(freeze_manifest, f, indent=2)

    print(f"Selection frozen successfully in {selection_path}:")
    print(f"  Segmentation: {freeze_manifest['selected_segmentation']['selected_family']}")
    print(f"  Recommender: {freeze_manifest['selected_recommender']}")
    return freeze_manifest


def run_test_pipeline(config_path: str | Path) -> Dict[str, Any]:
    """Execute final test refit and evaluation strictly following the frozen selection manifest."""
    selection_path = Path("reports/selection.json")
    if not selection_path.exists():
        raise RuntimeError("Selection manifest reports/selection.json is missing! Cannot run final test.")

    with open(selection_path, "r", encoding="utf-8") as f:
        freeze_manifest = json.load(f)

    with open(config_path, "r", encoding="utf-8") as f:
        config_text = f.read()
        config = yaml.safe_load(config_text)

    # Verify integrity hashes
    current_config_sha256 = compute_string_sha256(config_text)
    current_source_sha256 = compute_file_sha256(config["dataset"]["raw_xlsx_path"])
    if current_config_sha256 != freeze_manifest["config_sha256"]:
        raise ValueError("Config hash mismatch against frozen selection manifest!")
    if current_source_sha256 != freeze_manifest["source_sha256"]:
        raise ValueError("Source data hash mismatch against frozen selection manifest!")

    ds_cfg = config["dataset"]
    test_temp_cfg = config["temporal"]["test"]
    seg_cfg = config["segmentation"]
    rec_cfg = config["recommenders"]

    df_purchases = pd.read_parquet(ds_cfg["processed_parquet_path"])

    cutoff = pd.to_datetime(test_temp_cfg["cutoff"])
    future_start = pd.to_datetime(test_temp_cfg["future_start"])
    future_end = pd.to_datetime(test_temp_cfg["future_end"])

    print(f"=== Running Final Test Stage (Cutoff: {cutoff}) ===")

    # 1. Build test RFM snapshot
    df_profiles, rfm_meta = build_snapshot_rfm(df_purchases, cutoff=cutoff, rfm_window_days=180)
    df_active = df_profiles[df_profiles["status"] == "known_active"].copy()
    print(f"Test snapshot: {len(df_profiles):,} known ({len(df_active):,} active).")

    # 2. Refit frozen segmentation choice
    selected_seg_info = freeze_manifest["selected_segmentation"]
    segmenter, scaler, df_segment_summaries, seg_profiles_dict = fit_and_profile_selected_segmenter(
        df_active, selected_seg_info, seed=seg_cfg.get("primary_seed", 42)
    )

    # Assign segment IDs
    if selected_seg_info.get("is_rule_baseline", False):
        seg_ids, seg_labels = segmenter.predict(df_profiles)
        df_profiles["segment_id"] = seg_ids
        df_profiles["segment_label"] = seg_labels
    else:
        from retailmind.segmentation import extract_raw_rfm_matrix
        t_method = selected_seg_info.get("transform_method", "yeo_johnson")
        X_raw_active = extract_raw_rfm_matrix(df_active) if t_method != "log1p" else np.log1p(extract_raw_rfm_matrix(df_active))
        X_active = scaler.transform(X_raw_active)
        raw_preds = segmenter.predict(X_active)
        c_to_s = segmenter.cluster_to_seg_id_
        active_seg_ids = [c_to_s[c] for c in raw_preds]
        active_seg_labels = [seg_profiles_dict[s]["segment_label"] for s in active_seg_ids]

        df_profiles["segment_id"] = None
        df_profiles["segment_label"] = None

        active_indices = df_profiles[df_profiles["status"] == "known_active"].index
        df_profiles.loc[active_indices, "segment_id"] = active_seg_ids
        df_profiles.loc[active_indices, "segment_label"] = active_seg_labels

        inactive_indices = df_profiles[df_profiles["status"] == "known_inactive"].index
        df_profiles.loc[inactive_indices, "segment_id"] = "SG_INACTIVE"
        df_profiles.loc[inactive_indices, "segment_label"] = "Inactive (Outside 180-Day Window)"

    cust_seg_map = dict(zip(df_profiles["customer_id"], df_profiles["segment_id"]))

    # 3. Build test catalog and sparse interactions
    history_purchases = df_purchases[df_purchases["InvoiceDate"] < cutoff].copy()
    (
        catalog_items,
        item_descriptions,
        user_items,
        interaction_csr,
        customer_to_idx,
        item_to_idx,
    ) = build_catalog_and_interactions(
        df_purchases,
        cutoff=cutoff,
        min_distinct_buyers=config["catalog"].get("min_distinct_buyers", 5),
        active_window_days=config["catalog"].get("active_window_days", 90),
    )
    print(f"Test catalog size: {len(catalog_items):,} items.")

    # 4. Refit recommenders
    global_pop = GlobalPopularityRecommender().fit(history_purchases, catalog_items, cutoff=cutoff)
    seg_pop = SegmentPopularityRecommender().fit(history_purchases, cust_seg_map, catalog_items, cutoff=cutoff)

    selected_rec_name = freeze_manifest["selected_recommender"]
    cf_model = None
    if "ItemItemCF" in selected_rec_name:
        n_neighbors = int(selected_rec_name.split("_N")[1])
        cf_model = ItemItemCollaborativeFiltering(
            top_n_neighbors=n_neighbors,
            min_co_buyers=rec_cfg.get("cf_min_co_buyers", 2),
            block_size=rec_cfg.get("cf_block_size", 256),
        )
        cf_model.fit(interaction_csr, catalog_items, customer_to_idx, item_to_idx, history_purchases)

    # 5. Extract test holdout cohorts
    cohort_data = extract_evaluation_cohorts(
        df_purchases,
        cutoff=cutoff,
        future_start=future_start,
        future_end=future_end,
        catalog_items=catalog_items,
    )

    primary_users = cohort_data["primary_cohort_users"]
    primary_gt = cohort_data["primary_ground_truth"]
    cold_start_users = cohort_data["cold_start_users"]
    cold_start_gt = cohort_data["cold_start_ground_truth"]
    new_prod_users = cohort_data["new_product_users"]
    new_prod_gt = cohort_data["new_product_ground_truth"]

    print(f"Test primary cohort: {len(primary_users):,} returners.")
    print(f"Test cold-start cohort: {len(cold_start_users):,} new customers.")
    print(f"Test new-product cohort: {len(new_prod_users):,} returners exploring new items.")

    top_k = rec_cfg.get("top_k", 10)
    test_results: Dict[str, Any] = {}

    # Extract customer history lookup for new_items_only evaluation mode
    grouped_hist = history_purchases.groupby("CustomerID")["StockCode"].unique()
    cust_history_dict = {str(k): set(v) for k, v in grouped_hist.items()}

    # Evaluate baselines
    test_global = evaluate_model_on_cohort(
        global_pop,
        primary_users,
        primary_gt,
        catalog_items,
        cust_seg_map,
        seg_pop,
        global_pop,
        customer_history=cust_history_dict,
        mode="repeat_allowed",
        k=top_k,
        model_name="GlobalPopularity",
    )
    test_results["GlobalPopularity"] = test_global

    test_seg = evaluate_model_on_cohort(
        seg_pop,
        primary_users,
        primary_gt,
        catalog_items,
        cust_seg_map,
        seg_pop,
        global_pop,
        customer_history=cust_history_dict,
        mode="repeat_allowed",
        k=top_k,
        model_name="SegmentPopularity",
    )
    test_results["SegmentPopularity"] = test_seg

    # Cold-start evaluation (Global popularity on new customers)
    test_cold_start = evaluate_model_on_cohort(
        global_pop,
        cold_start_users,
        cold_start_gt,
        catalog_items,
        cust_seg_map,
        seg_pop,
        global_pop,
        customer_history=cust_history_dict,
        mode="repeat_allowed",
        k=top_k,
        model_name="ColdStart_GlobalPop",
    )
    test_results["ColdStart_GlobalPop"] = test_cold_start

    # New-product mode baselines
    test_global_new_prod = evaluate_model_on_cohort(
        global_pop,
        new_prod_users,
        new_prod_gt,
        catalog_items,
        cust_seg_map,
        seg_pop,
        global_pop,
        customer_history=cust_history_dict,
        mode="new_items_only",
        k=top_k,
        model_name="GlobalPopularity_NewItemsOnly",
    )
    test_results["GlobalPopularity_NewItemsOnly"] = test_global_new_prod

    test_seg_new_prod = evaluate_model_on_cohort(
        seg_pop,
        new_prod_users,
        new_prod_gt,
        catalog_items,
        cust_seg_map,
        seg_pop,
        global_pop,
        customer_history=cust_history_dict,
        mode="new_items_only",
        k=top_k,
        model_name="SegmentPopularity_NewItemsOnly",
    )
    test_results["SegmentPopularity_NewItemsOnly"] = test_seg_new_prod

    # Evaluate CF
    if cf_model is not None:
        test_cf = evaluate_model_on_cohort(
            cf_model,
            primary_users,
            primary_gt,
            catalog_items,
            cust_seg_map,
            seg_pop,
            global_pop,
            customer_history=cust_history_dict,
            mode="repeat_allowed",
            k=top_k,
            model_name=selected_rec_name,
        )
        test_results[selected_rec_name] = test_cf

        # New-product mode evaluation for CF
        test_new_prod = evaluate_model_on_cohort(
            cf_model,
            new_prod_users,
            new_prod_gt,
            catalog_items,
            cust_seg_map,
            seg_pop,
            global_pop,
            customer_history=cust_history_dict,
            mode="new_items_only",
            k=top_k,
            model_name=f"{selected_rec_name}_NewItemsOnly",
        )
        test_results[f"{selected_rec_name}_NewItemsOnly"] = test_new_prod

        # Bootstrap CI on test vs frozen baseline
        cf_ndcg = np.array([m["ndcg_at_k"] for m in test_cf["per_user_metrics"]])
        frozen_base_name = freeze_manifest.get("strongest_baseline", "SegmentPopularity")
        base_eval = test_seg if "Segment" in frozen_base_name else test_global
        base_ndcg = np.array([m["ndcg_at_k"] for m in base_eval["per_user_metrics"]])
        ci_cf, ci_base, ci_diff = paired_bootstrap_ci(cf_ndcg, base_ndcg, n_bootstraps=1000, seed=42)
    else:
        frozen_base_name = "GlobalPopularity"
        ci_cf = (0.0, 0.0)
        ci_base = (0.0, 0.0)
        ci_diff = (0.0, 0.0)

    # Clean per-user metrics for json
    summary_test_results = {}
    for m_name, m_eval in test_results.items():
        summary_test_results[m_name] = {k: v for k, v in m_eval.items() if k != "per_user_metrics"}

    test_report = {
        "stage": "test",
        "snapshot_cutoff": str(cutoff),
        "holdout_start": str(future_start),
        "holdout_end": str(future_end),
        "catalog_size": len(catalog_items),
        "primary_cohort_size": len(primary_users),
        "cold_start_cohort_size": len(cold_start_users),
        "new_product_cohort_size": len(new_prod_users),
        "future_item_coverage": round(cohort_data["future_item_coverage"], 4),
        "models": summary_test_results,
        "selected_recommender": selected_rec_name,
        "frozen_baseline": frozen_base_name,
        "bootstrap_ci_95": {
            "cf_ndcg": [round(ci_cf[0], 4), round(ci_cf[1], 4)],
            "baseline_ndcg": [round(ci_base[0], 4), round(ci_base[1], 4)],
            "difference_ndcg": [round(ci_diff[0], 4), round(ci_diff[1], 4)],
        },
        "selected_segmentation": selected_seg_info,
    }

    with open("reports/test_metrics.json", "w", encoding="utf-8") as f:
        json.dump(test_report, f, indent=2)

    # 6. Save test and release bundles
    selection_sha256 = compute_file_sha256("reports/selection.json")
    manifest_test = BundleManifest(
        bundle_version="0.1.0-release",
        stage="test",
        snapshot_cutoff=str(cutoff),
        created_at=datetime.now(timezone.utc).isoformat(),
        source_sha256=current_source_sha256,
        config_sha256=current_config_sha256,
        lock_sha256=freeze_manifest["lock_sha256"],
        selection_manifest_sha256=selection_sha256,
        segment_algorithm=selected_seg_info["selected_family"],
        segment_params=selected_seg_info,
        recommender_algorithm=selected_rec_name,
        recommender_params=freeze_manifest.get("recommender_params", {}),
        catalog_size=len(catalog_items),
        active_customers_count=len(df_active),
        known_customers_count=len(df_profiles),
        reports={
            "test_metrics": "reports/test_metrics.json",
            "selection": "reports/selection.json",
            "validation_metrics": "reports/validation_metrics.json",
        },
    )

    save_bundle(
        bundle_dir="artifacts/test",
        manifest=manifest_test,
        segmenter=segmenter,
        scaler=scaler,
        df_profiles=df_profiles,
        df_segment_summaries=df_segment_summaries,
        catalog_items=catalog_items,
        item_descriptions=item_descriptions,
        global_pop=global_pop,
        seg_pop=seg_pop,
        cf_model=cf_model,
        interaction_csr=interaction_csr,
        customer_to_idx=customer_to_idx,
        item_to_idx=item_to_idx,
        purchases_history=history_purchases,
    )

    # Copy to artifacts/release
    save_bundle(
        bundle_dir="artifacts/release",
        manifest=manifest_test,
        segmenter=segmenter,
        scaler=scaler,
        df_profiles=df_profiles,
        df_segment_summaries=df_segment_summaries,
        catalog_items=catalog_items,
        item_descriptions=item_descriptions,
        global_pop=global_pop,
        seg_pop=seg_pop,
        cf_model=cf_model,
        interaction_csr=interaction_csr,
        customer_to_idx=customer_to_idx,
        item_to_idx=item_to_idx,
        purchases_history=history_purchases,
    )
    print("Saved test and release bundles to artifacts/test and artifacts/release.")

    # Real MLflow experiment logging for test stage
    try:
        tracking_uri = config.get("tracking", {}).get("mlflow_tracking_uri", "sqlite:///mlflow.db")
        mlflow.set_tracking_uri(tracking_uri)
        mlflow.set_experiment("RetailMind_Segmentation_Recommender")
        with mlflow.start_run(run_name="frozen_test_holdout_evaluation"):
            mlflow.log_params({
                "stage": "test",
                "snapshot_cutoff": str(cutoff),
                "holdout_start": str(future_start),
                "holdout_end": str(future_end),
                "catalog_size": len(catalog_items),
                "selected_segment_family": selected_seg_info["selected_family"],
                "selected_recommender": selected_rec_name,
                "cf_neighbors": rec_cfg.get("cf_neighbors", 50),
                "transform_method": seg_cfg.get("transform_method", "yeo_johnson"),
                "weighting_method": rec_cfg.get("weighting_method", "binary"),
            })
            mlflow.log_metrics({
                "test_silhouette": float(selected_seg_info["mean_silhouette"]),
                "test_median_ari": float(selected_seg_info["median_ari"]),
                "test_cf_ndcg10": float(test_report["models"][selected_rec_name]["mean_ndcg"]),
                "test_cf_recall10": float(test_report["models"][selected_rec_name]["mean_recall"]),
                "test_cf_hitrate10": float(test_report["models"][selected_rec_name]["mean_hit_rate"]),
                "test_cf_catalog_coverage": float(test_report["models"][selected_rec_name]["catalog_coverage"]),
                "test_segpop_ndcg10": float(test_report["models"]["SegmentPopularity"]["mean_ndcg"]),
                "test_globalpop_ndcg10": float(test_report["models"]["GlobalPopularity"]["mean_ndcg"]),
                "test_coldstart_ndcg10": float(test_report["models"]["ColdStart_GlobalPop"]["mean_ndcg"]),
                "test_newitems_cf_ndcg10": float(test_report["models"]["ItemItemCF_N50_NewItemsOnly"]["mean_ndcg"]),
                "bootstrap_diff_ci_lower": float(test_report["bootstrap_ci_95"]["difference_ndcg"][0]),
                "bootstrap_diff_ci_upper": float(test_report["bootstrap_ci_95"]["difference_ndcg"][1]),
            })
            for rep in ["reports/test_metrics.json", "reports/selection.json", "reports/segment_profiles.csv", "reports/latency.json"]:
                if Path(rep).exists():
                    mlflow.log_artifact(rep)
            print("Logged test evaluation run and metrics to MLflow.")
    except Exception as e:
        print(f"Warning: MLflow test logging skipped/failed: {e}")

    return test_report
