import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from collections import Counter

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Cost of Living Explorer",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display:ital@0;1&family=DM+Sans:wght@300;400;500;600&display=swap');

html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
}

/* Dark background */
.stApp { background-color: #0d0f14; }

/* Sidebar */
[data-testid="stSidebar"] {
    background-color: #13151c;
    border-right: 1px solid #1e2130;
}
[data-testid="stSidebar"] .stMarkdown h2 {
    font-family: 'DM Serif Display', serif;
    color: #e8dcc8;
    font-size: 1.1rem;
    margin-bottom: 0.5rem;
}

/* Headers */
h1 { font-family: 'DM Serif Display', serif !important; color: #e8dcc8 !important; }
h2 { font-family: 'DM Serif Display', serif !important; color: #c9bfa8 !important; }
h3 { font-family: 'DM Sans', sans-serif !important; color: #9fa3b0 !important; font-weight: 500 !important; }

/* Metric cards */
[data-testid="metric-container"] {
    background: #13151c;
    border: 1px solid #1e2130;
    border-radius: 12px;
    padding: 1rem;
}
[data-testid="metric-container"] label { color: #6b7280 !important; font-size: 0.78rem !important; text-transform: uppercase; letter-spacing: 0.08em; }
[data-testid="metric-container"] [data-testid="stMetricValue"] { color: #e8dcc8 !important; font-family: 'DM Serif Display', serif; font-size: 1.6rem !important; }
[data-testid="metric-container"] [data-testid="stMetricDelta"] { font-size: 0.82rem !important; }

/* Tab styling */
[data-baseweb="tab-list"] { background: #13151c !important; border-radius: 10px; padding: 4px; gap: 4px; }
[data-baseweb="tab"] { background: transparent !important; color: #6b7280 !important; border-radius: 7px !important; font-size: 0.85rem !important; }
[aria-selected="true"][data-baseweb="tab"] { background: #1e2130 !important; color: #e8dcc8 !important; }

/* Divider */
hr { border-color: #1e2130 !important; margin: 1.5rem 0; }

/* City pill badges */
.city-badge {
    display: inline-block;
    padding: 3px 12px;
    border-radius: 20px;
    font-size: 0.78rem;
    font-weight: 600;
    letter-spacing: 0.04em;
    margin-right: 6px;
}

/* Scrollbar */
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: #0d0f14; }
::-webkit-scrollbar-thumb { background: #1e2130; border-radius: 3px; }
</style>
""", unsafe_allow_html=True)

# ── Data loading ──────────────────────────────────────────────────────────────
@st.cache_data
def load_data():
    raw = pd.read_excel("cost-of-living.xlsx", index_col=0)
    df = raw.T.copy()
    df.index.name = "location"
    df.reset_index(inplace=True)
    df[["city", "country"]] = df["location"].str.split(",", n=1, expand=True)
    df["city"]    = df["city"].str.strip()
    df["country"] = df["country"].str.strip()

    # Deduplicate column names
    seen, new_cols = {}, []
    for col in df.columns:
        if col in seen:
            seen[col] += 1
            new_cols.append(f"{col} ({seen[col]})")
        else:
            seen[col] = 0
            new_cols.append(col)
    df.columns = new_cols

    id_cols = ["location", "city", "country"]
    metric_cols = [c for c in df.columns if c not in id_cols]
    for col in metric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    return df, metric_cols

df, metric_cols = load_data()

# ── Category definitions ──────────────────────────────────────────────────────
CATEGORIES = {
    "🍽️ Restaurants": [
        "Meal, Inexpensive Restaurant",
        "Meal for 2 People, Mid-range Restaurant, Three-course",
        "McMeal at McDonalds (or Equivalent Combo Meal)",
        "Domestic Beer (0.5 liter draught)",
        "Imported Beer (0.33 liter bottle)",
        "Cappuccino (regular)",
        "Coke/Pepsi (0.33 liter bottle)",
    ],
    "🛒 Groceries": [
        "Milk (regular), (1 liter)",
        "Loaf of Fresh White Bread (500g)",
        "Rice (white), (1kg)",
        "Eggs (regular) (12)",
        "Local Cheese (1kg)",
        "Chicken Breasts (Boneless, Skinless), (1kg)",
        "Beef Round (1kg) (or Equivalent Back Leg Red Meat)",
        "Apples (1kg)", "Banana (1kg)", "Oranges (1kg)",
        "Tomato (1kg)", "Potato (1kg)", "Onion (1kg)", "Lettuce (1 head)",
    ],
    "🚌 Transport": [
        "One-way Ticket (Local Transport)",
        "Monthly Pass (Regular Price)",
        "Taxi Start (Normal Tariff)",
        "Taxi 1km (Normal Tariff)",
        "Gasoline (1 liter)",
    ],
    "🏠 Rent": [
        "Apartment (1 bedroom) in City Centre",
        "Apartment (1 bedroom) Outside of Centre",
        "Apartment (3 bedrooms) in City Centre",
        "Apartment (3 bedrooms) Outside of Centre",
    ],
    "⚡ Utilities": [
        "Basic (Electricity, Heating, Cooling, Water, Garbage) for 85m2 Apartment",
        "Internet (60 Mbps or More, Unlimited Data, Cable/ADSL)",
        "1 min. of Prepaid Mobile Tariff Local (No Discounts or Plans)",
    ],
    "🎭 Leisure": [
        "Fitness Club, Monthly Fee for 1 Adult",
        "Cinema, International Release, 1 Seat",
        "Tennis Court Rent (1 Hour on Weekend)",
    ],
    "👗 Clothing": [
        "1 Pair of Jeans (Levis 501 Or Similar)",
        "1 Summer Dress in a Chain Store (Zara, H&M, ...)",
        "1 Pair of Nike Running Shoes (Mid-Range)",
        "1 Pair of Men Leather Business Shoes",
    ],
}

# Filter to only cols that exist in dataset
CATEGORIES = {
    k: [m for m in v if m in metric_cols]
    for k, v in CATEGORIES.items()
}

SALARY_COL   = next(c for c in metric_cols if "salary" in c.lower())
MORTGAGE_COL = next(c for c in metric_cols if "mortgage" in c.lower())

# City colours (up to 5 cities)
PALETTE = ["#f4a261", "#4cc9f0", "#a8dadc", "#e76f51", "#90be6d"]

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🌍 Cost of Living\n*Explorer*")
    st.markdown("---")

    all_cities = sorted(df["city"].dropna().tolist())
    st.markdown("## Select Cities")
    st.caption("Choose 2–5 cities to compare")

    selected_cities = st.multiselect(
        label="Cities",
        options=all_cities,
        default=["London", "New York", "Tokyo", "Paris"],
        max_selections=5,
        label_visibility="collapsed",
    )

    st.markdown("---")
    st.markdown("## Categories")
    selected_cats = st.multiselect(
        label="Categories",
        options=list(CATEGORIES.keys()),
        default=list(CATEGORIES.keys()),
        label_visibility="collapsed",
    )

    st.markdown("---")
    st.caption("Data: Kaggle — Cost of Living dataset  \nAll prices in **USD**")

# ── Guard ─────────────────────────────────────────────────────────────────────
if len(selected_cities) < 2:
    st.markdown("# Cost of Living Explorer")
    st.info("👈 Select at least **2 cities** in the sidebar to start comparing.")
    st.stop()

# ── Filter data ───────────────────────────────────────────────────────────────
city_df = df[df["city"].isin(selected_cities)].set_index("city")
colors  = {city: PALETTE[i] for i, city in enumerate(selected_cities)}

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("# Cost of Living Explorer")
badges = " ".join(
    f'<span class="city-badge" style="background:{colors[c]}22; color:{colors[c]}; border:1px solid {colors[c]}44">{c}</span>'
    for c in selected_cities
)
st.markdown(badges, unsafe_allow_html=True)
st.markdown("---")

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs([
    "📊  Overview",
    "🔍  Category Breakdown",
    "🏠  Rent & Salary",
    "📋  Full Data Table",
])

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1 — OVERVIEW
# ═══════════════════════════════════════════════════════════════════════════════
with tab1:
    # Composite score for selected categories
    all_selected_metrics = [m for cat in selected_cats for m in CATEGORIES[cat]]
    score_cols = [c for c in all_selected_metrics if c in metric_cols
                  and c not in [SALARY_COL, MORTGAGE_COL]]

    scores = city_df[score_cols].mean(axis=1).reindex(selected_cities)
    baseline = scores.min()

    # ── KPI row ──
    st.markdown("### Composite Cost Score")
    st.caption("Mean price across all selected categories (USD)")
    cols = st.columns(len(selected_cities))
    for i, city in enumerate(selected_cities):
        score = scores.get(city, None)
        delta_val = ((score / baseline) - 1) * 100 if score and baseline else None
        delta_str = f"+{delta_val:.0f}% vs cheapest" if delta_val and delta_val > 0.5 else ("Cheapest" if delta_val is not None else "")
        with cols[i]:
            st.metric(
                label=city,
                value=f"${score:.0f}" if score else "N/A",
                delta=delta_str if delta_str != "Cheapest" else None,
                delta_color="inverse",
            )
            if delta_str == "Cheapest":
                st.caption("🏆 Most affordable")

    st.markdown("---")

    # ── Radar chart ──
    st.markdown("### Category Radar")
    cat_scores = {}
    for cat in selected_cats:
        cols_in_cat = [c for c in CATEGORIES[cat] if c in city_df.columns]
        if cols_in_cat:
            cat_scores[cat] = city_df[cols_in_cat].mean(axis=1)

    if cat_scores:
        radar_df = pd.DataFrame(cat_scores).reindex(selected_cities)
        # Normalise 0-1 per category so radar is readable
        radar_norm = radar_df.div(radar_df.max())

        fig = go.Figure()
        theta = list(radar_df.columns) + [radar_df.columns[0]]

        for city in selected_cities:
            vals = radar_norm.loc[city].tolist() + [radar_norm.loc[city].tolist()[0]]
            fig.add_trace(go.Scatterpolar(
                r=vals, theta=theta, name=city,
                fill="toself", opacity=0.25,
                line=dict(color=colors[city], width=2.5),
                fillcolor=colors[city],
            ))

        fig.update_layout(
            polar=dict(
                bgcolor="#13151c",
                radialaxis=dict(visible=True, range=[0, 1], showticklabels=False, gridcolor="#1e2130"),
                angularaxis=dict(tickfont=dict(size=11, color="#9fa3b0"), gridcolor="#1e2130"),
            ),
            paper_bgcolor="#0d0f14", plot_bgcolor="#0d0f14",
            font=dict(color="#9fa3b0"),
            legend=dict(bgcolor="#13151c", bordercolor="#1e2130", borderwidth=1,
                        font=dict(color="#e8dcc8")),
            margin=dict(l=60, r=60, t=40, b=40),
            height=460,
        )
        st.plotly_chart(fig, use_container_width=True)

    # ── Bar: composite score ──
    st.markdown("### Composite Score Comparison")
    fig2 = go.Figure()
    for city in selected_cities:
        fig2.add_trace(go.Bar(
            x=[city], y=[scores.get(city, 0)],
            name=city,
            marker_color=colors[city],
            text=[f"${scores.get(city, 0):.0f}"],
            textposition="outside",
            textfont=dict(color="#e8dcc8", size=13),
        ))
    fig2.update_layout(
        paper_bgcolor="#0d0f14", plot_bgcolor="#0d0f14",
        font=dict(color="#9fa3b0"),
        xaxis=dict(showgrid=False, tickfont=dict(color="#e8dcc8", size=13)),
        yaxis=dict(gridcolor="#1e2130", tickprefix="$", tickfont=dict(color="#6b7280")),
        showlegend=False,
        margin=dict(l=20, r=20, t=20, b=20),
        height=340,
        bargap=0.35,
    )
    st.plotly_chart(fig2, use_container_width=True)


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2 — CATEGORY BREAKDOWN
# ═══════════════════════════════════════════════════════════════════════════════
with tab2:
    for cat in selected_cats:
        cat_metrics = [c for c in CATEGORIES[cat] if c in city_df.columns]
        if not cat_metrics:
            continue

        st.markdown(f"### {cat}")

        fig = go.Figure()
        x_labels = [m.split("(")[0].strip() for m in cat_metrics]  # short labels

        for city in selected_cities:
            vals = [city_df.loc[city, m] if city in city_df.index else None for m in cat_metrics]
            fig.add_trace(go.Bar(
                name=city, x=x_labels, y=vals,
                marker_color=colors[city],
                text=[f"${v:.0f}" if v else "" for v in vals],
                textposition="outside",
                textfont=dict(size=10, color="#9fa3b0"),
            ))

        fig.update_layout(
            barmode="group",
            paper_bgcolor="#0d0f14", plot_bgcolor="#0d0f14",
            font=dict(color="#9fa3b0"),
            xaxis=dict(tickfont=dict(color="#c9bfa8", size=10), showgrid=False),
            yaxis=dict(gridcolor="#1e2130", tickprefix="$", tickfont=dict(color="#6b7280")),
            legend=dict(bgcolor="#13151c", bordercolor="#1e2130", borderwidth=1,
                        font=dict(color="#e8dcc8"), orientation="h",
                        yanchor="bottom", y=1.02, xanchor="right", x=1),
            margin=dict(l=20, r=20, t=40, b=60),
            height=320,
        )
        st.plotly_chart(fig, use_container_width=True)
        st.markdown("---")


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 3 — RENT & SALARY
# ═══════════════════════════════════════════════════════════════════════════════
with tab3:
    rent_1bed_centre  = "Apartment (1 bedroom) in City Centre"
    rent_1bed_outside = "Apartment (1 bedroom) Outside of Centre"
    rent_3bed_centre  = "Apartment (3 bedrooms) in City Centre"

    col_a, col_b = st.columns(2)

    with col_a:
        st.markdown("### Monthly Salary vs Rent")
        fig = go.Figure()
        bar_items = {
            "Net Salary": (SALARY_COL, "#e8dcc8"),
            "1-bed Centre": (rent_1bed_centre, "#f4a261"),
            "1-bed Outside": (rent_1bed_outside, "#4cc9f0"),
            "3-bed Centre": (rent_3bed_centre, "#e76f51"),
        }
        for label, (col, colour) in bar_items.items():
            if col not in city_df.columns:
                continue
            fig.add_trace(go.Bar(
                name=label,
                x=selected_cities,
                y=[city_df.loc[c, col] if c in city_df.index else None for c in selected_cities],
                marker_color=colour,
            ))
        fig.update_layout(
            barmode="group",
            paper_bgcolor="#0d0f14", plot_bgcolor="#0d0f14",
            font=dict(color="#9fa3b0"),
            xaxis=dict(tickfont=dict(color="#e8dcc8"), showgrid=False),
            yaxis=dict(gridcolor="#1e2130", tickprefix="$"),
            legend=dict(bgcolor="#13151c", bordercolor="#1e2130", borderwidth=1,
                        font=dict(color="#e8dcc8"), orientation="h",
                        yanchor="bottom", y=1.02, xanchor="right", x=1),
            margin=dict(l=10, r=10, t=50, b=10),
            height=380,
        )
        st.plotly_chart(fig, use_container_width=True)

    with col_b:
        st.markdown("### Rent-to-Income Ratio")
        st.caption("% of salary needed to pay 1-bed city centre rent — lower is better")

        ratios = {}
        for city in selected_cities:
            if city not in city_df.index:
                continue
            salary = city_df.loc[city, SALARY_COL]
            rent   = city_df.loc[city, rent_1bed_centre]
            if pd.notna(salary) and pd.notna(rent) and salary > 0:
                ratios[city] = round((rent / salary) * 100, 1)

        if ratios:
            sorted_cities = sorted(ratios, key=ratios.get)
            fig2 = go.Figure(go.Bar(
                x=list(ratios[c] for c in sorted_cities),
                y=sorted_cities,
                orientation="h",
                marker_color=[colors[c] for c in sorted_cities],
                text=[f"{ratios[c]}%" for c in sorted_cities],
                textposition="outside",
                textfont=dict(color="#e8dcc8"),
            ))
            fig2.add_vline(x=30, line_dash="dash", line_color="#6b7280",
                           annotation_text="30% benchmark",
                           annotation_font_color="#6b7280")
            fig2.update_layout(
                paper_bgcolor="#0d0f14", plot_bgcolor="#0d0f14",
                font=dict(color="#9fa3b0"),
                xaxis=dict(gridcolor="#1e2130", ticksuffix="%",
                           tickfont=dict(color="#6b7280")),
                yaxis=dict(tickfont=dict(color="#e8dcc8"), showgrid=False),
                margin=dict(l=10, r=60, t=10, b=10),
                height=380,
                showlegend=False,
            )
            st.plotly_chart(fig2, use_container_width=True)

    # ── Purchasing power table ──
    st.markdown("### Purchasing Power at a Glance")
    st.caption("How many days of salary needed to afford common items")

    salary_row = {city: city_df.loc[city, SALARY_COL] / 30
                  for city in selected_cities if city in city_df.index}

    pp_items = {
        "Inexpensive meal": "Meal, Inexpensive Restaurant",
        "Monthly transport pass": "Monthly Pass (Regular Price)",
        "1L gasoline": "Gasoline (1 liter)",
        "Running shoes": "1 Pair of Nike Running Shoes (Mid-Range)",
        "Cinema ticket": "Cinema, International Release, 1 Seat",
    }

    pp_data = []
    for label, col in pp_items.items():
        if col not in city_df.columns:
            continue
        row = {"Item": label}
        for city in selected_cities:
            if city not in city_df.index:
                continue
            item_price   = city_df.loc[city, col]
            daily_salary = salary_row.get(city)
            if pd.notna(item_price) and daily_salary and daily_salary > 0:
                row[city] = f"{item_price / daily_salary:.1f} days"
            else:
                row[city] = "N/A"
        pp_data.append(row)

    pp_df = pd.DataFrame(pp_data).set_index("Item")
    st.dataframe(
        pp_df,
        use_container_width=True,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 4 — FULL DATA TABLE
# ═══════════════════════════════════════════════════════════════════════════════
with tab4:
    st.markdown("### All Metrics")
    st.caption("All prices in USD")

    # Build a clean pivot: metrics as rows, cities as columns
    display_cols = [c for c in metric_cols if c in city_df.columns]
    table = city_df[display_cols].T.reindex(columns=selected_cities)
    table.index.name = "Metric"

    # Format as currency
    def fmt(val):
        if pd.isna(val):
            return "—"
        return f"${val:,.2f}"

    st.dataframe(
        table.style.format(fmt),
        use_container_width=True,
        height=600,
    )

    # Download button
    csv = table.to_csv()
    st.download_button(
        label="⬇️ Download as CSV",
        data=csv,
        file_name="cost_of_living_comparison.csv",
        mime="text/csv",
    )
