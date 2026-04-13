import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from collections import Counter

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
html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
.stApp { background-color: #0d0f14; }
[data-testid="stSidebar"] { background-color: #13151c; border-right: 1px solid #1e2130; }
h1 { font-family: 'DM Serif Display', serif !important; color: #e8dcc8 !important; }
h2 { font-family: 'DM Serif Display', serif !important; color: #c9bfa8 !important; }
h3 { color: #9fa3b0 !important; font-weight: 500 !important; }
[data-testid="metric-container"] { background: #13151c; border: 1px solid #1e2130; border-radius: 12px; padding: 1rem; }
[data-testid="metric-container"] label { color: #6b7280 !important; font-size: 0.78rem !important; text-transform: uppercase; letter-spacing: 0.08em; }
[data-testid="metric-container"] [data-testid="stMetricValue"] { color: #e8dcc8 !important; font-size: 1.6rem !important; }
hr { border-color: #1e2130 !important; margin: 1.5rem 0; }
.city-badge { display: inline-block; padding: 3px 12px; border-radius: 20px; font-size: 0.78rem; font-weight: 600; margin-right: 6px; }
</style>
""", unsafe_allow_html=True)

# ── Plot style ────────────────────────────────────────────────────────────────
plt.rcParams.update({
    'figure.facecolor': '#0d0f14',
    'axes.facecolor':   '#13151c',
    'axes.edgecolor':   '#1e2130',
    'axes.labelcolor':  '#9fa3b0',
    'xtick.color':      '#9fa3b0',
    'ytick.color':      '#9fa3b0',
    'text.color':       '#e8dcc8',
    'grid.color':       '#1e2130',
    'grid.linewidth':   0.7,
})

PALETTE = ["#f4a261", "#4cc9f0", "#a8dadc", "#e76f51", "#90be6d"]

# ── Load data ─────────────────────────────────────────────────────────────────
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

# ── Categories ────────────────────────────────────────────────────────────────
CATEGORIES = {
    "🍽️ Restaurants": ["Meal, Inexpensive Restaurant", "Meal for 2 People, Mid-range Restaurant, Three-course",
                        "McMeal at McDonalds (or Equivalent Combo Meal)", "Cappuccino (regular)",
                        "Domestic Beer (0.5 liter draught)"],
    "🛒 Groceries":   ["Milk (regular), (1 liter)", "Loaf of Fresh White Bread (500g)", "Rice (white), (1kg)",
                        "Eggs (regular) (12)", "Chicken Breasts (Boneless, Skinless), (1kg)",
                        "Beef Round (1kg) (or Equivalent Back Leg Red Meat)", "Apples (1kg)", "Banana (1kg)"],
    "🚌 Transport":   ["One-way Ticket (Local Transport)", "Monthly Pass (Regular Price)",
                        "Taxi Start (Normal Tariff)", "Gasoline (1 liter)"],
    "🏠 Rent":        ["Apartment (1 bedroom) in City Centre", "Apartment (1 bedroom) Outside of Centre",
                        "Apartment (3 bedrooms) in City Centre", "Apartment (3 bedrooms) Outside of Centre"],
    "⚡ Utilities":   ["Basic (Electricity, Heating, Cooling, Water, Garbage) for 85m2 Apartment",
                        "Internet (60 Mbps or More, Unlimited Data, Cable/ADSL)"],
    "🎭 Leisure":     ["Fitness Club, Monthly Fee for 1 Adult", "Cinema, International Release, 1 Seat"],
    "👗 Clothing":    ["1 Pair of Jeans (Levis 501 Or Similar)", "1 Pair of Nike Running Shoes (Mid-Range)",
                        "1 Summer Dress in a Chain Store (Zara, H&M, ...)"],
}
CATEGORIES = {k: [m for m in v if m in metric_cols] for k, v in CATEGORIES.items()}

SALARY_COL   = next(c for c in metric_cols if "salary" in c.lower())
MORTGAGE_COL = next(c for c in metric_cols if "mortgage" in c.lower())
RENT_COL     = next(c for c in metric_cols if "1 bedroom" in c.lower() and "centre" in c.lower() and "outside" not in c.lower())

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🌍 Cost of Living\n*Explorer*")
    st.markdown("---")
    all_cities = sorted(df["city"].dropna().tolist())
    st.markdown("## Select Cities")
    st.caption("Choose 2–5 cities to compare")
    selected_cities = st.multiselect(
        label="Cities", options=all_cities,
        default=["London", "New York", "Tokyo", "Paris"],
        max_selections=5, label_visibility="collapsed",
    )
    st.markdown("---")
    st.markdown("## Categories")
    selected_cats = st.multiselect(
        label="Categories", options=list(CATEGORIES.keys()),
        default=list(CATEGORIES.keys()), label_visibility="collapsed",
    )
    st.markdown("---")
    st.caption("Data: Kaggle — Cost of Living  \nAll prices in **USD**")

if len(selected_cities) < 2:
    st.markdown("# Cost of Living Explorer")
    st.info("👈 Select at least **2 cities** in the sidebar to start comparing.")
    st.stop()

city_df = df[df["city"].isin(selected_cities)].set_index("city")
colors  = {city: PALETTE[i] for i, city in enumerate(selected_cities)}

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("# 🌍 Cost of Living Explorer")
badges = " ".join(
    f'<span class="city-badge" style="background:{colors[c]}22;color:{colors[c]};border:1px solid {colors[c]}44">{c}</span>'
    for c in selected_cities
)
st.markdown(badges, unsafe_allow_html=True)
st.markdown("---")

tab1, tab2, tab3, tab4 = st.tabs(["📊 Overview", "🔍 Category Breakdown", "🏠 Rent & Salary", "📋 Full Table"])

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1 — OVERVIEW
# ═══════════════════════════════════════════════════════════════════════════════
with tab1:
    all_metrics = [m for cat in selected_cats for m in CATEGORIES[cat]]
    score_cols  = [c for c in all_metrics if c in metric_cols and c not in [SALARY_COL, MORTGAGE_COL]]
    scores      = city_df[score_cols].mean(axis=1).reindex(selected_cities)
    baseline    = scores.min()

    st.markdown("### Composite Cost Score")
    st.caption("Mean price across all selected categories (USD)")
    cols = st.columns(len(selected_cities))
    for i, city in enumerate(selected_cities):
        score = scores.get(city)
        delta_val = ((score / baseline) - 1) * 100 if score and baseline else None
        with cols[i]:
            st.metric(
                label=city,
                value=f"${score:.0f}" if score else "N/A",
                delta=f"+{delta_val:.0f}% vs cheapest" if delta_val and delta_val > 0.5 else None,
                delta_color="inverse",
            )
            if delta_val is not None and delta_val <= 0.5:
                st.caption("🏆 Most affordable")

    st.markdown("---")

    # Composite bar chart
    st.markdown("### Composite Score Comparison")
    fig, ax = plt.subplots(figsize=(10, 4))
    x = np.arange(len(selected_cities))
    bars = ax.bar(x, [scores.get(c, 0) for c in selected_cities],
                  color=[colors[c] for c in selected_cities], width=0.5, zorder=2)
    ax.set_xticks(x)
    ax.set_xticklabels(selected_cities, fontsize=12)
    ax.set_ylabel("USD")
    ax.yaxis.grid(True, zorder=0)
    ax.set_axisbelow(True)
    for bar in bars:
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
                f"${bar.get_height():.0f}", ha='center', va='bottom', fontsize=11)
    plt.tight_layout()
    st.pyplot(fig)
    plt.close()

    st.markdown("---")

    # Radar chart
    st.markdown("### Category Radar")
    cat_scores = {}
    for cat in selected_cats:
        cols_in_cat = [c for c in CATEGORIES[cat] if c in city_df.columns]
        if cols_in_cat:
            cat_scores[cat] = city_df[cols_in_cat].mean(axis=1)

    if cat_scores:
        radar_df   = pd.DataFrame(cat_scores).reindex(selected_cities)
        radar_norm = radar_df.div(radar_df.max())
        labels     = list(radar_df.columns)
        N          = len(labels)
        angles     = np.linspace(0, 2 * np.pi, N, endpoint=False).tolist()
        angles    += angles[:1]

        fig, ax = plt.subplots(figsize=(6, 6), subplot_kw=dict(polar=True))
        ax.set_facecolor('#13151c')
        fig.patch.set_facecolor('#0d0f14')
        ax.spines['polar'].set_color('#1e2130')
        ax.grid(color='#1e2130', linewidth=0.7)

        for city in selected_cities:
            vals = radar_norm.loc[city].tolist() + [radar_norm.loc[city].tolist()[0]]
            ax.plot(angles, vals, color=colors[city], linewidth=2, label=city)
            ax.fill(angles, vals, color=colors[city], alpha=0.08)

        ax.set_thetagrids(np.degrees(angles[:-1]),
                          [l.replace("🍽️ ", "").replace("🛒 ", "").replace("🚌 ", "")
                            .replace("🏠 ", "").replace("⚡ ", "").replace("🎭 ", "").replace("👗 ", "")
                           for l in labels],
                          fontsize=9, color='#9fa3b0')
        ax.set_ylim(0, 1)
        ax.set_yticks([])
        ax.legend(loc='upper right', bbox_to_anchor=(1.35, 1.15),
                  facecolor='#13151c', edgecolor='#1e2130',
                  labelcolor='#e8dcc8', fontsize=9)
        plt.tight_layout()
        st.pyplot(fig)
        plt.close()

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2 — CATEGORY BREAKDOWN
# ═══════════════════════════════════════════════════════════════════════════════
with tab2:
    for cat in selected_cats:
        cat_metrics = [c for c in CATEGORIES[cat] if c in city_df.columns]
        if not cat_metrics:
            continue
        st.markdown(f"### {cat}")

        short_labels = [m.split("(")[0].strip()[:30] for m in cat_metrics]
        x = np.arange(len(cat_metrics))
        width = 0.8 / len(selected_cities)

        fig, ax = plt.subplots(figsize=(12, 4))
        for i, city in enumerate(selected_cities):
            vals = [city_df.loc[city, m] if city in city_df.index else 0 for m in cat_metrics]
            offset = (i - len(selected_cities)/2 + 0.5) * width
            ax.bar(x + offset, vals, width=width*0.9, color=colors[city], label=city, zorder=2)

        ax.set_xticks(x)
        ax.set_xticklabels(short_labels, rotation=20, ha='right', fontsize=9)
        ax.set_ylabel("USD")
        ax.yaxis.grid(True, zorder=0)
        ax.set_axisbelow(True)
        ax.legend(facecolor='#13151c', edgecolor='#1e2130', labelcolor='#e8dcc8', fontsize=9)
        plt.tight_layout()
        st.pyplot(fig)
        plt.close()
        st.markdown("---")

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 3 — RENT & SALARY
# ═══════════════════════════════════════════════════════════════════════════════
with tab3:
    col_a, col_b = st.columns(2)

    with col_a:
        st.markdown("### Salary vs Rent")
        items  = {"Net Salary": (SALARY_COL, "#e8dcc8"),
                  "1-bed Centre": (RENT_COL, "#f4a261")}
        x      = np.arange(len(selected_cities))
        width  = 0.35
        fig, ax = plt.subplots(figsize=(7, 4))
        for i, (label, (col, colour)) in enumerate(items.items()):
            if col not in city_df.columns:
                continue
            vals = [city_df.loc[c, col] if c in city_df.index else 0 for c in selected_cities]
            ax.bar(x + (i - 0.5) * width, vals, width=width*0.9, color=colour, label=label, zorder=2)
        ax.set_xticks(x)
        ax.set_xticklabels(selected_cities, fontsize=10)
        ax.set_ylabel("USD / month")
        ax.yaxis.grid(True, zorder=0)
        ax.set_axisbelow(True)
        ax.legend(facecolor='#13151c', edgecolor='#1e2130', labelcolor='#e8dcc8')
        plt.tight_layout()
        st.pyplot(fig)
        plt.close()

    with col_b:
        st.markdown("### Rent-to-Income Ratio")
        st.caption("% of salary needed for 1-bed city centre rent")
        ratios = {}
        for city in selected_cities:
            if city not in city_df.index:
                continue
            salary = city_df.loc[city, SALARY_COL]
            rent   = city_df.loc[city, RENT_COL]
            if pd.notna(salary) and pd.notna(rent) and salary > 0:
                ratios[city] = round((rent / salary) * 100, 1)

        if ratios:
            sorted_cities = sorted(ratios, key=ratios.get)
            fig, ax = plt.subplots(figsize=(7, 4))
            bars = ax.barh(sorted_cities, [ratios[c] for c in sorted_cities],
                           color=[colors[c] for c in sorted_cities], zorder=2)
            ax.axvline(30, color='#6b7280', linestyle='--', linewidth=1, label='30% benchmark')
            ax.xaxis.grid(True, zorder=0)
            ax.set_axisbelow(True)
            ax.set_xlabel("%")
            for bar, city in zip(bars, sorted_cities):
                ax.text(bar.get_width() + 0.5, bar.get_y() + bar.get_height()/2,
                        f"{ratios[city]}%", va='center', fontsize=10)
            ax.legend(facecolor='#13151c', edgecolor='#1e2130', labelcolor='#e8dcc8')
            plt.tight_layout()
            st.pyplot(fig)
            plt.close()

    # Purchasing power table
    st.markdown("### Purchasing Power")
    st.caption("Days of salary needed to afford each item")
    pp_items = {
        "Inexpensive meal":    "Meal, Inexpensive Restaurant",
        "Monthly transport":   "Monthly Pass (Regular Price)",
        "Running shoes":       "1 Pair of Nike Running Shoes (Mid-Range)",
        "Cinema ticket":       "Cinema, International Release, 1 Seat",
        "1L gasoline":         "Gasoline (1 liter)",
    }
    pp_data = []
    for label, col in pp_items.items():
        if col not in city_df.columns:
            continue
        row = {"Item": label}
        for city in selected_cities:
            if city not in city_df.index:
                continue
            price  = city_df.loc[city, col]
            salary = city_df.loc[city, SALARY_COL]
            if pd.notna(price) and pd.notna(salary) and salary > 0:
                row[city] = f"{price / (salary/30):.1f} days"
            else:
                row[city] = "N/A"
        pp_data.append(row)
    st.dataframe(pd.DataFrame(pp_data).set_index("Item"), use_container_width=True)

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 4 — FULL TABLE
# ═══════════════════════════════════════════════════════════════════════════════
with tab4:
    st.markdown("### All Metrics")
    st.caption("All prices in USD")
    display_cols = [c for c in metric_cols if c in city_df.columns]
    table = city_df[display_cols].T.reindex(columns=selected_cities)
    table.index.name = "Metric"

    def fmt(val):
        return f"${val:,.2f}" if pd.notna(val) else "—"

    st.dataframe(table.style.format(fmt), use_container_width=True, height=600)
    st.download_button("⬇️ Download as CSV", table.to_csv(),
                       "cost_of_living_comparison.csv", "text/csv")
