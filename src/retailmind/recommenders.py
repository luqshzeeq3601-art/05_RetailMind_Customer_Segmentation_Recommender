"""Recommendation algorithms: Global popularity, Segment popularity, and Sparse Item-Item CF."""

from typing import Dict, List, Optional, Set, Tuple

import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix, diags
from sklearn.metrics.pairwise import cosine_similarity

from retailmind.contracts import RecommendedItem


class GlobalPopularityRecommender:
    """Ranks catalog items by distinct purchasing customers in the 90-day activity window."""

    def __init__(self) -> None:
        self.ranked_items: List[Tuple[str, float]] = []
        self.item_scores: Dict[str, float] = {}

    def fit(
        self,
        df_purchases_history: pd.DataFrame,
        catalog_items: List[str],
        cutoff: pd.Timestamp,
        active_window_days: int = 90,
    ) -> "GlobalPopularityRecommender":
        window_start = cutoff - pd.Timedelta(days=active_window_days)
        recent = df_purchases_history[df_purchases_history["InvoiceDate"] >= window_start]
        recent_catalog = recent[recent["StockCode"].isin(catalog_items)]

        counts = recent_catalog.groupby("StockCode")["CustomerID"].nunique().to_dict()

        # Build list with counts (0 for catalog items with no 90d purchase)
        items_with_score = []
        for sc in catalog_items:
            cnt = float(counts.get(sc, 0))
            items_with_score.append((sc, cnt))

        # Sort: score descending, then StockCode ascending
        items_with_score.sort(key=lambda x: (-x[1], x[0]))
        self.ranked_items = items_with_score
        self.item_scores = dict(items_with_score)
        return self

    def recommend(
        self,
        k: int,
        exclude_items: Optional[Set[str]] = None,
        item_descriptions: Optional[Dict[str, str]] = None,
    ) -> List[RecommendedItem]:
        exclude = exclude_items or set()
        descriptions = item_descriptions or {}
        results: List[RecommendedItem] = []
        rank = 1

        for sc, score in self.ranked_items:
            if sc in exclude:
                continue
            desc = descriptions.get(sc, sc)
            results.append(
                RecommendedItem(
                    rank=rank,
                    stock_code=sc,
                    description=desc,
                    score=float(score),
                    method="global_popularity",
                    reason_code="popular_overall",
                    reason_text="One of the most popular products among all shoppers",
                    supporting_stock_codes=[],
                    is_fallback=True,
                )
            )
            rank += 1
            if len(results) >= k:
                break

        return results


class SegmentPopularityRecommender:
    """Ranks catalog items by distinct purchasing customers within a specific customer segment."""

    def __init__(self) -> None:
        self.segment_rankings: Dict[str, List[Tuple[str, float]]] = {}
        self.segment_scores: Dict[str, Dict[str, float]] = {}

    def fit(
        self,
        df_purchases_history: pd.DataFrame,
        customer_segments: Dict[str, str],
        catalog_items: List[str],
        cutoff: pd.Timestamp,
        active_window_days: int = 90,
    ) -> "SegmentPopularityRecommender":
        window_start = cutoff - pd.Timedelta(days=active_window_days)
        recent = df_purchases_history[df_purchases_history["InvoiceDate"] >= window_start].copy()
        recent_catalog = recent[recent["StockCode"].isin(catalog_items)].copy()

        # Map customers to segment
        recent_catalog["segment_id"] = recent_catalog["CustomerID"].map(customer_segments)
        valid_seg = recent_catalog[recent_catalog["segment_id"].notna()]

        unique_segments = set(customer_segments.values())
        for seg_id in unique_segments:
            seg_data = valid_seg[valid_seg["segment_id"] == seg_id]
            counts = seg_data.groupby("StockCode")["CustomerID"].nunique().to_dict()

            items_with_score = []
            for sc in catalog_items:
                cnt = float(counts.get(sc, 0))
                items_with_score.append((sc, cnt))

            # Sort: score desc, StockCode asc
            items_with_score.sort(key=lambda x: (-x[1], x[0]))
            self.segment_rankings[seg_id] = items_with_score
            self.segment_scores[seg_id] = dict(items_with_score)

        return self

    def recommend(
        self,
        segment_id: Optional[str],
        k: int,
        global_pop: GlobalPopularityRecommender,
        exclude_items: Optional[Set[str]] = None,
        item_descriptions: Optional[Dict[str, str]] = None,
    ) -> List[RecommendedItem]:
        exclude = exclude_items or set()
        descriptions = item_descriptions or {}
        results: List[RecommendedItem] = []
        rank = 1
        seen_items = set()

        if segment_id and segment_id in self.segment_rankings:
            for sc, score in self.segment_rankings[segment_id]:
                if sc in exclude:
                    continue
                if score <= 0:
                    break
                desc = descriptions.get(sc, sc)
                results.append(
                    RecommendedItem(
                        rank=rank,
                        stock_code=sc,
                        description=desc,
                        score=float(score),
                        method="segment_popularity",
                        reason_code="popular_in_segment",
                        reason_text=f"Popular among shoppers in your segment ({segment_id})",
                        supporting_stock_codes=[],
                        is_fallback=True,
                    )
                )
                seen_items.add(sc)
                rank += 1
                if len(results) >= k:
                    return results

        # Fill remaining positions with global popularity
        remaining_needed = k - len(results)
        if remaining_needed > 0:
            combined_exclude = exclude.union(seen_items)
            global_fill = global_pop.recommend(
                k=remaining_needed,
                exclude_items=combined_exclude,
                item_descriptions=descriptions,
            )
            for item in global_fill:
                item.rank = rank
                results.append(item)
                rank += 1

        return results


class ItemItemCollaborativeFiltering:
    """Sparse item-item collaborative filtering with bounded neighbors and cosine similarity."""

    def __init__(
        self,
        top_n_neighbors: int = 50,
        min_co_buyers: int = 2,
        block_size: int = 256,
        weighting_method: str = "binary",
    ) -> None:
        self.top_n_neighbors = top_n_neighbors
        self.min_co_buyers = min_co_buyers
        self.block_size = block_size
        self.weighting_method = weighting_method
        # item_idx -> list of (neighbor_item_idx, similarity_score)
        self.neighbor_index: Dict[int, List[Tuple[int, float]]] = {}
        self.catalog_items: List[str] = []
        self.item_to_idx: Dict[str, int] = {}
        self.idx_to_item: Dict[int, str] = {}
        self.customer_history: Dict[str, Set[str]] = {}
        self.customer_history_indices: Dict[str, List[int]] = {}

    def fit(
        self,
        interaction_csr: csr_matrix,
        catalog_items: List[str],
        customer_to_idx: Dict[str, int],
        item_to_idx: Dict[str, int],
        df_purchases_history: pd.DataFrame,
    ) -> "ItemItemCollaborativeFiltering":
        self.catalog_items = list(catalog_items)
        self.item_to_idx = dict(item_to_idx)
        self.idx_to_item = {idx: sc for sc, idx in item_to_idx.items()}

        # Extract full customer purchase history for fast lookup
        grouped = df_purchases_history.groupby("CustomerID")["StockCode"].unique()
        self.customer_history = {str(cid): set(codes) for cid, codes in grouped.items()}

        # Convert customer history to catalog column indices
        self.customer_history_indices = {}
        for cid, codes in self.customer_history.items():
            valid_indices = [self.item_to_idx[sc] for sc in codes if sc in self.item_to_idx]
            if valid_indices:
                self.customer_history_indices[cid] = valid_indices

        # Apply weighting if configured
        matrix_to_use = interaction_csr
        if self.weighting_method == "tfidf":
            item_df = np.array(interaction_csr.sum(axis=0)).flatten()
            n_users = interaction_csr.shape[0]
            idf = np.log((n_users + 1.0) / (item_df + 1.0)) + 1.0
            idf_diag = diags(idf)
            matrix_to_use = interaction_csr.dot(idf_diag).tocsr()

        # matrix_to_use is (n_users, n_items)
        # item_user is (n_items, n_users)
        item_user = matrix_to_use.T.tocsr()
        n_items = len(self.catalog_items)
        self.neighbor_index = {}

        # Compute cosine similarity in blocks of seed items
        for start_idx in range(0, n_items, self.block_size):
            end_idx = min(start_idx + self.block_size, n_items)
            block_items = item_user[start_idx:end_idx]

            # Cosine similarity block: (block_size, n_items)
            sim_block = cosine_similarity(block_items, item_user, dense_output=True)

            # Also compute co-buyer counts: block_items * interaction_csr.T
            co_buyers_block = (block_items * interaction_csr).toarray()

            for i_local in range(end_idx - start_idx):
                i_global = start_idx + i_local
                # Set diagonal to 0 (zero self-similarity)
                sim_block[i_local, i_global] = 0.0

                # Filter by min_co_buyers
                co_buyers = co_buyers_block[i_local]
                sim_row = sim_block[i_local]
                valid_mask = (co_buyers >= self.min_co_buyers) & (sim_row > 0)

                valid_indices = np.where(valid_mask)[0]
                valid_scores = sim_row[valid_mask]

                if len(valid_indices) == 0:
                    self.neighbor_index[i_global] = []
                    continue

                # Sort by score desc, then item index asc
                # To sort deterministically:
                order = np.lexsort((valid_indices, -valid_scores))
                top_order = order[: self.top_n_neighbors]

                neighbors = [
                    (int(valid_indices[idx]), float(valid_scores[idx]))
                    for idx in top_order
                ]
                self.neighbor_index[i_global] = neighbors

        return self

    def recommend_for_customer(
        self,
        customer_id: str,
        k: int,
        segment_id: Optional[str],
        seg_pop: SegmentPopularityRecommender,
        global_pop: GlobalPopularityRecommender,
        mode: str = "repeat_allowed",
        item_descriptions: Optional[Dict[str, str]] = None,
    ) -> List[RecommendedItem]:
        descriptions = item_descriptions or {}
        hist_items = self.customer_history.get(customer_id, set())
        exclude_items: Set[str] = set()

        if mode == "new_items_only":
            exclude_items = set(hist_items)

        seed_indices = self.customer_history_indices.get(customer_id, [])
        candidate_scores: Dict[int, float] = {}
        candidate_supporters: Dict[int, List[Tuple[str, float]]] = {}

        if seed_indices:
            num_seeds = float(len(seed_indices))
            # Aggregate neighbor scores across all seed items
            for s_idx in seed_indices:
                s_code = self.idx_to_item[s_idx]
                neighbors = self.neighbor_index.get(s_idx, [])
                for n_idx, sim in neighbors:
                    candidate_scores[n_idx] = candidate_scores.get(n_idx, 0.0) + (sim / num_seeds)
                    if n_idx not in candidate_supporters:
                        candidate_supporters[n_idx] = []
                    candidate_supporters[n_idx].append((s_code, sim))

        # Filter and rank candidates
        cf_ranked = []
        for n_idx, score in candidate_scores.items():
            sc = self.idx_to_item[n_idx]
            if sc in exclude_items:
                continue
            if score > 0:
                cf_ranked.append((sc, score, n_idx))

        # Sort: score descending, then StockCode ascending
        cf_ranked.sort(key=lambda x: (-x[1], x[0]))

        results: List[RecommendedItem] = []
        rank = 1
        seen_items = set()

        for sc, score, n_idx in cf_ranked[:k]:
            supporters = candidate_supporters.get(n_idx, [])
            # Sort supporters by similarity desc, StockCode asc
            supporters.sort(key=lambda x: (-x[1], x[0]))
            top_supporters = [s[0] for s in supporters[:3]]
            supporter_names = [descriptions.get(c, c) for c in top_supporters]
            reason_text = (
                f"Frequently bought together with {', '.join(supporter_names)}"
                if supporter_names
                else "Based on products in your purchase history"
            )

            desc = descriptions.get(sc, sc)
            results.append(
                RecommendedItem(
                    rank=rank,
                    stock_code=sc,
                    description=desc,
                    score=float(score),
                    method="item_cf",
                    reason_code="similar_to_purchase_history",
                    reason_text=reason_text,
                    supporting_stock_codes=top_supporters,
                    is_fallback=False,
                )
            )
            seen_items.add(sc)
            rank += 1

        # Fill remaining slots with segment popularity, then global popularity
        if len(results) < k:
            combined_exclude = exclude_items.union(seen_items)
            fallback_items = seg_pop.recommend(
                segment_id=segment_id,
                k=k - len(results),
                global_pop=global_pop,
                exclude_items=combined_exclude,
                item_descriptions=descriptions,
            )
            for fb in fallback_items:
                fb.rank = rank
                results.append(fb)
                rank += 1

        return results
