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

## Hızlı başlangıç

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp config/env.example .env
# .env içinde SMTP ve ALERT_TO alanlarını doldurun
```

Tek seferlik deneme (e-posta yok, konsola yazar):

```bash
KAP_DRY_RUN=1 python -m kap_alert once --notify-on-start
```

Sürekli izleme (her dakika):

```bash
python -m kap_alert watch --interval 60
```

Beş dakikada bir:

```bash
python -m kap_alert watch --interval 300
```

İlk çalışmada geçmişi basmamak için mevcut bildirimler tohumlanır ve e-posta gitmez. Son 30 dakikayı da görmek isterseniz:

```bash
python -m kap_alert watch --backfill-minutes 30
```

## E-posta ayarı

`.env` örneği (`config/env.example`):

| Değişken | Açıklama |
| --- | --- |
| `SMTP_HOST` | Örn. `smtp.office365.com` veya `smtp.gmail.com` |
| `SMTP_PORT` | Genelde `587` |
| `SMTP_USER` / `SMTP_PASSWORD` | SMTP kimliği |
| `SMTP_FROM` | Gönderen adres |
| `ALERT_TO` | Bildirimlerin gideceği adres |
| `KAP_POLL_INTERVAL` | Saniye (60 veya 300) |

Office 365 / Google’da uygulama şifresi veya SMTP relay gerekebilir. SMTP tanımlı değilse program otomatik dry-run’a düşer.

## Filtreleri değiştirme

Kurallar `src/kap_alert/filters.yaml` içindedir. Kendi kopyanızı `KAP_FILTERS_PATH` ile verebilirsiniz.

- `skip_subjects`: hiç bakılmayan konular
- `always_match_subjects`: konu başlığı yeter, hemen bildir
- `categories.*.patterns`: özet + gövde içinde aranan ifadeler (Türkçe karakter katlamalı)
- `veto_patterns`: iflas, konkordato, not düşürme gibi olumsuzlar
- `min_score`: eşik (varsayılan 3)

Belirli hisselerle sınırlamak isterseniz aynı dosyaya kendi kelimelerinizi eklemeniz yeter; ticker listesi ileride eklenebilir.

## Docker

```bash
cp config/env.example .env
docker compose up -d --build
docker compose logs -f
```

Veritabanı (`seen` bildirimler) volume’da tutulur; yeniden başlatınca aynı KAP kaydı tekrar mail gitmez.

## systemd

`deploy/kap-alert.service` örneğini `/etc/systemd/system/` altına kopyalayıp `WorkingDirectory` ve `EnvironmentFile` yollarını düzenleyin.

## Geliştirme

```bash
pip install -e ".[dev]"
pytest
```

Canlı KAP’a bağlanan testler CI’da yoktur; birim testleri kaydedilmiş KAP JSON fixture’ları ve kural setini kullanır.
