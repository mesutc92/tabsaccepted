# KAP Bildirim Takibi

Borsa İstanbul şirketlerinin [KAP](https://www.kap.org.tr) (Kamuyu Aydınlatma Platformu) bildirimlerini **1 dakikada bir** (isterseniz 5 dakikada bir) tarar, hissede pozitif etki yaratabilecek türden haberleri ayıklar ve e-posta ile iletir.

Bu bir tavsiye aracı değildir; KAP’ın kamuya açık bildirimlerini hızlı görmeniz içindir.

## Ne yapar?

1. KAP’ın herkese açık bildirim listesini çeker (`/tr/api/disclosure/members/byCriteria`).
2. Devre kesici, test, içeriden öğrenenlerin alım-satımı gibi gürültüyü atar.
3. Kalanları kural setine göre puanlar: kâr artışı, temettü, yeni sözleşme, ihale kazanımı, birleşme/devralma, pay geri alımı, kapasite/yatırım vb.
4. Özel durum açıklamalarında bildirim gövdesini de okur.
5. Eşleşenleri HTML e-posta olarak gönderir. Aynı bildirimi ikinci kez göndermez.

Varsayılan aralık **60 saniye**dir. KAP tarafında makul bir hızdır (tur başına 1 liste isteği + yalnızca adayların gövdesi).

## Docker ile yerelde çalıştırma

Docker Desktop (Windows/macOS) veya Docker Engine + Compose yeterli. Konteynerin `www.kap.org.tr` ve SMTP sunucusuna çıkışı olmalı.

```bash
git clone https://github.com/mesutc92/tabsaccepted.git
cd tabsaccepted
git checkout cursor/kap-bildirim-takibi-8a90   # PR main'e birleşene kadar
cp config/env.example .env
```

`.env` içinde **en az** `SMTP_PASSWORD` ve `ALERT_TO` doldurun (aşağıdaki tablo). Sonra:

```bash
docker compose up -d --build
docker compose logs -f
```

İlk denemede mail atmadan log izlemek için `.env` içinde `KAP_DRY_RUN=true` yapın, sonra `false` çekip `docker compose up -d` tekrarlayın.

Tek tur (mail yok):

```bash
docker compose run --rm kap-alert kap-alert once --dry-run --notify-on-start
```

Durdurma: `docker compose down` (görülen bildirimler volume’da kalır). Sıfırdan başlamak: `docker compose down -v`.

Filtreleri `src/kap_alert/filters.yaml` üzerinden değiştirip `docker compose restart` yeterli; imajı yeniden derlemeniz gerekmez.

## Ayarlar (`.env`)

Şablon: `config/env.example` → proje kökünde `.env`. Docker Compose bu dosyayı okur.

**Mail için zorunlu**

| Değişken | Örnek | Not |
| --- | --- | --- |
| `SMTP_HOST` | `smtp.office365.com` | Gmail: `smtp.gmail.com` |
| `SMTP_PORT` | `587` | STARTTLS |
| `SMTP_USER` | hesap e-postası | |
| `SMTP_PASSWORD` | SMTP / uygulama şifresi | Repoya koymayın |
| `SMTP_FROM` | gönderen adres | Office 365’te genelde `SMTP_USER` ile aynı |
| `SMTP_STARTTLS` | `true` | |
| `ALERT_TO` | alıcı adres | Tek alıcı |

Office 365’te MFA açıksa normal şifre çoğu zaman yetmez; kiracıda SMTP AUTH açık olmalı veya uygulama şifresi kullanılmalı. Gmail’de [uygulama şifresi](https://support.google.com/accounts/answer/185833) gerekir. Bu alanlar boşsa program mail atmaz, dry-run’a düşer.

**İsteğe bağlı**

| Değişken | Varsayılan | Anlamı |
| --- | --- | --- |
| `KAP_POLL_INTERVAL` | `60` | Saniye. `300` = 5 dakika |
| `KAP_LOOKBACK_DAYS` | `1` | Liste penceresi (dün+bugün) |
| `KAP_DRY_RUN` | `false` | `true`: mail yok, log var |
| `KAP_NOTIFY_ON_START` | `false` | İlk çalışmada listedekileri de bildir |
| `KAP_BACKFILL_MINUTES` | `0` | İlk çalışmada yalnızca son N dakikayı bildir |
| `KAP_FETCH_BODY` | `true` | Özel durum gövdesini oku |

## Python ile (Docker olmadan)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp config/env.example .env
python -m kap_alert watch --interval 60
```

Tek seferlik deneme: `KAP_DRY_RUN=1 python -m kap_alert once --notify-on-start`

## Filtreleri değiştirme

Kurallar `src/kap_alert/filters.yaml` içindedir.

- `skip_subjects`: hiç bakılmayan konular
- `always_match_subjects`: konu başlığı yeter, hemen bildir
- `categories.*.patterns`: özet + gövde içinde aranan ifadeler (Türkçe karakter katlamalı)
- `veto_patterns`: iflas, konkordato, not düşürme gibi olumsuzlar
- `min_score`: eşik (varsayılan 3)

## systemd

`deploy/kap-alert.service` örneğini `/etc/systemd/system/` altına kopyalayıp `WorkingDirectory` ve `EnvironmentFile` yollarını düzenleyin.

## Geliştirme

```bash
pip install -e ".[dev]"
pytest
```

Canlı KAP’a bağlanan testler CI’da yoktur; birim testleri kaydedilmiş KAP JSON fixture’ları ve kural setini kullanır.
