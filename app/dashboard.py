"""RetailMind: Customer Segmentation and Product Recommendation Dashboard."""

import json
from pathlib import Path
from typing import Optional

import pandas as pd
import plotly.express as px
import streamlit as st

from retailmind.contracts import RecommendationRequest
from retailmind.service import RetailMindService

st.set_page_config(
    page_title="RetailMind — Customer Segmentation & Recommender",
    page_icon="🛍️",
    layout="wide",
    initial_sidebar_state="expanded",
)


@st.cache_resource
def load_service(bundle_path: str) -> Optional[RetailMindService]:
    """Cache and load the RetailMindService bundle."""
    try:
        p = Path(bundle_path)
        if not p.exists() or not (p / "manifest.json").exists():
            return None
        return RetailMindService(bundle_path)
    except Exception:
        return None


def main() -> None:
    st.sidebar.title("🛍️ RetailMind")
    st.sidebar.markdown(
        "**Customer Segmentation & Personalized Recommendations**\n\n"
        "Decision-support dashboard for retail analysts and marketers."
    )

    bundle_dir = st.sidebar.text_input("Artifact Bundle Path", value="artifacts/release")
    service = load_service(bundle_dir)

    if service is None:
        st.error(f"⚠️ Model bundle not found or invalid at `{bundle_dir}`.")
        st.info(
            "### Setup Instructions\n"
            "To build and prepare the model artifacts, run the following pipeline commands:\n"
            "```powershell\n"
            "python -m retailmind.cli prepare --config configs/default.yaml\n"
            "python -m retailmind.cli train --stage validation --config configs/default.yaml\n"
            "python -m retailmind.cli freeze --config configs/default.yaml\n"
            "python -m retailmind.cli train --stage test --config configs/default.yaml\n"
            "```"
        )
        return

    manifest = service.manifest

    # Header metric banner
    st.title("🛍️ RetailMind Intelligence Console")
    st.caption(
        f"Artifact Version: `{manifest.bundle_version}` | Cutoff Date: `{manifest.snapshot_cutoff[:10]}` | Currency: `GBP (£)`"
    )

    tab_overview, tab_customer, tab_evidence = st.tabs(
        ["📊 Customer Segments Overview", "👤 Customer Profile & Recommendations", "📑 Model Card & Evaluation"]
    )

    # ==================== TAB 1: OVERVIEW ====================
    with tab_overview:
        st.subheader("Customer Cohort & Segment Summary")

        # Top summary KPIs
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Known Customers", f"{manifest.known_customers_count:,}")
        c2.metric("Active Customers (180d)", f"{manifest.active_customers_count:,}")
        c3.metric("Eligible Product Catalog", f"{manifest.catalog_size:,} items")
        c4.metric("Segment Model", f"{manifest.segment_algorithm}")

        st.markdown("---")

        df_segs = service.df_segment_summaries.copy()

        # Display Segment Table
        st.markdown("#### Segment Profiles")
        st.dataframe(
            df_segs.style.format(
                {
                    "customer_count": "{:,}",
                    "customer_share": "{:.1%}",
                    "median_recency": "{:.0f} days",
                    "median_frequency": "{:.0f} orders",
                    "median_monetary": "£{:,.2f}",
                }
            ),
            use_container_width=True,
        )

        csv_seg_data = service.export_segments_csv()
        st.download_button(
            label="📥 Download Segments Summary CSV",
            data=csv_seg_data,
            file_name="retailmind_segments_summary.csv",
            mime="text/csv",
        )

        st.markdown("---")
        st.markdown("#### Visual Distribution")

        v1, v2 = st.columns(2)
        with v1:
            fig_pie = px.pie(
                df_segs,
                values="customer_count",
                names="segment_label",
                title="Customer Share by Segment",
                hole=0.4,
                color_discrete_sequence=px.colors.qualitative.Prism,
            )
            st.plotly_chart(fig_pie, use_container_width=True)

        with v2:
            fig_bar = px.bar(
                df_segs,
                x="segment_id",
                y="median_monetary",
                color="segment_label",
                text="median_monetary",
                title="Median Spending by Segment (£)",
                labels={"segment_id": "Segment", "median_monetary": "Median Monetary (£)"},
                color_discrete_sequence=px.colors.qualitative.Prism,
            )
            fig_bar.update_traces(texttemplate="£%{text:,.0f}", textposition="outside")
            st.plotly_chart(fig_bar, use_container_width=True)

    # ==================== TAB 2: CUSTOMER RECOMMENDATIONS ====================
    with tab_customer:
        st.subheader("Customer Intelligence & Top-K Recommendations")

        # Load demo customers fixture
        demo_fixture_path = Path("tests/fixtures/demo_customers.json")
        demo_options = {}
        if demo_fixture_path.exists():
            with open(demo_fixture_path, "r", encoding="utf-8") as f:
                demo_list = json.load(f)
                demo_options = {d["label"]: d["id"] for d in demo_list}

        col_sel1, col_sel2 = st.columns([2, 2])
        with col_sel1:
            selected_demo = st.selectbox(
                "Select a Preset Demo Customer Persona:",
                options=["-- Custom ID Search --"] + list(demo_options.keys()),
            )

        with col_sel2:
            if selected_demo != "-- Custom ID Search --":
                default_cid = demo_options[selected_demo]
            else:
                default_cid = "17850"
            input_cid = st.text_input("Customer ID (e.g. 17850, 18102, DEMO-NEW-999):", value=default_cid)

        # Recommendation settings
        st.markdown("#### Recommendation Parameters")
        p1, p2 = st.columns(2)
        with p1:
            req_k = st.slider("Top K Recommendations:", min_value=1, max_value=20, value=10)
        with p2:
            mode_choice = st.radio(
                "Recommendation Mode:",
                options=["repeat_allowed", "new_items_only"],
                format_func=lambda x: "Allow Repeat Purchases (Personalized Favorites + Next Items)" if x == "repeat_allowed" else "New Products Only (Exclude Prior History)",
            )

        if st.button("Generate Recommendations", type="primary"):
            req = RecommendationRequest(
                customer_id=input_cid.strip(),
                top_k=req_k,
                mode=mode_choice,
                bundle=bundle_dir,
            )
            resp = service.recommend(req)

            st.markdown("---")
            # Customer Status Card
            st.markdown("### Customer Profile")
            prof_cols = st.columns(4)

            status_display = {
                "known_active": "🟢 Active Customer",
                "known_inactive": "🟡 Inactive (>180d)",
                "unknown_customer": "⚪ Unknown / Cold Start",
            }.get(resp.customer_status, resp.customer_status)

            prof_cols[0].metric("Customer Status", status_display)
            prof_cols[1].metric("Segment", f"{resp.segment_id or 'N/A'}")
            prof_cols[2].metric("Segment Name", f"{resp.segment_label or 'Global Fallback'}")

            profile = service.get_customer_profile(input_cid.strip())
            if profile:
                prof_cols[3].metric("Past Spending (180d)", f"£{profile.monetary_gbp:,.2f}")
            else:
                prof_cols[3].metric("Past Spending", "£0.00")

            # Recommendations Output
            st.markdown(f"### Recommended Products (Top {resp.returned_k})")
            status_alert = {
                "ok": "✅ Personalized recommendations generated successfully.",
                "fallback_only": "ℹ️ Note: Returned items are top popularity fallbacks due to zero collaborative filtering matches or cold-start status.",
                "insufficient_catalog": "⚠️ Fewer candidate products available in catalog than requested K.",
                "empty_catalog": "❌ No eligible catalog items found.",
            }.get(resp.status, resp.status)
            st.info(status_alert)

            if resp.items:
                items_data = []
                for item in resp.items:
                    items_data.append(
                        {
                            "Rank": item.rank,
                            "Stock Code": item.stock_code,
                            "Product Description": item.description,
                            "Score": f"{item.score:.4f}",
                            "Algorithm": "Collaborative Filtering" if item.method == "item_cf" else ("Segment Popularity" if item.method == "segment_popularity" else "Global Popularity"),
                            "Reason": item.reason_text,
                            "Fallback?": "⚠️ Fallback" if item.is_fallback else "✨ Personalized",
                        }
                    )
                df_recs = pd.DataFrame(items_data)
                st.dataframe(df_recs, use_container_width=True, hide_index=True)

                csv_rec_data = service.export_recommendations_csv(resp)
                st.download_button(
                    label=f"📥 Download Recommendations CSV ({resp.customer_id})",
                    data=csv_rec_data,
                    file_name=f"recommendations_{resp.customer_id}_{resp.recommendation_mode}.csv",
                    mime="text/csv",
                )

    # ==================== TAB 3: MODEL CARD & EVIDENCE ====================
    with tab_evidence:
        st.subheader("Model Performance & Frozen Evaluation Protocol")

        test_report_path = Path("reports/test_metrics.json")

        if test_report_path.exists():
            with open(test_report_path, "r", encoding="utf-8") as f:
                test_rep = json.load(f)

            st.markdown("#### Final Test Holdout Performance (28-Day Temporal Holdout)")
            st.markdown(
                f"- **Cutoff**: `{test_rep['snapshot_cutoff'][:10]}` | **Holdout**: `{test_rep['holdout_start'][:10]}` to `{test_rep['holdout_end'][:10]}`\n"
                f"- **Evaluated Returners**: `{test_rep['primary_cohort_size']:,}` | **Cold Start Users**: `{test_rep['cold_start_cohort_size']:,}`\n"
                f"- **Selected Recommender**: `{test_rep['selected_recommender']}`"
            )

            # Build comparison table
            table_rows = []
            for m_name, m_data in test_rep["models"].items():
                table_rows.append(
                    {
                        "Model": m_name,
                        "Cohort": m_data["cohort_size"],
                        "NDCG@10": f"{m_data['mean_ndcg']:.4f}",
                        "Recall@10": f"{m_data['mean_recall']:.4f}",
                        "Precision@10": f"{m_data['mean_precision']:.4f}",
                        "HitRate@10": f"{m_data['mean_hit_rate']:.1%}",
                        "Catalog Coverage": f"{m_data['catalog_coverage']:.1%}",
                        "Fallback Share": f"{m_data['fallback_item_share']:.1%}",
                    }
                )
            st.dataframe(pd.DataFrame(table_rows), use_container_width=True, hide_index=True)

            ci_diff = test_rep["bootstrap_ci_95"]["difference_ndcg"]
            st.success(
                f"**Statistical Significance:** 95% Paired Bootstrap Confidence Interval for NDCG@10 difference (CF vs Baseline): `[{ci_diff[0]:.4f}, {ci_diff[1]:.4f}]`"
            )
        else:
            st.warning("Test metrics report not yet generated.")

        st.markdown("---")
        st.markdown(
            "#### ⚠️ Operational Scope & Analytical Limitations\n"
            "1. **Implicit Feedback:** Recommendation scores reflect co-purchase cosine affinity and historical popularity, not explicit ratings or purchase probabilities.\n"
            "2. **Offline vs Online:** Offline NDCG and Recall evaluate rank quality against held-out purchases; they do not establish causal conversion uplift without live A/B testing.\n"
            "3. **Data Freshness:** Recommendations utilize historical purchases strictly preceding the snapshot cutoff date to ensure zero future data leakage.\n"
            "4. **No Automated Actions:** RetailMind is an analyst decision-support tool. It does not automate live marketing campaigns, payments, or stock ordering."
        )


if __name__ == "__main__":
    main()
