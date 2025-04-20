import streamlit as st
import pandas as pd
import requests
import time
import altair as alt
from datetime import datetime

# ===== FUNCTION: ดึงข้อมูลจาก SET API =====
def get_set_financial_data(symbol):
    url = f"https://www.set.or.th/api/set/stock/{symbol}/financial-highlight"
    headers = {
        "User-Agent": "Mozilla/5.0"
    }
    res = requests.get(url, headers=headers)
    if res.status_code != 200:
        return None

    data = res.json()
    return {
        "symbol": symbol,
        "price": float(data.get("lastPrice", 0)),
        "div_yield": float(data.get("dividendYield", 0)),
        "eps": float(data.get("eps", 0)),
        "roe": float(data.get("roe", 0)),
        "dps": float(data.get("dps", 0)),
        "pe": float(data.get("pe", 0)),
        "high_52w": float(data.get("fiftyTwoWeekHigh", 0)),
        "low_52w": float(data.get("fiftyTwoWeekLow", 0)),
        "market_cap": float(data.get("marketCap", 0))
    }

# ===== โหลดรายชื่อหุ้นทั้งหมดใน SET =====
def load_all_symbols():
    url = "https://www.set.or.th/dat/eod/listedcompany/static/listedCompanies_th_TH.xlsx"
    df = pd.read_excel(url, skiprows=1)
    return df['หลักทรัพย์'].dropna().unique().tolist()

symbols = load_all_symbols()
data = []

st.set_page_config(page_title="Dividend Stock Dashboard", layout="wide")
st.title("📈 Dividend & Value Stock Dashboard")

st.markdown("""
แสดงหุ้นที่มีทั้ง **ปันผลเด่น** และ **กำไรมั่นคง** พร้อมเปรียบเทียบราคาปัจจุบันกับราคาที่เหมาะสม (Fair Price)
""")

st.info(f"กำลังโหลดข้อมูลหุ้นทั้งหมดใน SET ({len(symbols)} ตัว)... โปรดรอสักครู่")

# ===== ดึงข้อมูลหุ้นทั้งหมดแบบ loop =====
for i, sym in enumerate(symbols):
    info = get_set_financial_data(sym)
    if info:
        data.append(info)
    time.sleep(0.8)  # ป้องกัน block
    if i % 20 == 0:
        st.write(f"📊 โหลดแล้ว {i}/{len(symbols)} ตัว")

# ===== คำนวณราคาที่ควรซื้อ =====
def calc_fair_price_ddm(dps, r=0.09, g=0.03):
    return dps / (r - g) if r > g else 0

def calc_fair_price_pe(eps, pe_avg=12):
    return eps * pe_avg

# ===== แสดงผล Dashboard =====
df = pd.DataFrame(data)
df["fair_price_ddm"] = df["dps"].apply(lambda x: round(calc_fair_price_ddm(x), 2))
df["fair_price_pe"] = df["eps"].apply(lambda x: round(calc_fair_price_pe(x), 2))
df["status"] = df.apply(lambda row: "✅ น่าซื้อ" if row["price"] < min(row["fair_price_ddm"], row["fair_price_pe"]) else "⛔️ ยังไม่คุ้ม", axis=1)

# ===== ตัวกรอง =====
st.sidebar.header("🔎 ตัวกรองหุ้น")
div_yield_min = st.sidebar.slider("Dividend Yield ขั้นต่ำ (%)", 0.0, 10.0, 4.0, 0.1)
roe_min = st.sidebar.slider("ROE ขั้นต่ำ (%)", 0.0, 20.0, 8.0, 0.5)
pe_max = st.sidebar.slider("P/E ไม่เกิน", 0.0, 30.0, 15.0, 0.5)
market_cap_min = st.sidebar.number_input("Market Cap ขั้นต่ำ (ล้านบาท)", value=10000.0)
price_range = st.sidebar.slider("ช่วงราคาหุ้น (บาท)", 0.0, 500.0, (10.0, 200.0), 1.0)

filtered_df = df[(df["div_yield"] >= div_yield_min) &
                 (df["roe"] >= roe_min) &
                 (df["pe"] <= pe_max) &
                 (df["market_cap"] >= market_cap_min) &
                 (df["price"] >= price_range[0]) &
                 (df["price"] <= price_range[1])]

st.dataframe(filtered_df.style.format({
    "price": "{:.2f}",
    "div_yield": "{:.1f}%",
    "eps": "{:.2f}",
    "roe": "{:.1f}%",
    "dps": "{:.2f}",
    "fair_price_ddm": "{:.2f}",
    "fair_price_pe": "{:.2f}",
    "market_cap": "{:.0f}",
    "high_52w": "{:.2f}",
    "low_52w": "{:.2f}"
}).applymap(lambda x: "color: green" if isinstance(x, str) and "น่าซื้อ" in x else ""))

# ===== แสดงกราฟเปรียบเทียบราคาปัจจุบันกับราคาที่ควรซื้อ =====
st.subheader("📊 เปรียบเทียบราคาหุ้น vs ราคาที่เหมาะสม")
if not filtered_df.empty:
    chart_df = filtered_df.melt(id_vars=["symbol"], value_vars=["price", "fair_price_ddm", "fair_price_pe"],
                                var_name="ประเภทราคา", value_name="มูลค่า")
    chart = alt.Chart(chart_df).mark_bar().encode(
        x=alt.X('symbol:N', title='หุ้น'),
        y=alt.Y('มูลค่า:Q', title='ราคา (บาท)'),
        color='ประเภทราคา:N',
        tooltip=['symbol', 'ประเภทราคา', 'มูลค่า']
    ).properties(
        width=800,
        height=400
    )
    st.altair_chart(chart, use_container_width=True)
else:
    st.info("ไม่พบหุ้นที่ตรงตามเงื่อนไข")

# ===== ดาวน์โหลดไฟล์ Excel รายวัน =====
st.subheader("📥 ดาวน์โหลดไฟล์หุ้นที่น่าซื้อวันนี้")
today = datetime.now().strftime("%Y-%m-%d")
st.download_button(
    label="📁 ดาวน์โหลดไฟล์ Excel",
    data=filtered_df.to_excel(index=False),
    file_name=f"หุ้นปันผล_{today}.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)

st.caption("Developed by AI x นักลงทุนสายปันผล")
