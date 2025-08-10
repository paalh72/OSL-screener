import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import ta
import matplotlib.pyplot as plt

st.set_page_config(page_title="RSI Screener - Oslo Børs", layout="wide")

# --- Hent tickers fra CSV i GitHub (bytt ut DITT_GITHUB_BRUKERNAVN)
@st.cache_data
def hent_oslo_tickers():
    try:
        url = "https://raw.githubusercontent.com/DITT_GITHUB_BRUKERNAVN/OSL-screener/main/oslo_tickers.csv"
        df = pd.read_csv(url)
        tickers = [f"{t.strip()}.OL" for t in df["Ticker"].dropna().unique()]
        return tickers
    except Exception as e:
        st.warning(f"Kunne ikke hente tickers fra nett, bruker fallback. ({e})")
        return ["EQNR.OL", "NHY.OL", "MOWI.OL", "ORK.OL", "TEL.OL"]

oslo_tickers = hent_oslo_tickers()

st.title("📈 RSI Screener – Oslo Børs (OSL-screener)")
st.markdown("Analyserer 5 års historikk for RSI-svinger mellom 20 og 70.")

# --- Brukerparametere
min_swings = st.sidebar.number_input("Minste antall RSI-svinger (20 ↔ 70)", 1, 200, 10)
min_gain = st.sidebar.number_input("Min. kursøkning (%) mellom RSI 20 → 70", 1, 100, 10)
min_success_rate = st.sidebar.number_input("Min. suksessandel (%)", 0, 100, 50)
min_volume = st.sidebar.number_input("Min. snittvolum", 0, 50_000_000, 100_000)

st.sidebar.markdown("---")
st.sidebar.write("Antall tickers i liste: " + str(len(oslo_tickers)))

# --- Resultater
results = []

progress_bar = st.progress(0)
status_text = st.empty()

for i, ticker in enumerate(oslo_tickers):
    progress_bar.progress((i+1)/len(oslo_tickers))
    status_text.text(f"Henter og analyserer {ticker} ...")

    try:
        df = yf.download(ticker, period="5y", interval="1d", progress=False)
        if df.empty:
            continue

        df = df.dropna(subset=["Close", "Volume"])
        if df.empty:
            continue

        # Volumfilter
        if df['Volume'].mean() < min_volume:
            continue

        # RSI beregning (14)
        df['RSI'] = ta.momentum.RSIIndicator(df['Close'], window=14).rsi()

        last_rsi20_price = None
        successes = 0
        total_swings = 0

        # Finn hver sekvens: fall til <=20, deretter opp til >=70
        for idx in range(1, len(df)):
            prev_rsi = df['RSI'].iloc[idx-1]
            curr_rsi = df['RSI'].iloc[idx]
            # Registrer pris når RSI går under eller lik 20
            if prev_rsi > 20 and curr_rsi <= 20:
                last_rsi20_price = df['Close'].iloc[idx]
            # Når vi senere når 70 eller mer, sjekk gain
            if last_rsi20_price is not None and prev_rsi < 70 and curr_rsi >= 70:
                total_swings += 1
                gain_pct = (df['Close'].iloc[idx] - last_rsi20_price) / last_rsi20_price * 100
                if gain_pct >= min_gain:
                    successes += 1
                last_rsi20_price = None

        if total_swings >= min_swings:
            success_rate = (successes / total_swings * 100) if total_swings else 0
            if success_rate >= min_success_rate:
                results.append({
                    "Ticker": ticker,
                    "Svinger": total_swings,
                    "Suksessrate (%)": round(success_rate, 2),
                    "Ganger oppfylt": successes,
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

    ticker_choice = st.selectbox("Velg aksje for graf", df_results["Ticker"])
    if ticker_choice:
        df = yf.download(ticker_choice, period="5y", interval="1d", progress=False)
        df = df.dropna(subset=["Close", "Volume"])
        df['RSI'] = ta.momentum.RSIIndicator(df['Close'], window=14).rsi()

        fig, ax1 = plt.subplots(figsize=(12,6))
        ax1.set_title(f"{ticker_choice} – Kurs og volum (5 år)")
        ax1.plot(df.index, df['Close'], label="Kurs")
        ax1.set_ylabel("Pris")
        ax1.legend(loc="upper left")

        ax2 = ax1.twinx()
        ax2.bar(df.index, df['Volume'], alpha=0.3)
        ax2.set_ylabel("Volum")

        st.pyplot(fig)

        fig2, ax3 = plt.subplots(figsize=(12,3))
        ax3.plot(df.index, df['RSI'], label="RSI")
        ax3.axhline(70, linestyle="--")
        ax3.axhline(20, linestyle="--")
        ax3.set_ylabel("RSI")
        st.pyplot(fig2)

else:
    st.warning("Ingen aksjer matcher kriteriene.")
