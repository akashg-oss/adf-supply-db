import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime

st.set_page_config(page_title="FG Supply & Sourcing Dashboard", page_icon="📦", layout="wide")

st.markdown("""
<style>
.block-container {padding-top:1.2rem}
.kpi {background:#fff;border:1px solid #e5e7eb;border-radius:12px;padding:14px;min-height:100px}
.kpi-label {font-size:12px;color:#6b7280}
.kpi-value {font-size:25px;font-weight:700;color:#20242b;margin-top:5px}
.section {font-size:19px;font-weight:700;margin:18px 0 10px}
</style>
""", unsafe_allow_html=True)

# ---------- DEMO DATA ----------
def demo_data():
    rows = [
        ["STAY Oud Till Dawn 50ml","PPLBFC8903380042153","ADF","West",125000,42000,48000,24000,28,120,95,92,520],
        ["STAY Vanilla Past Midnight 50ml","PPLBFC8903380042184","ADF","West",112000,65000,48000,12000,34,110,96,95,500],
        ["STAY White Moon Light 50ml","PPLBFC8903380042191","ADF","West",98000,21000,25000,0,14,80,88,86,510],
        ["Aura Sparkling Ecstasy 100ml","PPLBFC8903380043402","ADF","North",82000,35000,18000,9000,20,75,91,90,850],
        ["Aura Whimsical & Wild 100ml","PPLBFC8903380042122","ADF","North",74000,12000,20000,8000,16,90,94,93,830],
        ["Aura Romantic Daydreams 100ml","PPLBFC8903380042115","ADF","North",105000,78000,12000,5000,31,60,97,96,820],
        ["Aura Lovestruck Delight 100ml","PPLBFC8903380043396","ADF","South",118000,18000,22000,7000,12,90,89,88,840],
        ["STAY Amber Until Sunset 50ml","PPLBFC8903380042207","ADF","South",95000,55000,35000,10000,32,105,93,91,520],
        ["STAY Sugar After Dusk 50ml","PPLBFC8903380042177","ADF","West",68000,16000,40000,15000,31,115,95,94,505],
        ["Aura Lovestruck Delight Mini 20ml","PPLBFC8903380043495","ADF","South",45000,8000,15000,4000,18,85,87,85,310],
        ["Aura Silent Fire 100ml","PPLBFC8903380043396","ADF","North",56000,31000,5000,0,19,65,98,97,800],
        ["STAY Bloom After Dark 20ml","PPLBFC8903380043471","ADF","West",39000,6000,12000,2000,15,70,90,89,305],
    ]
    c=["SKU Name","SKU Code","Supplier","Region","Monthly Demand","FG Stock","Open PO",
       "In Transit","DOI","Lead Time","OTIF","Fill Rate","Unit Cost"]
    d=pd.DataFrame(rows,columns=c)
    d["Net Available"]=d["FG Stock"]+d["Open PO"]+d["In Transit"]
    d["Gap"]=d["Monthly Demand"]-d["Net Available"]
    d["Coverage"]=np.where(d["Monthly Demand"]>0,d["Net Available"]/d["Monthly Demand"]*30,0)
    d["PO Value"]=d["Open PO"]*d["Unit Cost"]
    d["Status"]=np.select(
        [d["Gap"]>d["Monthly Demand"]*.10,d["Gap"]>0,d["DOI"]>60],
        ["Critical","At Risk","Excess"],default="Healthy")
    return d

def load_file(f):
    raw=pd.read_csv(f) if f.name.lower().endswith(".csv") else pd.read_excel(f)
    raw.columns=[str(x).strip() for x in raw.columns]
    aliases={
        "SKU Name":["SKU Name","FG Name","Name of FG","Product","Product Name"],
        "SKU Code":["SKU Code","SKU"],
        "Supplier":["Supplier","Vendor","Manufacturer","3P Manufacturer"],
        "Region":["Region","Zone"],
        "Monthly Demand":["Monthly Demand","Demand","Forecast","Monthly Forecast"],
        "FG Stock":["FG Stock","Stock","Current Stock","FG Inventory"],
        "Open PO":["Open PO","Open PO Qty","Open PO Quantity"],
        "In Transit":["In Transit","Transit","In-Transit"],
        "DOI":["DOI","Days of Inventory","Days Inventory"],
        "Lead Time":["Lead Time","Lead Time Days"],
        "OTIF":["OTIF","OTIF %"],
        "Fill Rate":["Fill Rate","Fill Rate %"],
        "Unit Cost":["Unit Cost","Price","FG Price","Price/PCS"],
    }
    rename={}
    lookup={str(x).lower():x for x in raw.columns}
    for target,opts in aliases.items():
        for o in opts:
            if o.lower() in lookup:
                rename[lookup[o.lower()]]=target
                break
    d=raw.rename(columns=rename).copy()
    for c in ["SKU Name","SKU Code","Supplier","Region"]:
        if c not in d: d[c]=""
    for c in ["Monthly Demand","FG Stock","Open PO","In Transit","DOI","Lead Time","OTIF","Fill Rate","Unit Cost"]:
        if c not in d: d[c]=0
        d[c]=pd.to_numeric(d[c].astype(str).str.replace(",","").str.replace("%",""),errors="coerce").fillna(0)
    d["Net Available"]=d["FG Stock"]+d["Open PO"]+d["In Transit"]
    d["Gap"]=d["Monthly Demand"]-d["Net Available"]
    d["Coverage"]=np.where(d["Monthly Demand"]>0,d["Net Available"]/d["Monthly Demand"]*30,0)
    d["PO Value"]=d["Open PO"]*d["Unit Cost"]
    d["Status"]=np.select(
        [d["Gap"]>d["Monthly Demand"]*.10,d["Gap"]>0,d["DOI"]>60],
        ["Critical","At Risk","Excess"],default="Healthy")
    return d

# ---------- SIDEBAR ----------
st.sidebar.title("📦 FG Sourcing Control Tower")
file=st.sidebar.file_uploader("Upload sourcing data (optional)",type=["xlsx","xls","csv"])
if file:
    try:
        df=load_file(file)
        st.sidebar.success(f"{len(df):,} SKU rows loaded")
    except Exception as e:
        st.sidebar.error(f"File error: {e}")
        df=demo_data()
else:
    df=demo_data()
    st.sidebar.info("Demo data is active. Upload your real sourcing file when ready.")

suppliers=["All"]+sorted(df["Supplier"].astype(str).replace("nan","").unique().tolist())
regions=["All"]+sorted(df["Region"].astype(str).replace("nan","").unique().tolist())
statuses=["All","Critical","At Risk","Healthy","Excess"]
supplier=st.sidebar.selectbox("Supplier",suppliers)
region=st.sidebar.selectbox("Region",regions)
status=st.sidebar.selectbox("Supply Status",statuses)

v=df.copy()
if supplier!="All": v=v[v.Supplier==supplier]
if region!="All": v=v[v.Region==region]
if status!="All": v=v[v.Status==status]

# ---------- HEADER ----------
st.title("FG Supply & Sourcing Dashboard")
st.caption(f"Supply control tower • Refreshed {datetime.now().strftime('%d %b %Y, %H:%M')}")

critical=(v.Status=="Critical").sum()
risk=v.Status.isin(["Critical","At Risk"]).sum()
low_doi=(v.DOI<10).sum()
excess=(v.Status=="Excess").sum()

a,b,c,d=st.columns(4)
a.metric("🔴 Critical SKUs",f"{critical}","Immediate sourcing action")
b.metric("🟠 Risk SKUs",f"{risk}","Critical + At Risk")
c.metric("🟡 Low DOI",f"{low_doi}","Less than 10 days")
d.metric("🔵 Excess SKUs",f"{excess}",">60 days")

st.markdown('<div class="section">Executive Overview</div>',unsafe_allow_html=True)
vals=[
("Monthly Demand",f"{v['Monthly Demand'].sum()/100000:.2f} L","units"),
("FG Inventory",f"{v['FG Stock'].sum()/100000:.2f} L","on hand"),
("Open PO",f"{v['Open PO'].sum()/100000:.2f} L","to be received"),
("In Transit",f"{v['In Transit'].sum()/100000:.2f} L","on the way"),
("Supply Gap",f"{v['Gap'].clip(lower=0).sum()/1000:.1f} K","additional sourcing"),
("Open PO Value",f"₹{v['PO Value'].sum()/10000000:.2f} Cr","approx."),
("Supplier OTIF",f"{v['OTIF'].mean():.1f}%","delivery performance"),
("Fill Rate",f"{v['Fill Rate'].mean():.1f}%","supply fulfillment"),
]
cc=st.columns(8)
for col,(lab,val,sub) in zip(cc,vals):
    col.markdown(f'<div class="kpi"><div class="kpi-label">{lab}</div><div class="kpi-value">{val}</div><div class="kpi-label">{sub}</div></div>',unsafe_allow_html=True)

# ---------- SUPPLY PLAN ----------
st.markdown('<div class="section">Supply Plan — What needs action?</div>',unsafe_allow_html=True)
plan=v[["SKU Name","SKU Code","Supplier","Monthly Demand","FG Stock","Open PO","In Transit","Net Available","Gap","Coverage","DOI","Status"]].copy()
plan=plan.sort_values(["Gap","DOI"],ascending=[False,True])
st.dataframe(plan,use_container_width=True,hide_index=True,column_config={
    "Monthly Demand":st.column_config.NumberColumn("Demand",format="%,d"),
    "FG Stock":st.column_config.NumberColumn("FG Stock",format="%,d"),
    "Open PO":st.column_config.NumberColumn("Open PO",format="%,d"),
    "In Transit":st.column_config.NumberColumn("In Transit",format="%,d"),
    "Net Available":st.column_config.NumberColumn("Net Available",format="%,d"),
    "Gap":st.column_config.NumberColumn("Gap",format="%,d"),
    "Coverage":st.column_config.NumberColumn("Coverage",format="%.0f days"),
    "DOI":st.column_config.NumberColumn("DOI",format="%.0f days"),
})

# ---------- CHARTS ----------
l,r=st.columns(2)
with l:
    st.markdown('<div class="section">Demand vs Net Supply</div>',unsafe_allow_html=True)
    st.bar_chart(v.set_index("SKU Name")[["Monthly Demand","Net Available"]])
with r:
    st.markdown('<div class="section">Supply Status</div>',unsafe_allow_html=True)
    st.bar_chart(v.Status.value_counts().reindex(["Critical","At Risk","Healthy","Excess"],fill_value=0))

# ---------- SUPPLIER ----------
st.markdown('<div class="section">Supplier Performance</div>',unsafe_allow_html=True)
ss=v.groupby("Supplier").agg(
    SKUs=("SKU Name","count"),Demand=("Monthly Demand","sum"),Open_PO=("Open PO","sum"),
    OTIF=("OTIF","mean"),Fill_Rate=("Fill Rate","mean"),Avg_DOI=("DOI","mean")
).reset_index()
ss["Risk SKUs"]=v.groupby("Supplier")["Status"].apply(lambda x:x.isin(["Critical","At Risk"]).sum()).reindex(ss.Supplier).fillna(0).values
st.dataframe(ss,use_container_width=True,hide_index=True,column_config={
    "Demand":st.column_config.NumberColumn(format="%,d"),
    "Open_PO":st.column_config.NumberColumn("Open PO",format="%,d"),
    "OTIF":st.column_config.NumberColumn(format="%.1f%%"),
    "Fill_Rate":st.column_config.NumberColumn("Fill Rate",format="%.1f%%"),
    "Avg_DOI":st.column_config.NumberColumn("Avg DOI",format="%.0f"),
})

# ---------- ALERTS ----------
st.markdown('<div class="section">🚨 Alerts & Exceptions</div>',unsafe_allow_html=True)
alerts=[]
for _,x in v[v.Status=="Critical"].sort_values("Gap",ascending=False).head(5).iterrows():
    alerts.append(f"🔴 **{x['SKU Name']}** — supply gap {max(x.Gap,0):,.0f} units. Raise / expedite PO.")
for _,x in v[v.DOI<10].sort_values("DOI").head(5).iterrows():
    alerts.append(f"🟠 **{x['SKU Name']}** — only {x.DOI:.0f} days inventory coverage.")
for _,x in v[v.Status=="Excess"].sort_values("DOI",ascending=False).head(5).iterrows():
    alerts.append(f"🔵 **{x['SKU Name']}** — {x.DOI:.0f} days inventory. Review future PO / demand.")
if alerts:
    for x in alerts: st.info(x)
else: st.success("No major exceptions in the selected view.")

# ---------- SKU DRILLDOWN ----------
st.markdown('<div class="section">SKU Drilldown</div>',unsafe_allow_html=True)
if len(v):
    sku=st.selectbox("Select SKU",v["SKU Name"].tolist())
    x=v[v["SKU Name"]==sku].iloc[0]
    q=st.columns(5)
    q[0].metric("FG Stock",f"{x['FG Stock']:,.0f}")
    q[1].metric("Open PO",f"{x['Open PO']:,.0f}")
    q[2].metric("In Transit",f"{x['In Transit']:,.0f}")
    q[3].metric("Coverage",f"{x['Coverage']:.0f} days")
    q[4].metric("Supply Gap",f"{max(x['Gap'],0):,.0f}")
    detail=pd.DataFrame({
        "Attribute":["SKU Code","Supplier","Region","Monthly Demand","Lead Time","OTIF","Fill Rate","Unit Cost","Status"],
        "Value":[x["SKU Code"],x["Supplier"],x["Region"],f"{x['Monthly Demand']:,.0f}",f"{x['Lead Time']:.0f} days",
                 f"{x['OTIF']:.1f}%",f"{x['Fill Rate']:.1f}%",f"₹{x['Unit Cost']:,.0f}",x["Status"]]
    })
    st.dataframe(detail,use_container_width=True,hide_index=True)

# ---------- EXPORT ----------
st.markdown('<div class="section">Export</div>',unsafe_allow_html=True)
st.download_button("⬇️ Download Current View",v.to_csv(index=False).encode("utf-8"),
                   "FG_Supply_Sourcing_Current_View.csv","text/csv")
st.caption("Prototype: demo data is included. The next version can connect PO, inventory, demand and supplier files separately.")
