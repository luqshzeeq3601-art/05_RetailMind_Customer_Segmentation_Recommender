# RetailMind workflow image

Asset: [workflow.png](workflow.png). Generated with the built-in OpenAI image-generation tool on 6 October 2026 and reviewed against the project source. Style: modern light theme, warm white background, navy text and teal accents. This is an architecture illustration, not a screenshot or measured result chart.

## Meaning and source

The README supplies the accessible text summary and links to the owning technical/data/protocol documents. Model metrics remain sourced from the saved analytical artifacts. The diagram does not certify deployment or operational impact.

## Generation prompt

```text
Use case: infographic-diagram. Asset type: a GitHub README workflow image. Wide landscape 2:1, at least 1600 pixels wide. Modern light theme: warm white background, navy text, restrained teal accents, flat rounded cards, thin clean arrowheads, original small line icons, generous whitespace. No dark panels, gradients, logos, watermarks or fake screenshots. Large readable typography at a 900-pixel display width. Use EXACT labels given below. Explain implemented source architecture; do not invent metrics, successful deployment, automatic retraining or measured commercial impact.
Exact title: "RetailMind". Exact subtitle: "From purchase history to segments and recommendations".
Left block "Clean purchase history" feeds "Chronological snapshots".
That snapshot block branches into TWO parallel blocks: "RFM + K-Means segments" and "Item-item collaborative filtering". Both feed "Trusted release bundle".
The release bundle feeds "Shared recommendation service".
From the shared-service card, two output cards: "Streamlit + FastAPI + CLI" and "Popularity fallback".
The fallback card subtitle is "Sparse history / new customer", and a small arrow from it points back to the same output-interface card to show the returned recommendations.
Footer: "Features use historical data only" and "Offline ranking is not measured revenue uplift".
Constraints: avoid an infinite cycle; fallback is a branch used before outputs. Customer IDs are lookup keys, not ML features. No sales/ROI metrics or causal campaign claim. This image should make both segmentation and the sparse-history fallback understandable.
```

## Reviewed correction: Edit

```text
Edit this RetailMind image with ONE precise wording correction. Preserve all geometry, labels, colors, icons, arrows and the light modern theme. Inside the "Popularity fallback" card, replace only the small explanatory sentence "Use globally popular items when personalized results are unavailable" with exactly "Use segment or global popularity when personalized results are unavailable". The existing "Sparse history / new customer" subtitle stays. Do not change the rest of the image.
```
