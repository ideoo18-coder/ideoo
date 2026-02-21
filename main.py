import os
import time
import schedule
import requests
import pandas as pd
from datetime import datetime
import pytz
from tvDatafeed import TvDatafeed, Interval

# ============================================================
# AYARLAR - Buraya kendi bilgilerini gir
# ============================================================
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
TV_USERNAME = os.environ.get("TV_USERNAME", "")   # TradingView kullanıcı adı (opsiyonel)
TV_PASSWORD = os.environ.get("TV_PASSWORD", "")   # TradingView şifre (opsiyonel)
# ============================================================

TURKEY_TZ = pytz.timezone("Europe/Istanbul")

# BIST hisseleri listesi (en likit 100+)
BIST_SYMBOLS = [
    "AKBNK", "ARCLK", "ASELS", "BIMAS", "DOHOL", "EREGL", "FROTO", "GARAN",
    "GUBRF", "HALKB", "ISCTR", "KCHOL", "KOZAA", "KOZAL", "KRDMD", "MGROS",
    "ODAS", "PETKM", "PGSUS", "SAHOL", "SISE", "SKBNK", "SODA", "TAVHL",
    "TCELL", "THYAO", "TKFEN", "TOASO", "TSKB", "TTKOM", "TUPRS", "ULKER",
    "VAKBN", "VESTL", "YKBNK", "ZOREN", "AEFES", "AGESA", "AKSA", "ALARK",
    "ALBRK", "ALFAS", "ALGYO", "ALKIM", "ALTNY", "ANACM", "ARASE", "ARDYZ",
    "ARSAN", "ARZUM", "ASUZU", "ATAKP", "ATATP", "AYGAZ", "BAGFS", "BAKAB",
    "BANVT", "BERA", "BFREN", "BIENY", "BRISA", "BRSAN", "BRYAT", "BUCIM",
    "BURCE", "BURVA", "BTCIM", "CANTE", "CCOLA", "CEMTS", "CIMSA", "CLEBI",
    "CWENE", "DESA", "DEVA", "DNISI", "DYOBY", "ECILC", "EGEEN", "EKGYO",
    "EMKEL", "ENKAI", "ENJSA", "ENTRA", "EPLAS", "ERBOS", "EREGL", "ESCOM",
    "EUPWR", "EUREN", "FENER", "FLAP", "FMIZP", "FONET", "FORMT", "GARAN",
    "GLYHO", "GSDHO", "GSRAY", "HEKTS", "HLGYO", "HRKET", "HTTBT", "HUNER",
    "ICBCT", "IHLGM", "ISGSY", "ISMEN", "ITTFH", "IZFAS", "IZINV", "JANTS",
    "KARSN", "KCAER", "KERVT", "KLNMA", "KLRHO", "KNFRT", "KONYA", "KOPOL",
    "KORDS", "KTLEV", "KUTPO", "LIDER", "LINK", "LOGO", "LRSHO", "LUKSK",
    "MAGEN", "MAKIM", "MAKTK", "MAVI", "MEDTR", "MEPET", "MERIT", "MIATK",
    "MPARK", "NATEN", "NETAS", "NTGAZ", "NTHOL", "NUGYO", "NUHCM", "OBAMS",
    "OBASE", "OFSYM", "ONCSM", "ORCAY", "ORGE", "ORION", "OSTIM", "OTKAR",
    "OYAKC", "OYYAT", "PAMEL", "PAPIL", "PARSN", "PASEU", "PCILT", "PENGD",
    "PKENT", "PLTUR", "POLTK", "POLHO", "PRTAS", "PSDTC", "QUAGR", "RALYH",
    "RAYSG", "RHEAG", "RODRG", "ROYAL", "RTALB", "RUBNS", "RYGYO", "SAFKR",
    "SANFM", "SANEL", "SARAC", "SARKY", "SEKFK", "SELEC", "SELGD", "SEYKM",
    "SILVR", "SMRTG", "SOKM", "SONME", "SUMAS", "SURGY", "SUWEN", "TATGD",
    "TDGYO", "TEKTU", "TEPGE", "TEZOL", "TGSAS", "THYAO", "TKNSA", "TLMAN",
    "TMPOL", "TMSN", "TNZTP", "TRCAS", "TRGYO", "TRILC", "TSPOR", "TTRAK",
    "TUCLK", "TURSG", "UFUK", "ULUUN", "UNLU", "USAK", "USDTR", "UTPYA",
    "VAKFN", "VBTYZ", "VERUS", "VKFYO", "VRGYO", "WINTO", "WNGAR", "XCORP",
    "YATAS", "YKFIN", "YKSLN", "YONGA", "YUNSA", "YYLGD", "ZEDUR",
]

# Tekrar eden sembolleri temizle
BIST_SYMBOLS = list(set(BIST_SYMBOLS))


def send_telegram(message):
    """Telegram'a mesaj gönder"""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("HATA: Telegram bilgileri eksik!")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    try:
        r = requests.post(url, json=payload, timeout=10)
        if r.status_code == 200:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Telegram mesajı gönderildi.")
        else:
            print(f"Telegram hatası: {r.text}")
    except Exception as e:
        print(f"Telegram bağlantı hatası: {e}")


def ema(series, period):
    """EMA hesapla"""
    return series.ewm(span=period, adjust=False).mean()


def rsi(series, period=14):
    """RSI hesapla"""
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(com=period - 1, adjust=False).mean()
    avg_loss = loss.ewm(com=period - 1, adjust=False).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def adx_and_di(high, low, close, period=14):
    """ADX, +DI, -DI hesapla"""
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
    """CMF hesapla"""
    mfv = ((close - low) - (high - close)) / (high - low) * volume
    cmf = mfv.rolling(period).sum() / volume.rolling(period).sum()
    return cmf


def check_symbol(tv, symbol, timeframe_label, interval):
    """
    Bir sembolü belirtilen timeframe'de filtrele.
    Günlük veriler fundamental filtrelerde kullanılır,
    4 saatlik veriler teknik filtrelerde kullanılır.
    """
    try:
        # 4 saatlik veri (teknik analiz + stop)
        df4h = tv.get_hist(symbol=symbol, exchange="BIST", interval=interval, n_bars=200)
        if df4h is None or len(df4h) < 50:
            return None

        close = df4h["close"]
        high = df4h["high"]
        low = df4h["low"]
        volume = df4h["volume"]

        # Günlük veri (EMA200 için)
        df1d = tv.get_hist(symbol=symbol, exchange="BIST", interval=Interval.in_daily, n_bars=250)
        if df1d is None or len(df1d) < 200:
            return None

        # ---- TEKNİK FİLTRELER ----
        ema20_4h = ema(close, 20)
        ema50_4h = ema(close, 50)
        ema200_1d = ema(df1d["close"], 200)

        current_close = close.iloc[-1]
        current_ema20_4h = ema20_4h.iloc[-1]
        current_ema50_4h = ema50_4h.iloc[-1]
        current_ema200_1d = ema200_1d.iloc[-1]

        # Fiyat > EMA200 (günlük)
        if current_close <= current_ema200_1d:
            return None

        # EMA20 > EMA50 (4 saatlik)
        if current_ema20_4h <= current_ema50_4h:
            return None

        # RSI > 50
        rsi_val = rsi(close).iloc[-1]
        if rsi_val <= 50:
            return None

        # ADX > 18, +DI > -DI
        adx_val, plus_di, minus_di = adx_and_di(high, low, close)
        if adx_val.iloc[-1] <= 18:
            return None
        if plus_di.iloc[-1] <= minus_di.iloc[-1]:
            return None

        # CMF >= 0.04
        cmf_val = chaikin_money_flow(high, low, close, volume).iloc[-1]
        if cmf_val < 0.04:
            return None

        # Göreceli hacim > 1.5 (son bar hacmi / 20 bar ortalaması)
        avg_vol = volume.iloc[-21:-1].mean()
        rel_vol = volume.iloc[-1] / avg_vol if avg_vol > 0 else 0
        if rel_vol < 1.5:
            return None

        # Hacim * Fiyat > 15M TL
        if (volume.iloc[-1] * current_close) < 15_000_000:
            return None

        # Değişim % -2 ile +4 arası
        prev_close = close.iloc[-2]
        change_pct = (current_close - prev_close) / prev_close * 100
        if change_pct < -2 or change_pct > 4:
            return None

        # ---- STOP SEVİYESİ = 4 saatlik EMA20 ----
        stop_level = round(current_ema20_4h, 2)
        price = round(current_close, 2)

        return {
            "symbol": symbol,
            "price": price,
            "stop": stop_level,
            "change_pct": round(change_pct, 2),
            "rsi": round(rsi_val, 1),
            "adx": round(adx_val.iloc[-1], 1),
            "cmf": round(cmf_val, 3),
            "rel_vol": round(rel_vol, 2),
        }

    except Exception as e:
        print(f"  {symbol} hatası: {e}")
        return None


def run_scan():
    """Ana tarama fonksiyonu"""
    now = datetime.now(TURKEY_TZ)
    print(f"\n{'='*50}")
    print(f"Tarama başlıyor: {now.strftime('%d.%m.%Y %H:%M')}")
    print(f"{'='*50}")

    # Borsa saatleri dışında tarama yapma (opsiyonel - kripto için kaldır)
    # Saat 10:00 - 18:30 arası BIST
    if not (10 <= now.hour < 18 or (now.hour == 18 and now.minute <= 30)):
        print("Borsa kapalı, tarama atlanıyor.")
        return

    # TradingView bağlantısı
    try:
        if TV_USERNAME and TV_PASSWORD:
            tv = TvDatafeed(TV_USERNAME, TV_PASSWORD)
        else:
            tv = TvDatafeed()  # Anonim (bazı limitler olabilir)
    except Exception as e:
        print(f"TradingView bağlantı hatası: {e}")
        return

    # Timeframe'leri tanımla
    timeframes = {
        "1S": Interval.in_1_hour,
        "2S": Interval.in_2_hours,
        "4S": Interval.in_4_hours,
        "1G": Interval.in_daily,
    }

    all_results = {}

    for tf_label, tf_interval in timeframes.items():
        results = []
        print(f"\n[{tf_label}] Taranıyor...")
        for symbol in BIST_SYMBOLS:
            result = check_symbol(tv, symbol, tf_label, tf_interval)
            if result:
                results.append(result)
                print(f"  ✅ {symbol} geçti!")
            time.sleep(0.3)  # Rate limit için bekle

        all_results[tf_label] = results

    # Telegram mesajı oluştur
    send_scan_results(all_results, now)


def send_scan_results(results, scan_time):
    """Tarama sonuçlarını Telegram'a gönder"""
    time_str = scan_time.strftime("%d.%m.%Y %H:%M")
    total = sum(len(v) for v in results.values())

    if total == 0:
        msg = f"📊 <b>BIST Tarama - {time_str}</b>\n\nHiçbir hisse filtreleri geçemedi."
        send_telegram(msg)
        return

    msg = f"📊 <b>BIST Tarama Sonuçları</b>\n🕐 {time_str}\n"
    msg += "─" * 30 + "\n"

    for tf_label, stocks in results.items():
        if not stocks:
            continue
        msg += f"\n⏱ <b>{tf_label} Zaman Dilimi</b> ({len(stocks)} hisse)\n"
        for s in stocks:
            msg += (
                f"▶ <b>{s['symbol']}</b> | "
                f"Fiyat: {s['price']} ₺ | "
                f"Stop: {s['stop']} ₺\n"
            )

    msg += f"\n─" * 30
    msg += f"\n📌 Toplam: {total} hisse | Sonraki tarama: 15 dk sonra"

    send_telegram(msg)


def main():
    print("BIST Tarama Botu Başlatıldı!")
    print("Her 15 dakikada bir tarama yapılacak.\n")

    # İlk taramayı hemen yap
    run_scan()

    # Sonra her 15 dakikada bir
    schedule.every(15).minutes.do(run_scan)

    while True:
        schedule.run_pending()
        time.sleep(30)


if __name__ == "__main__":
    main()
