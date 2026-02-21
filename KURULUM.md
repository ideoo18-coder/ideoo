# BIST Tarama Botu - Kurulum Rehberi

## Sisteme Genel Bakış

Her 15 dakikada bir BIST hisselerini otomatik tarar, filtrelerini geçen hisseleri
aşağıdaki formatta Telegram'a gönderir:

```
📊 BIST Tarama Sonuçları
🕐 15.02.2025 14:15
──────────────────────────────
⏱ 4S Zaman Dilimi (3 hisse)
▶ THYAO | Fiyat: 285.40 ₺ | Stop: 271.00 ₺
▶ EREGL | Fiyat: 42.80 ₺  | Stop: 40.66 ₺
▶ ASELS | Fiyat: 95.20 ₺  | Stop: 90.44 ₺
```

**Stop seviyesi** = 4 saatlik EMA 20 değeri

---

## ADIM 1: Telegram Bot Oluştur

1. Telegram'da **@BotFather**'a git
2. `/newbot` yaz ve gönder
3. Bot için bir isim gir (örn: `BIST Tarama Botu`)
4. Kullanıcı adı gir (örn: `bist_tarama_bot`)
5. BotFather sana bir **token** verir → Bunu kaydet!
   Örnek: `7123456789:AAFxxxxxxxxxxxxxxxxxxxxxx`

### Chat ID Alma

1. Botuna bir mesaj gönder (herhangi bir şey yaz)
2. Tarayıcıda şu linki aç:
   `https://api.telegram.org/bot<TOKEN>/getUpdates`
   (TOKEN yerine kendi tokenını yaz)
3. JSON çıktısında `"chat":{"id":` yanındaki sayıyı kaydet
   Örnek: `"id": 987654321`

---

## ADIM 2: Railway'e Yükle (Ücretsiz Sunucu)

### 2.1 GitHub Hesabı Aç (ücretsiz)
- https://github.com adresine git, kayıt ol

### 2.2 Dosyaları GitHub'a Yükle
1. GitHub'da **"New repository"** tıkla
2. İsim ver: `bist-tarama`
3. **"uploading an existing file"** linkine tıkla
4. Sana verdiğim 3 dosyayı sürükle-bırak:
   - `main.py`
   - `requirements.txt`
   - `railway.toml`
5. **"Commit changes"** tıkla

### 2.3 Railway Hesabı Aç (ücretsiz)
- https://railway.app adresine git
- **"Start a New Project"** tıkla
- GitHub ile giriş yap

### 2.4 Projeyi Dağıt
1. **"Deploy from GitHub repo"** seç
2. `bist-tarama` reposunu seç
3. Railway otomatik build edecek

### 2.5 Çevre Değişkenlerini Ekle
Railway panelinde **Variables** sekmesine git, şunları ekle:

| Değişken | Değer |
|----------|-------|
| `TELEGRAM_BOT_TOKEN` | BotFather'dan aldığın token |
| `TELEGRAM_CHAT_ID` | Chat ID'n |

*(TradingView kullanıcı adı/şifre opsiyonel - eklemezsen anonim bağlanır)*

---

## ADIM 3: Botu Test Et

Railway'de **"Logs"** sekmesini aç. Şunları görmelisin:
```
BIST Tarama Botu Başlatıldı!
Her 15 dakikada bir tarama yapılacak.
Tarama başlıyor: 15.02.2025 14:00
[1S] Taranıyor...
  ✅ THYAO geçti!
...
```

Ve Telegram'a mesaj gelecek!

---

## Uygulanan Filtreler

| Filtre | Koşul |
|--------|-------|
| Göreceli Hacim | > 1.5 |
| Hacim × Fiyat | > 15M TL |
| RSI(14) | > 50 |
| ADX(14) | > 18 |
| +DI vs -DI | +DI > -DI |
| EMA20 vs EMA50 (4S) | EMA20 > EMA50 |
| Fiyat vs EMA200 (1G) | Fiyat > EMA200 |
| Chaikin Para Akışı | ≥ 0.04 |
| Günlük Değişim % | -2% ile +4% arası |
| **Stop Seviyesi** | **4S EMA 20** |

---

## Sık Karşılaşılan Sorunlar

**"Borsa kapalı, tarama atlanıyor" yazıyor**
→ Normal! Kod sadece 10:00-18:30 arası çalışır.

**Telegram mesajı gelmiyor**
→ Token ve Chat ID'yi kontrol et. Bota bir mesaj gönderip getUpdates'i tekrar dene.

**Hiç hisse çıkmıyor**
→ Filtreler çok katı olabilir. RSI eşiğini 45'e veya ADX'i 15'e düşürebilirsiniz (`main.py` içinde).

---

## Destek

Herhangi bir sorun yaşarsan kurulum adımlarını paylaş, yardımcı olalım!
