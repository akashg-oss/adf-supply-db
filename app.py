import io
from datetime import datetime
import numpy as np
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="FG Supply & Sourcing Control Tower",
    page_icon="📦",
    layout="wide",
)

# ============================================================
# STYLE
# ============================================================
st.markdown("""
<style>
.block-container {padding-top: 1rem; padding-bottom: 2rem;}
[data-testid="stMetric"] {
    border: 1px solid #e5e7eb;
    border-radius: 12px;
    padding: 12px;
    background: white;
}
.small-note {color:#6b7280;font-size:12px;}
.alert-critical {padding:12px;border-radius:10px;border:1px solid #fecaca;background:#fef2f2;}
.alert-warning {padding:12px;border-radius:10px;border:1px solid #fed7aa;background:#fff7ed;}
.alert-good {padding:12px;border-radius:10px;border:1px solid #bbf7d0;background:#f0fdf4;}
</style>
""", unsafe_allow_html=True)

st.title("📦 FG Supply & Sourcing Control Tower")
st.caption("Version 2 • Demand → Inventory → PO → Dispatch → Receipt → Risk")

# ============================================================
# HELPERS
# ============================================================
def clean_columns(df):
    df = df.copy()
    df.columns = [
        str(c).strip().replace("\n", " ").replace("  ", " ")
        for c in df.columns
    ]
    return df

def read_uploaded(uploaded):
    if uploaded is None:
        return None
    if uploaded.name.lower().endswith(".csv"):
        return clean_columns(pd.read_csv(uploaded))
    return clean_columns(pd.read_excel(uploaded))

def find_col(df, aliases):
    if df is None:
        return None
    lookup = {str(c).strip().lower(): c for c in df.columns}
    # exact first
    for a in aliases:
        if a.lower() in lookup:
            return lookup[a.lower()]
    # then contains
    for a in aliases:
        al = a.lower()
        for c in df.columns:
            if al in str(c).lower():
                return c
    return None

def standardize(df, mapping):
    """Rename source columns into dashboard-standard columns."""
    if df is None:
        return None
    out = df.copy()
    rename = {}
    for target, aliases in mapping.items():
        col = find_col(out, aliases)
        if col:
            rename[col] = target
    out = out.rename(columns=rename)
    return out

def num(df, col, default=0):
    if col not in df.columns:
        df[col] = default
    df[col] = pd.to_numeric(
        df[col].astype(str)
        .str.replace(",", "", regex=False)
        .str.replace("₹", "", regex=False)
        .str.replace("%", "", regex=False)
        .str.strip(),
        errors="coerce",
    ).fillna(default)
    return df

def date_col(df, col):
    if col in df.columns:
        df[col] = pd.to_datetime(df[col], errors="coerce")
    return df

def demo_sources():
    sku = pd.DataFrame([
        ["PPLBFC8903380043464NM1","8903380043464","Faces Canada STAY Oud Till Dawn Eau de Parfum - 20ml","ADF"],
        ["PPLBFC8903380042153","8903380042153","Faces Canada STAY Oud Till Dawn Eau de Parfum - 50ml","ADF"],
        ["PPLBFC8903380042184","8903380042184","Faces Canada STAY Vanilla Past Midnight Eau de Parfum - 50ml","ADF"],
        ["PPLBFC8903380042191","8903380042191","Faces Canada STAY White Moon Light Eau de Parfum - 50ml","ADF"],
        ["PPLBFC8903380043402","8903380043402","Faces Canada Aura Sparkling Ecstacy Eau de Parfum - 100ml","ADF"],
        ["PPLBFC8903380042207","8903380042207","Faces Canada STAY Amber Until Sunset Eau de Parfum - 50ml","ADF"],
        ["PPLBFC8903380042139","8903380042139","Faces Canada Aura Soft Serenity Eau de Parfum - 100ml","ADF"],
        ["PPLBFC8903380043396","8903380043396","Faces Canada Aura Silent Fire Eau de Parfum - 100ml","ADF"],
        ["PPLBFC8903380042115","8903380042115","Faces Canada Aura Romantic Daydreams Eau de Parfum - 100ml","ADF"],
        ["PPLBFC8903380042160","8903380042160","Faces Canada STAY Bloom After Dark Eau de Parfum - 50ml","ADF"],
        ["PPLBFC8903380042177","8903380042177","Faces Canada STAY Sugar After Dusk Eau de Parfum - 50ml","ADF"],
        ["PPLBFC8903380042108","8903380042108","Faces Canada Aura Lovestruck Delight Eau de Parfum - 100ml","ADF"],
        ["PPLBFC8903380043495NM8","8903380043495","Faces Canada STAY Vanilla Past Midnight Eau de Parfum mini - 20ml","ADF"],
        ["PPLBFC8903380042122","8903380042122","Faces Canada Aura Whimsical & Wild Eau de Parfum - 100ml","ADF"],
        ["PPLBFC8903380043518NM1","8903380043518","Faces Canada STAY Amber Until Sunset Eau de Parfum mini - 20ml","ADF"],
        ["PPLBFC8903380043488NM4","8903380043488","Faces Canada STAY Sugar After Dusk Eau de Parfum mini - 20ml","ADF"],
        ["PPLBFC8903380043501NM3","8903380043501","Faces Canada STAY White Moon Light Eau de Parfum mini - 20ml","ADF"],
        ["PPLBFC8903380043471NM9","8903380043471","Faces Canada STAY Bloom After Dark Eau de Parfum mini - 20ml","ADF"],
    ], columns=["SKU Code","EAN","SKU Name","Supplier"])

    rng = np.random.default_rng(7)
    n = len(sku)
    monthly = rng.integers(35000, 140000, n)
    stock = rng.integers(5000, 85000, n)
    open_po = rng.integers(0, 55000, n)
    transit = rng.integers(0, 25000, n)
    lead = rng.integers(30, 121, n)

    demand = sku[["SKU Code","SKU Name","Supplier"]].copy()
    demand["Month"] = "Current"
    demand["Demand Qty"] = monthly

    inv = sku[["SKU Code","SKU Name","Supplier"]].copy()
    inv["FG Stock"] = stock

    po_rows = []
    for i in range(n):
        po_qty = int(open_po[i])
        if po_qty:
            po_rows.append([
                f"PO-{26000+i}", sku.iloc[i]["SKU Code"], sku.iloc[i]["SKU Name"],
                "ADF", pd.Timestamp.today().normalize() - pd.Timedelta(days=int(rng.integers(5,35))),
                pd.Timestamp.today().normalize() + pd.Timedelta(days=int(lead[i])),
                po_qty, int(po_qty*rng.uniform(.2,.9)), int(po_qty*rng.uniform(.0,.5)),
                "Confirmed" if rng.random() > .25 else "At Risk"
            ])
    po = pd.DataFrame(po_rows, columns=[
        "PO Number","SKU Code","SKU Name","Supplier","PO Date","Expected Date",
        "PO Qty","Dispatched Qty","Received Qty","PO Status"
    ])
    return sku, demand, inv, po

# ============================================================
# SOURCE SCHEMAS
# ============================================================
SKU_MAP = {
    "SKU Code": ["SKU Code","SKU","Item Code","Material Code"],
    "EAN": ["EAN","EAN Code","Barcode","EAN/UPC"],
    "SKU Name": ["SKU Name","Name of FG","FG Name","Product Name","Description"],
    "Supplier": ["Supplier","Vendor","Manufacturer","3P Manufacturer"],
}
DEMAND_MAP = {
    "SKU Code": ["SKU Code","SKU","Item Code","Material Code"],
    "SKU Name": ["SKU Name","Name of FG","FG Name","Product Name","Description"],
    "Supplier": ["Supplier","Vendor","Manufacturer","3P Manufacturer"],
    "Demand Qty": ["Demand Qty","Demand","Forecast","Monthly Demand","Requirement","Qty"],
    "Month": ["Month","Demand Month","Forecast Month"],
}
INV_MAP = {
    "SKU Code": ["SKU Code","SKU","Item Code","Material Code"],
    "SKU Name": ["SKU Name","Name of FG","FG Name","Product Name","Description"],
    "Supplier": ["Supplier","Vendor","Manufacturer","3P Manufacturer"],
    "FG Stock": ["FG Stock","Current Stock","Inventory","FG Inventory","Stock Qty","Closing Stock"],
}
PO_MAP = {
    "PO Number": ["PO Number","PO No","PO","Purchase Order","Purchase Order No"],
    "SKU Code": ["SKU Code","SKU","Item Code","Material Code"],
    "SKU Name": ["SKU Name","Name of FG","FG Name","Product Name","Description"],
    "Supplier": ["Supplier","Vendor","Manufacturer","3P Manufacturer"],
    "PO Date": ["PO Date","Order Date","Created Date"],
    "Expected Date": ["Expected Date","Delivery Date","Committed Date","ETA"],
    "PO Qty": ["PO Qty","PO Quantity","Order Qty","Ordered Qty","Quantity"],
    "Dispatched Qty": ["Dispatched Qty","Dispatch Qty","Dispatched","Shipped Qty"],
    "Received Qty": ["Received Qty","GRN Qty","Receipt Qty","Received"],
    "PO Status": ["PO Status","Status","Delivery Status"],
}

# ============================================================
# SIDEBAR DATA INPUT
# ============================================================
st.sidebar.header("1. Data Inputs")
use_demo = st.sidebar.checkbox("Use demo data", value=True)

sku_file = st.sidebar.file_uploader("SKU / EAN Master", type=["xlsx","xls","csv"], key="sku")
demand_file = st.sidebar.file_uploader("Demand / Forecast", type=["xlsx","xls","csv"], key="demand")
inventory_file = st.sidebar.file_uploader("FG Inventory", type=["xlsx","xls","csv"], key="inventory")
po_file = st.sidebar.file_uploader("Open PO / PO Tracker", type=["xlsx","xls","csv"], key="po")

if use_demo or not any([sku_file, demand_file, inventory_file, po_file]):
    sku_raw, demand_raw, inv_raw, po_raw = demo_sources()
    demo_active = True
else:
    sku_raw = read_uploaded(sku_file) if sku_file else None
    demand_raw = read_uploaded(demand_file) if demand_file else None
    inv_raw = read_uploaded(inventory_file) if inventory_file else None
    po_raw = read_uploaded(po_file) if po_file else None
    demo_active = False

sku = standardize(sku_raw, SKU_MAP)
demand = standardize(demand_raw, DEMAND_MAP)
inv = standardize(inv_raw, INV_MAP)
po = standardize(po_raw, PO_MAP)

# ============================================================
# NORMALIZE
# ============================================================
for df, cols in [
    (sku, ["SKU Code","EAN","SKU Name","Supplier"]),
    (demand, ["SKU Code","SKU Name","Supplier"]),
    (inv, ["SKU Code","SKU Name","Supplier"]),
]:
    if df is not None:
        for c in cols:
            if c not in df.columns:
                df[c] = ""

if demand is not None:
    num(demand, "Demand Qty")
if inv is not None:
    num(inv, "FG Stock")

if po is not None:
    for c in ["PO Number","SKU Code","SKU Name","Supplier","PO Status"]:
        if c not in po.columns:
            po[c] = ""
    for c in ["PO Qty","Dispatched Qty","Received Qty"]:
        num(po, c)
    for c in ["PO Date","Expected Date"]:
        date_col(po, c)

# ============================================================
# BUILD SUPPLY MODEL
# ============================================================
if sku is None:
    sku = pd.DataFrame(columns=["SKU Code","EAN","SKU Name","Supplier"])

master = sku[["SKU Code","EAN","SKU Name","Supplier"]].drop_duplicates("SKU Code")

if demand is None:
    demand = master[["SKU Code","SKU Name","Supplier"]].copy()
    demand["Demand Qty"] = 0
else:
    demand = demand.groupby("SKU Code", as_index=False).agg({
        "Demand Qty":"sum",
        "SKU Name":"first",
        "Supplier":"first"
    })

if inv is None:
    inv = master[["SKU Code"]].copy()
    inv["FG Stock"] = 0
else:
    inv = inv.groupby("SKU Code", as_index=False)["FG Stock"].sum()

if po is None:
    po = pd.DataFrame(columns=[
        "PO Number","SKU Code","SKU Name","Supplier","PO Date","Expected Date",
        "PO Qty","Dispatched Qty","Received Qty","PO Status"
    ])

po_summary = po.groupby("SKU Code", as_index=False).agg({
    "PO Qty":"sum",
    "Dispatched Qty":"sum",
    "Received Qty":"sum",
})
po_summary["Open PO Qty"] = (
    po_summary["PO Qty"]
    - po_summary["Dispatched Qty"]
    - po_summary["Received Qty"]
).clip(lower=0)

model = master.merge(
    demand[["SKU Code","Demand Qty"]], on="SKU Code", how="left"
).merge(
    inv[["SKU Code","FG Stock"]], on="SKU Code", how="left"
).merge(
    po_summary[["SKU Code","PO Qty","Dispatched Qty","Received Qty","Open PO Qty"]],
    on="SKU Code", how="left"
)

for c in ["Demand Qty","FG Stock","PO Qty","Dispatched Qty","Received Qty","Open PO Qty"]:
    model[c] = pd.to_numeric(model[c], errors="coerce").fillna(0)

model["Net Supply"] = model["FG Stock"] + model["Open PO Qty"]
model["Supply Gap"] = (model["Demand Qty"] - model["Net Supply"]).clip(lower=0)
model["DOI"] = np.where(
    model["Demand Qty"] > 0,
    model["FG Stock"] / model["Demand Qty"] * 30,
    999
)
model["Projected DOI"] = np.where(
    model["Demand Qty"] > 0,
    model["Net Supply"] / model["Demand Qty"] * 30,
    999
)
model["Status"] = np.select(
    [
        model["Supply Gap"] > model["Demand Qty"] * 0.20,
        model["Supply Gap"] > 0,
        model["DOI"] < 10,
        model["DOI"] > 60,
    ],
    ["Critical","At Risk","Low DOI","Excess"],
    default="Healthy",
)

# ============================================================
# SIDEBAR FILTERS
# ============================================================
st.sidebar.header("2. Filters")
supplier_options = ["All"] + sorted([x for x in model["Supplier"].dropna().astype(str).unique() if x])
status_options = ["All","Critical","At Risk","Low DOI","Healthy","Excess"]

supplier_filter = st.sidebar.selectbox("Supplier", supplier_options)
status_filter = st.sidebar.selectbox("Supply Status", status_options)

view = model.copy()
if supplier_filter != "All":
    view = view[view["Supplier"].astype(str) == supplier_filter]
if status_filter != "All":
    view = view[view["Status"] == status_filter]

# ============================================================
# HEADER / KPI
# ============================================================
if demo_active:
    st.info("🧪 Demo mode is active. Upload your real Demand, Inventory and PO files in the sidebar to switch to live data.")

critical = int((view["Status"] == "Critical").sum())
risk = int(view["Status"].isin(["Critical","At Risk","Low DOI"]).sum())
low_doi = int((view["Status"] == "Low DOI").sum())
open_po_qty = view["Open PO Qty"].sum()
gap = view["Supply Gap"].sum()
stock = view["FG Stock"].sum()
demand_qty = view["Demand Qty"].sum()

k = st.columns(6)
k[0].metric("🔴 Critical SKUs", f"{critical:,}")
k[1].metric("🟠 Risk SKUs", f"{risk:,}")
k[2].metric("🟡 Low DOI", f"{low_doi:,}")
k[3].metric("📈 Demand", f"{demand_qty/100000:.2f} L")
k[4].metric("📦 FG Stock", f"{stock/100000:.2f} L")
k[5].metric("🚨 Supply Gap", f"{gap/1000:.1f} K")

# ============================================================
# TABS
# ============================================================
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🏠 Control Tower",
    "📋 PO Tracker",
    "📦 SKU Supply Plan",
    "🏭 Supplier View",
    "📊 Data & Export",
])

# ============================================================
# TAB 1 CONTROL TOWER
# ============================================================
with tab1:
    st.subheader("Where do I need to act today?")

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("### 🔴 Top Supply Gaps")
        gaps = view[view["Supply Gap"] > 0].sort_values("Supply Gap", ascending=False).head(10)
        if len(gaps):
            st.dataframe(
                gaps[["SKU Name","SKU Code","Supplier","Demand Qty","FG Stock","Open PO Qty","Supply Gap","Status"]],
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Demand Qty": st.column_config.NumberColumn("Demand", format="%,d"),
                    "FG Stock": st.column_config.NumberColumn("FG Stock", format="%,d"),
                    "Open PO Qty": st.column_config.NumberColumn("Open PO", format="%,d"),
                    "Supply Gap": st.column_config.NumberColumn("Gap", format="%,d"),
                },
            )
        else:
            st.success("No supply gaps in the selected view.")

    with c2:
        st.markdown("### ⏱️ Lowest Inventory Coverage")
        doi = view.sort_values("DOI", ascending=True).head(10)
        st.dataframe(
            doi[["SKU Name","SKU Code","Supplier","FG Stock","Demand Qty","DOI","Status"]],
            use_container_width=True,
            hide_index=True,
            column_config={
                "FG Stock": st.column_config.NumberColumn(format="%,d"),
                "Demand Qty": st.column_config.NumberColumn("Demand", format="%,d"),
                "DOI": st.column_config.NumberColumn("DOI", format="%.0f days"),
            },
        )

    st.markdown("### Supply Position")
    chart = view.set_index("SKU Name")[["Demand Qty","FG Stock","Open PO Qty"]].sort_values("Demand Qty", ascending=False).head(15)
    st.bar_chart(chart)

    st.markdown("### Status Mix")
    status_counts = view["Status"].value_counts().reindex(
        ["Critical","At Risk","Low DOI","Healthy","Excess"], fill_value=0
    )
    st.bar_chart(status_counts)

# ============================================================
# TAB 2 PO TRACKER
# ============================================================
with tab2:
    st.subheader("PO Tracker — follow-up list")

    if len(po):
        po_view = po.copy()

        today = pd.Timestamp.today().normalize()
        po_view["Open Qty"] = (
            po_view["PO Qty"] - po_view["Dispatched Qty"] - po_view["Received Qty"]
        ).clip(lower=0)

        po_view["Days to Due"] = (po_view["Expected Date"] - today).dt.days
        po_view["Delay Days"] = np.where(
            (po_view["Open Qty"] > 0) & po_view["Expected Date"].notna() & (po_view["Expected Date"] < today),
            (today - po_view["Expected Date"]).dt.days,
            0,
        )

        po_view["Action"] = np.select(
            [
                po_view["Delay Days"] > 0,
                (po_view["Days to Due"] <= 7) & (po_view["Open Qty"] > 0),
                po_view["Open Qty"] <= 0,
            ],
            ["🚨 Delayed","⚠️ Due within 7 days","✅ Closed"],
            default="🟢 Monitor",
        )

        po_action = st.multiselect(
            "Show PO actions",
            ["🚨 Delayed","⚠️ Due within 7 days","🟢 Monitor","✅ Closed"],
            default=["🚨 Delayed","⚠️ Due within 7 days"],
        )
        pv = po_view[po_view["Action"].isin(po_action)] if po_action else po_view

        p1,p2,p3,p4 = st.columns(4)
        p1.metric("Total POs", f"{len(po_view):,}")
        p2.metric("Open Qty", f"{po_view['Open Qty'].sum():,.0f}")
        p3.metric("Delayed POs", f"{(po_view['Delay Days']>0).sum():,}")
        p4.metric("Due ≤ 7 Days", f"{((po_view['Days to Due']<=7)&(po_view['Open Qty']>0)).sum():,}")

        st.dataframe(
            pv[[
                "PO Number","SKU Code","SKU Name","Supplier","PO Date","Expected Date",
                "PO Qty","Dispatched Qty","Received Qty","Open Qty",
                "Days to Due","Delay Days","PO Status","Action"
            ]].sort_values(["Delay Days","Days to Due"], ascending=[False,True]),
            use_container_width=True,
            hide_index=True,
            column_config={
                "PO Date": st.column_config.DateColumn(format="DD-MMM-YYYY"),
                "Expected Date": st.column_config.DateColumn(format="DD-MMM-YYYY"),
                "PO Qty": st.column_config.NumberColumn(format="%,d"),
                "Dispatched Qty": st.column_config.NumberColumn(format="%,d"),
                "Received Qty": st.column_config.NumberColumn(format="%,d"),
                "Open Qty": st.column_config.NumberColumn(format="%,d"),
            },
        )
    else:
        st.warning("No PO data available. Upload an Open PO / PO Tracker file.")

# ============================================================
# TAB 3 SKU SUPPLY PLAN
# ============================================================
with tab3:
    st.subheader("SKU-level Supply Plan")

    plan = view[[
        "SKU Name","SKU Code","EAN","Supplier",
        "Demand Qty","FG Stock","Open PO Qty","Net Supply",
        "Supply Gap","DOI","Projected DOI","Status"
    ]].copy()

    st.dataframe(
        plan.sort_values(["Supply Gap","DOI"], ascending=[False,True]),
        use_container_width=True,
        hide_index=True,
        column_config={
            "Demand Qty": st.column_config.NumberColumn("Demand", format="%,d"),
            "FG Stock": st.column_config.NumberColumn("FG Stock", format="%,d"),
            "Open PO Qty": st.column_config.NumberColumn("Open PO", format="%,d"),
            "Net Supply": st.column_config.NumberColumn("Net Supply", format="%,d"),
            "Supply Gap": st.column_config.NumberColumn("Supply Gap", format="%,d"),
            "DOI": st.column_config.NumberColumn(format="%.0f days"),
            "Projected DOI": st.column_config.NumberColumn("Projected DOI", format="%.0f days"),
        },
    )

    st.markdown("### SKU Drilldown")
    if len(view):
        selected_sku = st.selectbox("Select SKU", view["SKU Name"].tolist())
        x = view[view["SKU Name"] == selected_sku].iloc[0]

        q = st.columns(6)
        q[0].metric("Demand", f"{x['Demand Qty']:,.0f}")
        q[1].metric("FG Stock", f"{x['FG Stock']:,.0f}")
        q[2].metric("Open PO", f"{x['Open PO Qty']:,.0f}")
        q[3].metric("Net Supply", f"{x['Net Supply']:,.0f}")
        q[4].metric("DOI", f"{x['DOI']:.0f} days")
        q[5].metric("Gap", f"{x['Supply Gap']:,.0f}")

        related_po = po[po["SKU Code"].astype(str) == str(x["SKU Code"])] if len(po) else pd.DataFrame()
        if len(related_po):
            st.markdown("#### Related POs")
            st.dataframe(related_po, use_container_width=True, hide_index=True)

# ============================================================
# TAB 4 SUPPLIER
# ============================================================
with tab4:
    st.subheader("Supplier Performance & Exposure")

    if len(view):
        supplier_summary = view.groupby("Supplier", dropna=False).agg(
            SKUs=("SKU Code","count"),
            Demand=("Demand Qty","sum"),
            FG_Stock=("FG Stock","sum"),
            Open_PO=("Open PO Qty","sum"),
            Supply_Gap=("Supply Gap","sum"),
            Avg_DOI=("DOI","mean"),
        ).reset_index()

        supplier_summary["Risk SKUs"] = (
            view.assign(Risk=view["Status"].isin(["Critical","At Risk","Low DOI"]))
            .groupby("Supplier")["Risk"]
            .sum()
            .reindex(supplier_summary["Supplier"])
            .fillna(0)
            .astype(int)
            .values
        )

        st.dataframe(
            supplier_summary,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Demand": st.column_config.NumberColumn(format="%,d"),
                "FG_Stock": st.column_config.NumberColumn("FG Stock", format="%,d"),
                "Open_PO": st.column_config.NumberColumn("Open PO", format="%,d"),
                "Supply_Gap": st.column_config.NumberColumn("Supply Gap", format="%,d"),
                "Avg_DOI": st.column_config.NumberColumn("Avg DOI", format="%.0f days"),
            },
        )

        l,r = st.columns(2)
        with l:
            st.markdown("### Open PO Exposure by Supplier")
            st.bar_chart(supplier_summary.set_index("Supplier")["Open_PO"])
        with r:
            st.markdown("### Supply Gap by Supplier")
            st.bar_chart(supplier_summary.set_index("Supplier")["Supply_Gap"])

# ============================================================
# TAB 5 DATA & EXPORT
# ============================================================
with tab5:
    st.subheader("Data Quality & Export")

    dq1,dq2,dq3 = st.columns(3)
    dq1.metric("SKU Master Rows", f"{len(master):,}")
    dq2.metric("SKU Rows in Dashboard", f"{len(model):,}")
    dq3.metric("PO Rows", f"{len(po):,}")

    missing = view[view["SKU Code"].astype(str).str.strip() == ""]
    if len(missing):
        st.error(f"{len(missing)} rows have missing SKU Code.")
    else:
        st.success("SKU codes are populated for the current view.")

    st.markdown("### Download")
    export = view.copy()
    csv_bytes = export.to_csv(index=False).encode("utf-8")
    st.download_button(
        "⬇️ Download Supply Plan CSV",
        csv_bytes,
        "FG_Supply_Plan_V2.csv",
        "text/csv",
    )

    # Excel export with multiple sheets
    excel = io.BytesIO()
    with pd.ExcelWriter(excel, engine="openpyxl") as writer:
        view.to_excel(writer, index=False, sheet_name="Supply_Plan")
        po.to_excel(writer, index=False, sheet_name="PO_Tracker")
        master.to_excel(writer, index=False, sheet_name="SKU_Master")
    excel.seek(0)

    st.download_button(
        "⬇️ Download Full Excel Dashboard Data",
        excel,
        "FG_Sourcing_Control_Tower_V2.xlsx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

st.divider()
st.caption("Next enhancement: connect this control tower directly to your invoice OCR output, PO data, inventory snapshot and demand file so the dashboard becomes a single daily sourcing cockpit.")
