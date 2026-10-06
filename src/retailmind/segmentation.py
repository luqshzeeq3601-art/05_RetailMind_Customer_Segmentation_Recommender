"""Customer segmentation algorithms: RFM rule baseline, K-Means, GMM, and segment profiling."""

from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import adjusted_rand_score, davies_bouldin_score, silhouette_score
from sklearn.mixture import GaussianMixture
from sklearn.preprocessing import PowerTransformer, QuantileTransformer, StandardScaler


class RFMRulesSegmenter:
    """Rule-based RFM baseline segmenter using training quantiles."""

    def __init__(self) -> None:
        self.r_cutpoints: np.ndarray = np.array([])
        self.f_cutpoints: np.ndarray = np.array([])
        self.m_cutpoints: np.ndarray = np.array([])
        self.is_fitted: bool = False

    def fit(self, df_active: pd.DataFrame) -> "RFMRulesSegmenter":
        """Learn 25th, 50th, 75th percentiles from active training customers."""
        self.r_cutpoints = np.percentile(df_active["recency_days"], [25, 50, 75])
        self.f_cutpoints = np.percentile(df_active["frequency_invoices"], [25, 50, 75])
        self.m_cutpoints = np.percentile(df_active["monetary_gbp"], [25, 50, 75])
        self.is_fitted = True
        return self

    def _score_feature(self, values: np.ndarray, cutpoints: np.ndarray) -> np.ndarray:
        # searchsorted with side='right' -> 0, 1, 2, 3 -> bins 1, 2, 3, 4
        return 1 + np.searchsorted(cutpoints, values, side="right")

    def predict(self, df_profiles: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        """Predict segment IDs and labels for customer profiles.

        Returns:
            (segment_ids, segment_labels)
        """
        if not self.is_fitted:
            raise RuntimeError("RFMRulesSegmenter must be fitted before predict.")

        n = len(df_profiles)
        seg_ids = np.empty(n, dtype=object)
        seg_labels = np.empty(n, dtype=object)

        r_raw = df_profiles["recency_days"].to_numpy()
        f_raw = df_profiles["frequency_invoices"].to_numpy()
        m_raw = df_profiles["monetary_gbp"].to_numpy()
        statuses = df_profiles["status"].to_numpy()

        r_bins = self._score_feature(r_raw, self.r_cutpoints)
        r_scores = 5 - r_bins  # higher score = more recent
        f_scores = self._score_feature(f_raw, self.f_cutpoints)
        m_scores = self._score_feature(m_raw, self.m_cutpoints)

        for i in range(n):
            if statuses[i] == "known_inactive":
                seg_ids[i] = "SG_INACTIVE"
                seg_labels[i] = "Inactive (Outside 180-Day Window)"
                continue

            r = r_scores[i]
            f = f_scores[i]
            m = m_scores[i]

            if r >= 3 and f >= 3 and m >= 3:
                seg_ids[i] = "SG01"
                seg_labels[i] = "Recent Frequent High Spend"
            elif r <= 2 and m >= 3:
                seg_ids[i] = "SG02"
                seg_labels[i] = "Less Recent High Spend"
            elif r >= 3 and f <= 2:
                seg_ids[i] = "SG03"
                seg_labels[i] = "Recent Occasional"
            else:
                seg_ids[i] = "SG04"
                seg_labels[i] = "Other Active"

        return seg_ids, seg_labels


def extract_raw_rfm_matrix(df_active: pd.DataFrame) -> np.ndarray:
    """Extract raw non-negative (R, F, M) feature matrix."""
    r = np.maximum(0.0, df_active["recency_days"].to_numpy(dtype=np.float64))
    f = np.maximum(0.0, df_active["frequency_invoices"].to_numpy(dtype=np.float64))
    m = np.maximum(0.0, df_active["monetary_gbp"].to_numpy(dtype=np.float64))
    return np.column_stack([r, f, m])


def create_rfm_transformer(transform_method: str = "yeo_johnson") -> Any:
    """Instantiate the fitted feature transformer for RFM clustering."""
    if transform_method == "yeo_johnson":
        return PowerTransformer(method="yeo-johnson", standardize=True)
    elif transform_method == "quantile":
        return QuantileTransformer(output_distribution="normal", n_quantiles=1000, random_state=42)
    elif transform_method == "log1p":
        return StandardScaler()
    else:
        raise ValueError(f"Unknown transform_method: {transform_method}")


def prepare_rfm_matrix(df_active: pd.DataFrame, transform_method: str = "log1p") -> np.ndarray:
    """Extract and transform (R, F, M) for clustering."""
    raw_rfm = extract_raw_rfm_matrix(df_active)
    if transform_method == "log1p":
        return np.log1p(raw_rfm)
    return raw_rfm


def generate_cluster_label_and_hypothesis(
    med_r: float, med_f: float, med_m: float
) -> Tuple[str, str]:
    """Generate human-understandable segment label and campaign hypothesis from median RFM."""
    if med_m >= 1500 and med_f >= 4 and med_r <= 30:
        label = "High-Value Frequent VIPs"
        hypothesis = "Loyalty perks, early product access, and premium bundles to maximize retention."
    elif med_m >= 1000 and med_r > 50:
        label = "Lapsed High Spenders"
        hypothesis = "Re-engagement win-back campaigns with personalized high-tier product discounts."
    elif med_f >= 3 and med_r <= 40:
        label = "Steady Active Buyers"
        hypothesis = "Category cross-sell recommendations and volume discounts to boost basket size."
    elif med_r <= 30 and med_f <= 2:
        label = "Recent New / Occasional Buyers"
        hypothesis = "Nurture sequence and introductory category recommendations to foster repeat purchase."
    elif med_r > 60:
        label = "Dormant / Low Engagement"
        hypothesis = "Low-cost seasonal email reminders and highlight of top global bestsellers."
    else:
        label = "Standard Active Shoppers"
        hypothesis = "Targeted segment-popular product promotions and seasonal campaigns."
    return label, hypothesis


def evaluate_clustering_candidates(
    df_active: pd.DataFrame,
    seeds: List[int],
    kmeans_k_candidates: List[int],
    gmm_components_candidates: List[int],
    gmm_covariance_types: List[str],
    transform_method: str = "yeo_johnson",
    min_cluster_share: float = 0.03,
    min_median_ari: float = 0.80,
    min_mean_silhouette: float = 0.30,
    sample_size: int = 2000,
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """Compare K-Means and GMM across multiple seeds, evaluate eligibility, and select best model."""
    transformer = create_rfm_transformer(transform_method)
    X_raw = extract_raw_rfm_matrix(df_active) if transform_method != "log1p" else np.log1p(extract_raw_rfm_matrix(df_active))
    X_scaled = transformer.fit_transform(X_raw)

    n_samples = len(df_active)
    if n_samples <= sample_size:
        eval_indices = np.arange(n_samples)
    else:
        rng = np.random.RandomState(42)
        eval_indices = rng.choice(n_samples, size=sample_size, replace=False)

    X_eval = X_scaled[eval_indices]

    results: List[Dict[str, Any]] = []

    # 1. Evaluate RFM Rules baseline
    rfm_baseline = RFMRulesSegmenter()
    rfm_baseline.fit(df_active)
    seg_ids_rfm, _ = rfm_baseline.predict(df_active)

    unique_segs = sorted(list(set(seg_ids_rfm)))
    seg_to_int = {s: idx for idx, s in enumerate(unique_segs)}
    rfm_labels = np.array([seg_to_int[s] for s in seg_ids_rfm])

    eval_labels_rfm = rfm_labels[eval_indices]
    if len(np.unique(eval_labels_rfm)) == len(unique_segs):
        rfm_sil = float(silhouette_score(X_eval, eval_labels_rfm))
    else:
        rfm_sil = float(silhouette_score(X_scaled, rfm_labels))
    rfm_db = float(davies_bouldin_score(X_scaled, rfm_labels))

    counts_rfm = np.bincount(rfm_labels, minlength=len(unique_segs))
    shares_rfm = counts_rfm / n_samples
    min_share_rfm = float(np.min(shares_rfm))

    results.append(
        {
            "model_family": "RFMRules",
            "k_components": len(unique_segs),
            "covariance_type": "none",
            "mean_silhouette": round(rfm_sil, 4),
            "median_ari": 1.0,
            "davies_bouldin": round(rfm_db, 4),
            "min_cluster_share": round(min_share_rfm, 4),
            "is_eligible": False,  # Rule baseline is operational fallback, not eligible learned model
            "fits": [rfm_labels],
        }
    )

    # 2. Evaluate K-Means candidates
    for k in kmeans_k_candidates:
        fits = []
        silhouettes = []
        db_scores = []
        min_shares = []

        for seed in seeds:
            km = KMeans(n_clusters=k, n_init=20, random_state=seed)
            labels = km.fit_predict(X_scaled)
            fits.append(labels)

            counts = np.bincount(labels, minlength=k)
            shares = counts / n_samples
            min_shares.append(float(np.min(shares)))

            eval_labels = labels[eval_indices]
            # Check every cluster has at least 1 sample in eval
            if len(np.unique(eval_labels)) == k:
                sil = float(silhouette_score(X_eval, eval_labels))
            else:
                sil = float(silhouette_score(X_scaled, labels))
            silhouettes.append(sil)
            db_scores.append(float(davies_bouldin_score(X_scaled, labels)))

        # Pairwise ARI across all pairs of seeds
        ari_list = []
        for i in range(len(seeds)):
            for j in range(i + 1, len(seeds)):
                ari_list.append(float(adjusted_rand_score(fits[i], fits[j])))

        med_ari = float(np.median(ari_list))
        mean_sil = float(np.mean(silhouettes))
        mean_db = float(np.mean(db_scores))
        overall_min_share = float(np.min(min_shares))

        is_eligible = (
            (overall_min_share >= min_cluster_share)
            and (med_ari >= min_median_ari)
            and (mean_sil >= min_mean_silhouette)
        )

        results.append(
            {
                "model_family": "KMeans",
                "k_components": k,
                "covariance_type": "none",
                "mean_silhouette": round(mean_sil, 4),
                "median_ari": round(med_ari, 4),
                "davies_bouldin": round(mean_db, 4),
                "min_cluster_share": round(overall_min_share, 4),
                "is_eligible": is_eligible,
                "fits": fits,
            }
        )

    # 3. Evaluate GMM candidates
    for k in gmm_components_candidates:
        for cov in gmm_covariance_types:
            fits = []
            silhouettes = []
            db_scores = []
            min_shares = []
            bics = []

            for seed in seeds:
                gmm = GaussianMixture(
                    n_components=k,
                    covariance_type=cov,
                    n_init=5,
                    reg_covar=1e-6,
                    random_state=seed,
                )
                gmm.fit(X_scaled)
                labels = gmm.predict(X_scaled)
                fits.append(labels)
                bics.append(float(gmm.bic(X_scaled)))

                counts = np.bincount(labels, minlength=k)
                shares = counts / n_samples
                min_shares.append(float(np.min(shares)))

                eval_labels = labels[eval_indices]
                if len(np.unique(eval_labels)) == k:
                    sil = float(silhouette_score(X_eval, eval_labels))
                else:
                    sil = float(silhouette_score(X_scaled, labels))
                silhouettes.append(sil)
                db_scores.append(float(davies_bouldin_score(X_scaled, labels)))

            ari_list = []
            for i in range(len(seeds)):
                for j in range(i + 1, len(seeds)):
                    ari_list.append(float(adjusted_rand_score(fits[i], fits[j])))

            med_ari = float(np.median(ari_list))
            mean_sil = float(np.mean(silhouettes))
            mean_db = float(np.mean(db_scores))
            overall_min_share = float(np.min(min_shares))

            is_eligible = (
                (overall_min_share >= min_cluster_share)
                and (med_ari >= min_median_ari)
                and (mean_sil >= min_mean_silhouette)
            )

            results.append(
                {
                    "model_family": "GMM",
                    "k_components": k,
                    "covariance_type": cov,
                    "mean_silhouette": round(mean_sil, 4),
                    "median_ari": round(med_ari, 4),
                    "davies_bouldin": round(mean_db, 4),
                    "bic": round(float(np.mean(bics)), 1),
                    "min_cluster_share": round(overall_min_share, 4),
                    "is_eligible": is_eligible,
                    "fits": fits,
                }
            )

    df_results = pd.DataFrame(results)

    # Selection logic:
    # Filter eligible learned models
    eligible_df = df_results[
        (df_results["is_eligible"]) & (df_results["model_family"] != "RFMRules")
    ].copy()

    if not eligible_df.empty:
        # Maximum silhouette among eligible candidates
        max_sil = float(eligible_df["mean_silhouette"].max())
        # Candidates within 0.01 of the best silhouette
        tier_df = eligible_df[eligible_df["mean_silhouette"] >= (max_sil - 0.01 - 1e-6)].copy()

        # Preference hierarchy within the 0.01 tolerance band:
        # 1. Higher median ARI descending
        # 2. Fewer clusters (k_components ascending)
        # 3. Model family preference (KMeans before GMM)
        # 4. Mean silhouette descending
        family_map = {"KMeans": 0, "GMM": 1}
        tier_df["family_pref"] = tier_df["model_family"].map(family_map).fillna(2)
        tier_df = tier_df.sort_values(
            by=["median_ari", "k_components", "family_pref", "mean_silhouette"],
            ascending=[False, True, True, False],
        )

        best_row = tier_df.iloc[0]
        selected_model_info = {
            "selected_family": best_row["model_family"],
            "k_components": int(best_row["k_components"]),
            "covariance_type": best_row["covariance_type"],
            "transform_method": transform_method,
            "mean_silhouette": float(best_row["mean_silhouette"]),
            "median_ari": float(best_row["median_ari"]),
            "is_rule_baseline": False,
        }
    else:
        selected_model_info = {
            "selected_family": "RFMRules",
            "k_components": 4,
            "covariance_type": "none",
            "transform_method": "none",
            "mean_silhouette": None,
            "median_ari": None,
            "is_rule_baseline": True,
            "fallback_reason": "No learned clustering setting passed all eligibility criteria",
        }

    return df_results.drop(columns=["fits"]), selected_model_info


def fit_and_profile_selected_segmenter(
    df_active: pd.DataFrame,
    selected_info: Dict[str, Any],
    seed: int = 42,
) -> Tuple[Any, Any, pd.DataFrame, Dict[str, Dict[str, Any]]]:
    """Fit the chosen segmentation model on active customers, create segment mapping and profiles.

    Ordering rule for segment IDs (SG01, SG02, ...):
    Median monetary descending -> frequency descending -> recency ascending -> raw cluster index.
    """
    if selected_info.get("is_rule_baseline", False):
        segmenter = RFMRulesSegmenter()
        segmenter.fit(df_active)
        seg_ids, seg_labels = segmenter.predict(df_active)
        df_active_with_seg = df_active.copy()
        df_active_with_seg["segment_id"] = seg_ids
        df_active_with_seg["segment_label"] = seg_labels

        # Profile table
        profiles_list = []
        seg_profiles_dict = {}
        for seg_id in sorted(df_active_with_seg["segment_id"].unique()):
            sub = df_active_with_seg[df_active_with_seg["segment_id"] == seg_id]
            med_r = float(sub["recency_days"].median())
            med_f = float(sub["frequency_invoices"].median())
            med_m = float(sub["monetary_gbp"].median())
            label = sub["segment_label"].iloc[0]
            _, hypothesis = generate_cluster_label_and_hypothesis(med_r, med_f, med_m)

            seg_info = {
                "segment_id": seg_id,
                "segment_label": label,
                "customer_count": int(len(sub)),
                "customer_share": round(len(sub) / len(df_active), 4),
                "median_recency": round(med_r, 1),
                "median_frequency": round(med_f, 1),
                "median_monetary": round(med_m, 2),
                "campaign_hypothesis": hypothesis,
            }
            profiles_list.append(seg_info)
            seg_profiles_dict[seg_id] = seg_info

        return segmenter, None, pd.DataFrame(profiles_list), seg_profiles_dict

    # Learned model fit
    t_method = selected_info.get("transform_method", "yeo_johnson")
    transformer = create_rfm_transformer(t_method)
    X_raw = extract_raw_rfm_matrix(df_active) if t_method != "log1p" else np.log1p(extract_raw_rfm_matrix(df_active))
    X_scaled = transformer.fit_transform(X_raw)

    family = selected_info["selected_family"]
    k = selected_info["k_components"]

    if family == "KMeans":
        estimator = KMeans(n_clusters=k, n_init=20, random_state=seed)
        estimator.fit(X_scaled)
        raw_labels = estimator.predict(X_scaled)
    elif family == "GMM":
        cov = selected_info["covariance_type"]
        estimator = GaussianMixture(
            n_components=k,
            covariance_type=cov,
            n_init=5,
            reg_covar=1e-6,
            random_state=seed,
        )
        estimator.fit(X_scaled)
        raw_labels = estimator.predict(X_scaled)
    else:
        raise ValueError(f"Unknown family: {family}")

    # Compute raw cluster medians to sort deterministically
    df_temp = df_active.copy()
    df_temp["raw_cluster"] = raw_labels

    cluster_stats = []
    for c in range(k):
        sub = df_temp[df_temp["raw_cluster"] == c]
        cluster_stats.append(
            {
                "raw_cluster": c,
                "median_monetary": float(sub["monetary_gbp"].median()),
                "median_frequency": float(sub["frequency_invoices"].median()),
                "median_recency": float(sub["recency_days"].median()),
                "count": len(sub),
            }
        )

    # Sort cluster order: median_monetary desc, median_frequency desc, median_recency asc, raw_cluster asc
    df_stats = pd.DataFrame(cluster_stats).sort_values(
        by=["median_monetary", "median_frequency", "median_recency", "raw_cluster"],
        ascending=[False, False, True, True],
    ).reset_index(drop=True)

    cluster_to_seg_id = {
        row["raw_cluster"]: f"SG{idx+1:02d}" for idx, row in df_stats.iterrows()
    }

    profiles_list = []
    seg_profiles_dict = {}

    for idx, row in df_stats.iterrows():
        raw_c = int(row["raw_cluster"])
        seg_id = cluster_to_seg_id[raw_c]
        sub = df_temp[df_temp["raw_cluster"] == raw_c]
        med_r = float(sub["recency_days"].median())
        med_f = float(sub["frequency_invoices"].median())
        med_m = float(sub["monetary_gbp"].median())
        label, hypothesis = generate_cluster_label_and_hypothesis(med_r, med_f, med_m)

        seg_info = {
            "segment_id": seg_id,
            "raw_cluster": raw_c,
            "segment_label": label,
            "customer_count": int(len(sub)),
            "customer_share": round(len(sub) / len(df_active), 4),
            "median_recency": round(med_r, 1),
            "median_frequency": round(med_f, 1),
            "median_monetary": round(med_m, 2),
            "campaign_hypothesis": hypothesis,
        }
        profiles_list.append(seg_info)
        seg_profiles_dict[seg_id] = seg_info

    # Add mapping to estimator object
    estimator.cluster_to_seg_id_ = cluster_to_seg_id
    estimator.seg_profiles_dict_ = seg_profiles_dict

    return estimator, transformer, pd.DataFrame(profiles_list), seg_profiles_dict
