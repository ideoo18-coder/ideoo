import os
import time
import schedule
import requests
import pandas as pd
from datetime import datetime
import pytz
import yfinance as yf

# ============================================================
# AYARLAR
# ============================================================
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
# ============================================================

TURKEY_TZ = pytz.timezone("Europe/Istanbul")

BIST_SYMBOLS = [
    "AKBNK.IS", "ARCLK.IS", "ASELS.IS", "BIMAS.IS", "EREGL.IS", "FROTO.IS",
    "GARAN.IS", "HALKB.IS", "ISCTR.IS", "KCHOL.IS", "KOZAL.IS", "KRDMD.IS",
    "MGROS.IS", "PETKM.IS", "PGSUS.IS", "SAHOL.IS", "SISE.IS", "TAVHL.IS",
    "TCELL.IS", "THYAO.IS", "TKFEN.IS", "TOASO.IS", "TSKB.IS", "TTKOM.IS",
    "TUPRS.IS", "ULKER.IS", "VAKBN.IS", "VESTL.IS", "YKBNK.IS", "AEFES.IS",
    "AKSA.IS", "ALARK.IS", "ANACM.IS", "ASUZU.IS", "AYGAZ.IS", "BAGFS.IS",
    "BRISA.IS", "BRYAT.IS", "BUCIM.IS", "CCOLA.IS", "CIMSA.IS", "CLEBI.IS",
    "DEVA.IS", "ECILC.IS", "EKGYO.IS", "ENKAI.IS", "ENJSA.IS", "GUBRF.IS",
    "HEKTS.IS", "ISMEN.IS", "KARSN.IS", "LOGO.IS", "MAVI.IS", "MPARK.IS",
    "NTHOL.IS", "NUHCM.IS", "OTKAR.IS", "OYAKC.IS", "POLTK.IS", "ROYAL.IS",
    "SAFKR.IS", "SANEL.IS", "SARKY.IS", "SOKM.IS", "SODA.IS", "TATGD.IS",
    "TRGYO.IS", "TTRAK.IS", "ZOREN.IS", "ODAS.IS", "SKBNK.IS", "DOHOL.IS",
]


def send_telegram(message):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("HATA: Telegram bilgileri eksik!")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"}
    try:
        r = requests.post(url, json=payload, timeout=10)
        if r.status_code == 200:
            print("Telegram mesaji gonderildi.")
        else:
            print(f"Telegram hatasi: {r.text}")
    except Exception as e:
        print(f"Telegram baglanti hatasi: {e}")


def ema(series, period):
    return series.ewm(span=period, adjust=False).mean()


def rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(com=period - 1, adjust=False).mean()
    avg_loss = loss.ewm(com=period - 1, adjust=False).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def adx_and_di(high, low, close, period=14):
    tr1 = high - low
    tr2 = (high - close.shift()).abs()
    tr3 = (low - close.shift()).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    up = high - high.shift()
    down = low.shift() - low
    plus_dm = up.where((up > down) & (up > 0), 0)
    minus_dm = down.where((down > up) & (down > 0), 0)
    atr = tr.ewm(com=period - 1, adjust=False).mean()
    plus_di = 100 * plus_dm.ewm(com=period - 1, adjust=False).mean() / atr
    minus_di = 100 * minus_dm.ewm(com=period - 1, adjust=False).mean() / atr
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di)
    adx_val = dx.ewm(com=period - 1, adjust=False).mean()
    return adx_val, plus_di, minus_di


def chaikin_money_flow(high, low, close, volume, period=20):
    mfv = ((close - low) - (high - close)) / (high - low) * volume
    cmf = mfv.rolling(period).sum() / volume.rolling(period).sum()
    return cmf


def get_4h_data(ticker):
    df_raw = ticker.history(period="60d", interval="1h")
    if df_raw is None or len(df_raw) < 10:
        return None
    df = df_raw.resample("4h").agg({
        "Open": "first", "High": "max", "Low": "min",
        "Close": "last", "Volume": "sum"
    }).dropna()
    return df


def check_symbol(symbol, interval):
    try:
        ticker = yf.Ticker(symbol)

        if interval == "4h":
            df = get_4h_data(ticker)
        elif interval == "1h":
            df = ticker.history(period="60d", interval="1h")
        elif interval == "2h":
            df_raw = ticker.history(period="60d", interval="1h")
            df = df_raw.resample("2h").agg({
                "Open": "first", "High": "max", "Low": "min",
                "Close": "last", "Volume": "sum"
            }).dropna()
        else:  # 1d
            df = ticker.history(period="1y", interval="1d")

        if df is None or len(df) < 50:
            return None

        close = df["Close"]
        high = df["High"]
        low = df["Low"]
        volume = df["Volume"]

        df1d = ticker.history(period="2y", interval="1d")
        if df1d is None or len(df1d) < 200:
            return None

        ema20 = ema(close, 20)
        ema50 = ema(close, 50)
        ema200_1d = ema(df1d["Close"], 200)

        current_close = close.iloc[-1]

        if current_close <= ema200_1d.iloc[-1]:
            return None
        if ema20.iloc[-1] <= ema50.iloc[-1]:
            return None

        rsi_val = rsi(close).iloc[-1]
        if rsi_val <= 50:
            return None

        adx_val, plus_di, minus_di = adx_and_di(high, low, close)
        if adx_val.iloc[-1] <= 18:
            return None
        if plus_di.iloc[-1] <= minus_di.iloc[-1]:
            return None

        cmf_val = chaikin_money_flow(high, low, close, volume).iloc[-1]
        if cmf_val < 0.04:
            return None

        avg_vol = volume.iloc[-21:-1].mean()
        rel_vol = volume.iloc[-1] / avg_vol if avg_vol > 0 else 0
        if rel_vol < 1.5:
            return None

        if (volume.iloc[-1] * current_close) < 15_000_000:
            return None

        prev_close = close.iloc[-2]
        change_pct = (current_close - prev_close) / prev_close * 100
        if change_pct < -2 or change_pct > 4:
            return None

        # Stop = 4 saatlik EMA20
        df_4h = get_4h_data(ticker)
        if df_4h is not None and len(df_4h) >= 20:
            stop_level = round(ema(df_4h["Close"], 20).iloc[-1], 2)
        else:
            stop_level = round(ema20.iloc[-1], 2)

        return {
            "symbol": symbol.replace(".IS", ""),
            "price": round(current_close, 2),
            "stop": stop_level,
            "change_pct": round(change_pct, 2),
        }

    except Exception as e:
        print(f"  {symbol} hatasi: {e}")
        return None


def run_scan():
    now = datetime.now(TURKEY_TZ)
    print(f"\n{'='*50}")
    print(f"Tarama basliyor: {now.strftime('%d.%m.%Y %H:%M')}")

    if not (10 <= now.hour < 18 or (now.hour == 18 and now.minute <= 30)):
        print("Borsa kapali, tarama atlaniyor.")
        return

    timeframes = {"1S": "1h", "2S": "2h", "4S": "4h", "1G": "1d"}
    all_results = {}

    for tf_label, tf_interval in timeframes.items():
        results = []
        print(f"\n[{tf_label}] Taraniyor...")
        for symbol in BIST_SYMBOLS:
            result = check_symbol(symbol, tf_interval)
            if result:
                results.append(result)
                print(f"  OK: {result['symbol']}")
            time.sleep(0.5)
        all_results[tf_label] = results

    send_scan_results(all_results, now)


def send_scan_results(results, scan_time):
    time_str = scan_time.strftime("%d.%m.%Y %H:%M")
    total = sum(len(v) for v in results.values())

    if total == 0:
        msg = f"BIST Tarama - {time_str}\n\nHicbir hisse filtreleri gecemedi."
        send_telegram(msg)
        return

    msg = f"BIST Tarama Sonuclari\n{time_str}\n\n"

    for tf_label, stocks in results.items():
        if not stocks:
            continue
        msg += f"[{tf_label}] {len(stocks)} hisse\n"
        for s in stocks:
            msg += f"{s['symbol']} | Fiyat: {s['price']} TL | Stop: {s['stop']} TL\n"
        msg += "\n"

    msg += f"Toplam: {total} hisse"
    send_telegram(msg)


def main():
    print("BIST Tarama Botu Baslatildi!")
    run_scan()
    schedule.every(15).minutes.do(run_scan)
    while True:
        schedule.run_pending()
        time.sleep(30)


if __name__ == "__main__":
    main()
