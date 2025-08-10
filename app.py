import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import ta
import time
import matplotlib.pyplot as plt

st.set_page_config(page_title="RSI Screener - Oslo Børs", layout="wide")

# --- TICKERS FRA OSLO BØRS (eksempel-liste, kan utvides)
oslo_tickers = [
    "EQNR.OL", "NHY.OL", "MOWI.OL", "ORK.OL", "TEL.OL",
    "KID.OL", "SALM.OL", "AKRBP.OL", "YAR.OL", "ODL.OL"
]

st.title("📈 RSI Screener – Oslo Børs")
st.markdown("Analyserer 5 års historikk for RSI-svinger mellom 20 og 70.")

# --- Brukerparametere
min_swings = st.sidebar.number_input("Minste antall RSI-svinger (20 ↔ 70)", 5, 50, 10)
min_gain = st.sidebar.number_input("Min. kursøkning (%) mellom RSI 20 → 70", 1, 50, 10)
min_success_rate = st.sidebar.number_input("Min. suksessandel (%)", 10, 100, 50)
min_volume = st.sidebar.number_input("Min. snittvolum", 0, 10_000_000, 100_000)

# --- Resultater
results = []

progress_bar = st.progress(0)
status_text = st.empty()

for i, ticker in enumerate(oslo_tickers):
    progress_bar.progress((i+1)/len(oslo_tickers))
    status_text.text(f"Henter og analyserer {ticker} ...")

    try:
        df = yf.download(ticker, period="5y", interval="1d")
        if df.empty:
            continue

        df.dropna(inplace=True)

        # Volumfilter
        if df['Volume'].mean() < min_volume:
            continue

        # RSI beregning
        rsi = ta.momentum.RSIIndicator(df['Close'], window=14).rsi()
        df['RSI'] = rsi

        # Finn svinger mellom RSI 20 og 70
        swing_points = []
        last_rsi20_price = None
        successes = 0
        total_swings = 0

        for idx in range(1, len(df)):
            if df['RSI'].iloc[idx-1] > 20 and df['RSI'].iloc[idx] <= 20:
                last_rsi20_price = df['Close'].iloc[idx]
            if last_rsi20_price and df['RSI'].iloc[idx-1] < 70 and df['RSI'].iloc[idx] >= 70:
                total_swings += 1
                gain_pct = (df['Close'].iloc[idx] - last_rsi20_price) / last_rsi20_price * 100
                if gain_pct >= min_gain:
                    successes += 1
                last_rsi20_price = None

        if total_swings >= min_swings:
            success_rate = successes / total_swings * 100 if total_swings else 0
            if success_rate >= min_success_rate:
                results.append({
                    "Ticker": ticker,
                    "Svinger": total_swings,
                    "Suksessrate (%)": round(success_rate, 2),
                    "Snittvolum": int(df['Volume'].mean())
                })

    except Exception as e:
        st.error(f"Feil for {ticker}: {e}")

progress_bar.empty()
status_text.text("Analyse ferdig.")

# --- Vis resultater
if results:
    df_results = pd.DataFrame(results).sort_values(by="Suksessrate (%)", ascending=False)
    st.subheader("Aksjer som matcher kriteriene")
    st.dataframe(df_results)

    # Klikk for å se graf
    ticker_choice = st.selectbox("Velg aksje for graf", df_results["Ticker"])
    if ticker_choice:
        df = yf.download(ticker_choice, period="5y", interval="1d")
        df['RSI'] = ta.momentum.RSIIndicator(df['Close'], window=14).rsi()

        fig, ax1 = plt.subplots(figsize=(12,6))
        ax1.set_title(f"{ticker_choice} – Kurs og volum")
        ax1.plot(df.index, df['Close'], label="Kurs", color="blue")
        ax1.set_ylabel("Pris", color="blue")
        ax1.tick_params(axis='y', labelcolor="blue")

        ax2 = ax1.twinx()
        ax2.bar(df.index, df['Volume'], alpha=0.3, color="gray")
        ax2.set_ylabel("Volum", color="gray")
        ax2.tick_params(axis='y', labelcolor="gray")

        st.pyplot(fig)

        # RSI-plot
        fig2, ax3 = plt.subplots(figsize=(12,3))
        ax3.plot(df.index, df['RSI'], label="RSI", color="purple")
        ax3.axhline(70, color="red", linestyle="--")
        ax3.axhline(20, color="green", linestyle="--")
        ax3.set_ylabel("RSI")
        st.pyplot(fig2)

else:
    st.warning("Ingen aksjer matcher kriteriene.")
