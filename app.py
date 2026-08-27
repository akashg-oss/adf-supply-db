import io
from datetime import date, timedelta

import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="FG Supply Control Tower",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded",
)

# -----------------------------
# Styling
# -----------------------------
st.markdown("""
<style>
    .block-container {padding-top: 1.2rem; padding-bottom: 2rem;}
    .main-title {font-size: 2rem; font-weight: 750; margin-bottom: 0.1rem;}
    .subtitle {color:#6b7280; margin-bottom:1.2rem;}
    .kpi {
        padding: 18px 18px 14px 18px;
        border: 1px solid #e5e7eb;
        border-radius: 14px;
        background: white;
        min-height: 105px;
    }
    .kpi-label {font-size: .82rem; color:#6b7280; font-weight:600;}
    .kpi-value {font-size: 1.65rem; font-weight:750; margin-top:5px;}
    .kpi-note {font-size:.75rem; color:#6b7280; margin-top:3px;}
    .section-title {font-size:1.15rem; font-weight:700; margin-top:1rem;}
    div[data-testid="stMetric"] {
        border: 1px solid #e5e7eb; padding: 12px; border-radius: 12px;
        background: white;
    }
    [data-testid="stSidebar"] {border-right:1px solid #e5e7eb;}
    .status-critical {color:#b91c1c; font-weight:700;}
    .status-risk {color:#b45309; font-weight:700;}
    .status-healthy {color:#15803d; font-weight:700;}
</style>
""", unsafe_allow_html=True)


# -----------------------------
# Demo data
# -----------------------------
@st.cache_data
def demo_data():
    today = pd.Timestamp.today().normalize()

    skus = [
        ("PPLBFC8903380043464NM1", "Faces Canada STAY Oud Till Dawn - 20ml", "ADF", 8200, 2100, 4000, 18),
        ("PPLBFC8903380042153", "Faces Canada STAY Oud Till Dawn - 50ml", "ADF", 12500, 8400, 5000, 10),
        ("PPLBFC8903380042184", "Faces Canada STAY Vanilla Past Midnight - 50ml", "ADF", 9800, 1800, 7000, 22),
        ("PPLBFC8903380042191", "Faces Canada STAY White Moon Light - 50ml", "ADF", 7600, 6100, 3000, 12),
        ("PPLBFC8903380043402", "Faces Canada Aura Sparkling Ecstacy - 100ml", "ADF", 14500, 3200, 8500, 28),
        ("PPLBFC8903380042207", "Faces Canada STAY Amber Until Sunset - 50ml", "ADF", 8800, 9500, 2500, 7),
        ("PPLBFC8903380042139", "Faces Canada Aura Soft Serenity - 100ml", "ADF", 6100, 9000, 1000, 4),
        ("PPLBFC8903380043396", "Faces Canada Aura Silent Fire - 100ml", "ADF", 7200, 1200, 6000, 25),
        ("PPLBFC8903380042115", "Faces Canada Aura Romantic Daydreams - 100ml", "ADF", 13200, 2400, 6500, 18),
        ("PPLBFC8903380042160", "Faces Canada STAY Bloom After Dark - 50ml", "ADF", 6900, 5600, 1200, 8),
        ("PPLBFC8903380042177", "Faces Canada STAY Sugar After Dusk - 50ml", "ADF", 5400, 4300, 1800, 9),
        ("PPLBFC8903380042108", "Faces Canada Aura Lovestruck Delight - 100ml", "ADF", 11800, 1500, 9000, 31),
    ]

    sku_df = pd.DataFrame(skus, columns=["SKU Code","SKU Name","Supplier","Monthly Demand","FG Stock","Open PO","Lead Time Days"])
    sku_df["Daily Demand"] = sku_df["Monthly Demand"] / 30
    sku_df["Current DOI"] = sku_df["FG Stock"] / sku_df["Daily Demand"]
    sku_df["Projected Stock"] = sku_df["FG Stock"] + sku_df["Open PO"]
    sku_df["Projected DOI"] = sku_df["Projected Stock"] / sku_df["Daily Demand"]
    sku_df["Supply Gap"] = (sku_df["Monthly Demand"] - sku_df["Projected Stock"]).clip(lower=0)

    def status(r):
        if r["Current DOI"] < 7 or r["Supply Gap"] > 5000:
            return "Critical"
        if r["Current DOI"] < 15 or r["Supply Gap"] > 0:
            return "Risk"
        return "Healthy"

    sku_df["Status"] = sku_df.apply(status, axis=1)

    po_rows = []
    po_specs = [
        ("PO-ADF-26081", skus[0][0], "ADF", 4000, 2000, 0, today + pd.Timedelta(days=2)),
        ("PO-ADF-26082", skus[2][0], "ADF", 7000, 0, 0, today - pd.Timedelta(days=3)),
        ("PO-ADF-26083", skus[4][0], "ADF", 8500, 3500, 0, today + pd.Timedelta(days=9)),
        ("PO-ADF-26084", skus[7][0], "ADF", 6000, 0, 0, today + pd.Timedelta(days=5)),
        ("PO-ADF-26085", skus[8][0], "ADF", 6500, 1500, 0, today - pd.Timedelta(days=1)),
        ("PO-ADF-26086", skus[9][0], "ADF", 1200, 1200, 1200, today - pd.Timedelta(days=5)),
        ("PO-ADF-26087", skus[11][0], "ADF", 9000, 0, 0, today + pd.Timedelta(days=14)),
        ("PO-ADF-26088", skus[5][0], "ADF", 2500, 1000, 0, today + pd.Timedelta(days=4)),
    ]
    for po, sku, supplier, qty, dispatch, receipt, etd in po_specs:
        po_rows.append([po, sku, supplier, qty, dispatch, receipt, max(qty-dispatch,0), etd])
    po_df = pd.DataFrame(
        po_rows,
        columns=["PO Number","SKU Code","Supplier","PO Qty","Dispatched Qty","Received Qty","Open Qty","Expected Date"]
    )
    po_df["Days to Due"] = (po_df["Expected Date"] - today).dt.days
    po_df["Delay Days"] = (-po_df["Days to Due"]).clip(lower=0)
    po_df["Status"] = po_df.apply(
        lambda r: "Delayed" if r["Delay Days"] > 0 and r["Open Qty"] > 0
        else ("Open" if r["Open Qty"] > 0 else "Closed"), axis=1
    )

    inv_df = sku_df[["SKU Code","SKU Name","Supplier","FG Stock"]].copy()
    inv_df["As of"] = today

    demand_df = sku_df[["SKU Code","SKU Name","Monthly Demand"]].copy()
    demand_df["Month"] = today.strftime("%b-%Y")

    return sku_df, po_df, inv_df, demand_df


# -----------------------------
# Helpers
# -----------------------------
def money(x):
    return f"₹{x:,.0f}"

def make_kpi(label, value, note=""):
    st.markdown(
        f"""<div class="kpi">
        <div class="kpi-label">{label}</div>
        <div class="kpi-value">{value}</div>
        <div class="kpi-note">{note}</div>
        </div>""",
        unsafe_allow_html=True,
    )

def export_excel(sku_df, po_df, inv_df, demand_df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        sku_df.to_excel(writer, index=False, sheet_name="Supply Plan")
        po_df.to_excel(writer, index=False, sheet_name="PO Tracker")
        inv_df.to_excel(writer, index=False, sheet_name="FG Inventory")
        demand_df.to_excel(writer, index=False, sheet_name="Demand")
    output.seek(0)
    return output


# -----------------------------
# Sidebar
# -----------------------------
sku_df, po_df, inv_df, demand_df = demo_data()

st.sidebar.markdown("## 📦 FG Supply Control Tower")
st.sidebar.caption("Version 2.1 • Demo / Upload Mode")

mode = st.sidebar.radio("Data Mode", ["Demo Mode", "Upload Mode"], index=0)

if mode == "Upload Mode":
    st.sidebar.markdown("### Upload data")
    st.sidebar.caption("Upload the four files below. Demo data is used only when Demo Mode is selected.")
    f_sku = st.sidebar.file_uploader("1. SKU / EAN Master", type=["xlsx","xls","csv"])
    f_demand = st.sidebar.file_uploader("2. Demand", type=["xlsx","xls","csv"])
    f_inv = st.sidebar.file_uploader("3. FG Inventory", type=["xlsx","xls","csv"])
    f_po = st.sidebar.file_uploader("4. Open PO", type=["xlsx","xls","csv"])

    def read_file(f):
        if f is None:
            return None
        return pd.read_csv(f) if f.name.lower().endswith(".csv") else pd.read_excel(f)

    uploaded = [read_file(f_sku), read_file(f_demand), read_file(f_inv), read_file(f_po)]
    if all(x is not None for x in uploaded):
        st.sidebar.success("All four files uploaded. Basic mapping will be applied.")
        # Flexible starter mapping. Expected production mapping can be customized later.
        m_sku, m_demand, m_inv, m_po = uploaded
        m_sku.columns = [str(c).strip() for c in m_sku.columns]
        sku_df = m_sku.copy()
        # Try to standardize common column names.
        ren = {}
        for c in sku_df.columns:
            lc = c.lower()
            if "sku code" in lc or lc == "sku":
                ren[c] = "SKU Code"
            elif "sku name" in lc or "name" == lc:
                ren[c] = "SKU Name"
            elif "supplier" in lc or "vendor" in lc:
                ren[c] = "Supplier"
        sku_df = sku_df.rename(columns=ren)
        if "SKU Code" not in sku_df.columns or "SKU Name" not in sku_df.columns:
            st.sidebar.error("SKU Master needs SKU Code and SKU Name columns.")
        else:
            # Preserve supplied columns; derive operational fields where possible.
            sku_df["Supplier"] = sku_df.get("Supplier", "Unknown")
            sku_df["Monthly Demand"] = 0
            sku_df["FG Stock"] = 0
            sku_df["Open PO"] = 0
            sku_df["Lead Time Days"] = 0
            if "SKU Code" in m_demand.columns:
                demand_col = next((c for c in m_demand.columns if "demand" in str(c).lower()), None)
                if demand_col:
                    dm = m_demand.groupby("SKU Code")[demand_col].sum()
                    sku_df["Monthly Demand"] = sku_df["SKU Code"].map(dm).fillna(0)
            if "SKU Code" in m_inv.columns:
                stock_col = next((c for c in m_inv.columns if any(k in str(c).lower() for k in ["stock","inventory","qty"])), None)
                if stock_col:
                    im = m_inv.groupby("SKU Code")[stock_col].sum()
                    sku_df["FG Stock"] = sku_df["SKU Code"].map(im).fillna(0)
            if "SKU Code" in m_po.columns:
                open_col = next((c for c in m_po.columns if "open" in str(c).lower()), None)
                qty_col = next((c for c in m_po.columns if "po qty" in str(c).lower() or str(c).lower()=="quantity"), None)
                if open_col:
                    pm = m_po.groupby("SKU Code")[open_col].sum()
                elif qty_col:
                    pm = m_po.groupby("SKU Code")[qty_col].sum()
                else:
                    pm = pd.Series(dtype=float)
                sku_df["Open PO"] = sku_df["SKU Code"].map(pm).fillna(0)
            sku_df["Daily Demand"] = sku_df["Monthly Demand"] / 30
            sku_df["Current DOI"] = sku_df["FG Stock"].div(sku_df["Daily Demand"].replace(0, pd.NA)).fillna(999)
            sku_df["Projected Stock"] = sku_df["FG Stock"] + sku_df["Open PO"]
            sku_df["Projected DOI"] = sku_df["Projected Stock"].div(sku_df["Daily Demand"].replace(0, pd.NA)).fillna(999)
            sku_df["Supply Gap"] = (sku_df["Monthly Demand"] - sku_df["Projected Stock"]).clip(lower=0)
            sku_df["Status"] = sku_df.apply(lambda r: "Critical" if r["Current DOI"] < 7 or r["Supply Gap"] > 5000 else ("Risk" if r["Current DOI"] < 15 or r["Supply Gap"] > 0 else "Healthy"), axis=1)
            po_df = m_po.copy()
            inv_df = m_inv.copy()
            demand_df = m_demand.copy()
    else:
        st.sidebar.info("Upload all four files to switch from Demo Mode.")

# -----------------------------
# Header
# -----------------------------
st.markdown('<div class="main-title">FG Supply Control Tower</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Finished Goods sourcing, inventory, PO and supplier risk — management view</div>', unsafe_allow_html=True)

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🏠 Control Tower", "📋 PO Follow-up", "📦 Inventory & Demand",
    "🏭 Supplier Performance", "🔎 SKU Drilldown"
])

# -----------------------------
# Control Tower
# -----------------------------
with tab1:
    total_demand = sku_df["Monthly Demand"].sum()
    fg_stock = sku_df["FG Stock"].sum()
    open_po = sku_df["Open PO"].sum()
    gap = sku_df["Supply Gap"].sum()
    critical = int((sku_df["Status"] == "Critical").sum())
    risk = int((sku_df["Status"] == "Risk").sum())
    delayed = int((po_df["Status"] == "Delayed").sum()) if "Status" in po_df else 0

    c = st.columns(6)
    with c[0]: make_kpi("Monthly Demand", f"{total_demand:,.0f}", "Units")
    with c[1]: make_kpi("FG Inventory", f"{fg_stock:,.0f}", "Units on hand")
    with c[2]: make_kpi("Open PO", f"{open_po:,.0f}", "Units inbound")
    with c[3]: make_kpi("Supply Gap", f"{gap:,.0f}", "After open PO")
    with c[4]: make_kpi("Critical SKUs", critical, "Immediate action")
    with c[5]: make_kpi("Delayed POs", delayed, "Need supplier follow-up")

    st.markdown('<div class="section-title">Management Snapshot</div>', unsafe_allow_html=True)
    left, right = st.columns(2)

    with left:
        st.subheader("SKU Risk Distribution")
        risk_counts = sku_df["Status"].value_counts().reindex(["Critical","Risk","Healthy"]).fillna(0)
        st.bar_chart(risk_counts)

    with right:
        st.subheader("Demand vs Available Supply")
        chart = sku_df.set_index("SKU Name")[["Monthly Demand","FG Stock","Open PO"]].copy()
        st.bar_chart(chart)

    st.subheader("🚨 Priority Action List")
    priority = sku_df.sort_values(["Status","Supply Gap"], ascending=[True, False]).copy()
    priority["Action"] = priority.apply(
        lambda r: "Expedite PO / place additional supply" if r["Status"]=="Critical"
        else ("Confirm supplier dispatch plan" if r["Status"]=="Risk" else "Monitor"),
        axis=1
    )
    st.dataframe(
        priority[["SKU Code","SKU Name","Supplier","Monthly Demand","FG Stock","Open PO","Supply Gap","Current DOI","Status","Action"]],
        use_container_width=True, hide_index=True
    )

# -----------------------------
# PO Follow-up
# -----------------------------
with tab2:
    st.subheader("PO Follow-up")
    po_filter = st.multiselect("PO Status", sorted(po_df["Status"].dropna().unique()), default=sorted(po_df["Status"].dropna().unique()))
    po_view = po_df[po_df["Status"].isin(po_filter)].copy() if po_filter else po_df.iloc[0:0].copy()

    c1, c2, c3 = st.columns(3)
    with c1: st.metric("Open PO Units", f"{po_view['Open Qty'].sum():,.0f}")
    with c2: st.metric("Delayed POs", int((po_view["Status"]=="Delayed").sum()))
    with c3: st.metric("Open POs", int((po_view["Open Qty"]>0).sum()))

    st.dataframe(po_view, use_container_width=True, hide_index=True)

    st.subheader("PO Age / Due Profile")
    due = po_df.copy()
    due["Bucket"] = pd.cut(
        due["Days to Due"],
        bins=[-999, -1, 3, 7, 14, 999],
        labels=["Delayed", "0–3 days", "4–7 days", "8–14 days", "15+ days"]
    )
    st.bar_chart(due.groupby("Bucket", observed=False)["Open Qty"].sum())

# -----------------------------
# Inventory & Demand
# -----------------------------
with tab3:
    st.subheader("Inventory & Demand")
    d1, d2 = st.columns(2)
    with d1:
        st.metric("Average Current DOI", f"{sku_df['Current DOI'].replace([float('inf')], pd.NA).mean():.1f} days")
    with d2:
        st.metric("Average Projected DOI", f"{sku_df['Projected DOI'].replace([float('inf')], pd.NA).mean():.1f} days")

    inv_view = sku_df[["SKU Code","SKU Name","Monthly Demand","FG Stock","Open PO","Current DOI","Projected DOI","Supply Gap","Status"]].copy()
    st.dataframe(inv_view.sort_values("Current DOI"), use_container_width=True, hide_index=True)

    st.subheader("Lowest DOI")
    low = sku_df.nsmallest(8, "Current DOI").set_index("SKU Name")[["Current DOI","Projected DOI"]]
    st.bar_chart(low)

# -----------------------------
# Supplier Performance
# -----------------------------
with tab4:
    st.subheader("Supplier Performance")
    supplier = sku_df.groupby("Supplier", as_index=False).agg(
        SKUs=("SKU Code","count"),
        Demand=("Monthly Demand","sum"),
        FG_Stock=("FG Stock","sum"),
        Open_PO=("Open PO","sum"),
        Supply_Gap=("Supply Gap","sum"),
        Avg_DOI=("Current DOI","mean"),
        Critical_SKUs=("Status", lambda x: (x=="Critical").sum()),
        Risk_SKUs=("Status", lambda x: (x=="Risk").sum()),
    )
    supplier["Risk Exposure"] = supplier["Supply_Gap"] + supplier["Critical_SKUs"] * 1000
    st.dataframe(supplier.round(1), use_container_width=True, hide_index=True)

    a, b = st.columns(2)
    with a:
        st.subheader("Supplier Open PO")
        st.bar_chart(supplier.set_index("Supplier")["Open_PO"])
    with b:
        st.subheader("Supplier Supply Gap")
        st.bar_chart(supplier.set_index("Supplier")["Supply_Gap"])

# -----------------------------
# SKU Drilldown
# -----------------------------
with tab5:
    st.subheader("SKU Drilldown")
    selected = st.selectbox("Select SKU", sku_df["SKU Code"].tolist(), format_func=lambda x: sku_df.loc[sku_df["SKU Code"]==x, "SKU Name"].iloc[0])
    row = sku_df[sku_df["SKU Code"] == selected].iloc[0]

    st.markdown(f"### {row['SKU Name']}")
    k = st.columns(6)
    with k[0]: st.metric("Monthly Demand", f"{row['Monthly Demand']:,.0f}")
    with k[1]: st.metric("FG Stock", f"{row['FG Stock']:,.0f}")
    with k[2]: st.metric("Open PO", f"{row['Open PO']:,.0f}")
    with k[3]: st.metric("Current DOI", f"{row['Current DOI']:.1f} days")
    with k[4]: st.metric("Projected DOI", f"{row['Projected DOI']:.1f} days")
    with k[5]: st.metric("Supply Gap", f"{row['Supply Gap']:,.0f}")

    sku_pos = po_df[po_df["SKU Code"] == selected].copy()
    st.subheader("Related POs")
    if len(sku_pos):
        st.dataframe(sku_pos, use_container_width=True, hide_index=True)
    else:
        st.info("No PO records found for this SKU.")

# -----------------------------
# Export
# -----------------------------
st.sidebar.markdown("---")
st.sidebar.markdown("### Export")
xlsx = export_excel(sku_df, po_df, inv_df, demand_df)
st.sidebar.download_button(
    "⬇️ Download Dashboard Data",
    data=xlsx,
    file_name="FG_Supply_Control_Tower.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
)

st.sidebar.caption("Demo Mode uses sample data. Upload Mode is a starter mapping layer for your operational files.")
