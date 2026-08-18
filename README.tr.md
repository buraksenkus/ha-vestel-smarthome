# Home Assistant için Vestel Smart Home

[![Release](https://img.shields.io/github/v/release/mehmetaktas/ha-vestel-smarthome)](https://github.com/mehmetaktas/ha-vestel-smarthome/releases)
[![Downloads](https://img.shields.io/github/downloads/mehmetaktas/ha-vestel-smarthome/total.svg)](https://github.com/mehmetaktas/ha-vestel-smarthome/releases)
[![Validate](https://github.com/mehmetaktas/ha-vestel-smarthome/actions/workflows/validate.yml/badge.svg)](https://github.com/mehmetaktas/ha-vestel-smarthome/actions/workflows/validate.yml)
[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

🇬🇧 [English](README.md)

Vestel **Akıllı Yaşam** / **Evin Aklı** uygulamasıyla yönetilen klimalar için
resmî olmayan Home Assistant entegrasyonu (`homevsmart` bulut platformu).

> Vestel ile bir ilişkisi yoktur, Vestel tarafından onaylanmamış ve
> desteklenmemektedir. Resmî uygulamanın kullandığı bulut API'sini kullanır;
> bu API haber verilmeden değişebilir.

![Home Assistant'taki cihaz sayfası](https://raw.githubusercontent.com/mehmetaktas/ha-vestel-smarthome/main/images/device-page.png)

## Özellikler

| Varlık | Ne yapıyor |
| --- | --- |
| `climate` | Kapalı / oto / soğutma / nem alma / vantilatör / ısıtma, hedef sıcaklık, fan hızı, kanat pozisyonu, oda sıcaklığı |
| `switch` | Turbo, Eco, İyonizer, Uyku modu — yalnızca cihazının bildirdikleri |
| `sensor` | Oda sıcaklığı |
| `binary_sensor` | Bağlantı ve arıza durumu (ham hata kodu öznitelik olarak) |

Yetenekler sabit kodlanmaz, cihazın kendi `/device/discovery` belgesinden
okunur. Böylece modlar, sıcaklık aralıkları ve mevcut ekstralar senin
cihazının gerçekten desteklediğiyle örtüşür. Sıcaklık sınırları cihazın
kurallarını izler; Eco açıkken geçerli olan daha dar aralıklar dâhil.

## Gereksinimler

- Home Assistant 2024.12 veya üzeri
- Klimanın uygulamada eşleştirilmiş olduğu bir Akıllı Yaşam hesabı

## Kurulum

### HACS (önerilen)

[![Bu depoyu Home Assistant Community Store içinde aç.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=mehmetaktas&repository=ha-vestel-smarthome&category=integration)

Yukarıdaki düğmeye bas, ya da elle ekle:

1. HACS → Integrations → ⋮ → **Custom repositories**
2. `https://github.com/mehmetaktas/ha-vestel-smarthome` adresini **Integration**
   kategorisiyle ekle
3. **Vestel Smart Home**'u kur ve Home Assistant'ı yeniden başlat

### Manuel

`custom_components/vestel_smarthome` klasörünü Home Assistant'ın
`config/custom_components/` dizinine kopyala ve yeniden başlat.

## Ayarlama

[![Home Assistant'ta yeni entegrasyon kurulumunu başlat.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=vestel_smarthome)

**Ayarlar → Cihazlar ve Servisler → Entegrasyon Ekle → Vestel Smart Home**,
ardından uygulamada kullandığın e-posta ve şifreyle giriş yap. Hesabında
birden fazla ev varsa hangisini ekleyeceğin sorulur.

Sorgulama aralığı varsayılan olarak 30 saniyedir, entegrasyon seçeneklerinden
değiştirilebilir.

## Panel örnekleri

İki isteğe bağlı kart. Entegrasyon bunlar olmadan da çalışır, ama en çok
sorulan iki şeyi karşılıyorlar: derli toplu bir kumanda ve "bir süre sonra
kapansın" zamanlayıcısı.

Her yerde `climate.oturma_odasi_klima` yerine kendi varlık kimliğini yaz.

### Klima tile kartı

![Klima tile kartı](https://raw.githubusercontent.com/mehmetaktas/ha-vestel-smarthome/main/images/card-climate.png)

Cihaz adını, o anki modu ve hedef sıcaklığı, ölçülen oda sıcaklığını ve modu
değiştiren düğme sırasını gösterir. Ayrı bir "aç" düğmesi yoktur: `cool` ya da
`dry` seçmek cihazı açar, `off` kapatır.

```yaml
type: tile
entity: climate.oturma_odasi_klima
vertical: false
features_position: bottom
features:
  - type: climate-hvac-modes
    hvac_modes:
      - "off"
      - cool
      - dry
```

| Seçenek | Anlamı | Alabileceği değerler |
| --- | --- | --- |
| `entity` | Klima varlığı. Zorunlu. | senin `climate.*` varlığın |
| `vertical` | İkon metnin yanında değil üstünde | `true`, `false` (varsayılan) |
| `features_position` | Düğme sırasının yeri | `bottom` (varsayılan), `inline` |
| `hvac_modes` | Hangi mod düğmeleri, bu sırayla | `"off"`, `auto`, `cool`, `dry`, `fan_only`, `heat` — cihazının bildirdikleri |

`"off"` tırnak içinde olmalı. Tırnaksız YAML `off` kelimesini `false` booleanı
olarak okur ve düğme sessizce kaybolur. `hvac_modes` satırını hiç yazmazsan
cihazın desteklediği bütün modlar görünür.

**Neler ekleyebilirsin.** Aşağıdakilerin her biri `features:` altına eklenen
ayrı bir madde. Tile kartı bunları yazdığın sırayla alt alta dizer.

| Özellik | Ne ekler | Seçenekleri |
| --- | --- | --- |
| `target-temperature` | Hedef sıcaklık için artı/eksi kumandası | yok |
| `climate-fan-modes` | Fan hızı seçici | `fan_modes:` — `auto`, `1`, `2`, `3`, `4`, `5`; `style:` `dropdown` (varsayılan) veya `icons` |
| `climate-swing-modes` | Kanat pozisyonu seçici | `swing_modes:` — `"off"`, `1`–`6`; `style:` `dropdown` veya `icons` |

Daha dolu bir sürüm:

```yaml
type: tile
entity: climate.oturma_odasi_klima
features_position: bottom
features:
  - type: climate-hvac-modes
    hvac_modes:
      - "off"
      - cool
      - dry
      - heat
  - type: target-temperature
  - type: climate-fan-modes
    style: icons
    fan_modes:
      - auto
      - "1"
      - "3"
      - "5"
```

Cihaz bazı kombinasyonlara izin vermiyor ve entegrasyon bunu uyguluyor: Turbo
açıkken fan hızı değiştirilemez, `fan_only` modunda otomatik hız yoktur, Eco
açıkken geçerli sıcaklık aralığı daralır. Reddedilen değerler cihaza
gönderilmez, ekranda hata olarak görünür.

Turbo, Eco, İyonizer ve Uyku ayrı `switch` varlıklarıdır; tile kartının özellik
sırasına değil kendi kartlarına konur.

### Kapatma zamanlayıcısı

![Zamanlayıcı kartı](https://raw.githubusercontent.com/mehmetaktas/ha-vestel-smarthome/main/images/card-timer.png)

Bir süre seç, **Başlat**'a bas, kart geri saymaya başlar. Sıfıra ulaşınca klima
kapanır ve bildirim gider. Geri sayım bir `timer` yardımcısında tutulduğu için
Home Assistant yeniden başlasa bile bozulmaz — script içindeki düz bir `delay:`
bunu yapamaz.

Dört parça gerekiyor.

**1. Yardımcılar** — Ayarlar → Cihazlar ve Servisler → Yardımcılar → Yardımcı oluştur

| Yardımcı | Türü | Varlık kimliği |
| --- | --- | --- |
| Süre girişi | **Tarih ve/veya saat** → yalnızca *Saat* | `input_datetime.klima_kapatma_suresi` |
| Geri sayım | **Zamanlayıcı** | `timer.klima_kapatma` |

**2. Script** — süreyi okuyup geri sayımı başlatır

```yaml
alias: Klima kapat (süreli)
sequence:
  - action: timer.start
    target:
      entity_id: timer.klima_kapatma
    data:
      duration: >-
        {{ '%02d:%02d:00' % (
             state_attr('input_datetime.klima_kapatma_suresi', 'hour'),
             state_attr('input_datetime.klima_kapatma_suresi', 'minute')) }}
```

**3. Otomasyon** — süre dolunca klimayı kapatır

```yaml
alias: Klima - süre dolunca kapat
mode: single
triggers:
  - trigger: event
    event_type: timer.finished
    event_data:
      entity_id: timer.klima_kapatma
conditions: []
actions:
  - action: climate.turn_off
    target:
      entity_id: climate.oturma_odasi_klima
  - action: persistent_notification.create
    data:
      title: Klima kapatıldı
      message: Süre doldu, klima otomatik kapandı.
```

Bildirimin telefona gitmesini istersen `persistent_notification.create` yerine
`notify.mobile_app_<telefonun>` yaz. Bildirim yalnızca zamanlayıcı kapattığında
gider, sen elle kapattığında çıkmaz.

**4. Kart**

```yaml
type: entities
title: Klima kapatma
entities:
  - entity: input_datetime.klima_kapatma_suresi
    name: Süre (saat:dakika)
  - entity: timer.klima_kapatma
    name: Kalan
  - type: button
    name: Zamanlayıcı
    icon: mdi:timer-play
    action_name: Başlat
    tap_action:
      action: perform-action
      perform_action: script.klima_kapat_sureli
```

| Satır | Ne okur / ne yapar | Değerler |
| --- | --- | --- |
| Süre girişi | Kapanmadan önce ne kadar beklenecek | `00:01`–`23:59`, saat:dakika olarak |
| Kalan | Kalan süre | duruyorken `idle`, çalışırken geri sayar |
| Başlat düğmesi | Script'i çalıştırır, o da zamanlayıcıyı başlatır | — |

Süre yardımcısı bir **süre uzunluğu** olarak okunur, saat olarak değil: `01:30`
"bir buçuk saat sonra" demektir, "saat 01:30'da" değil.

Geri sayım sürerken Başlat'a tekrar basmak sayacı o anki değerle sıfırdan
başlatır. İptal için `timer.klima_kapatma` üzerinde `timer.cancel` çağır —
`perform_action: timer.cancel` yazan ikinci bir düğme satırı işi görür.

## Nasıl çalışıyor

Cihaz durumunu birkaç sayısal register üzerinden bildirir. Her register'ın
içine birden fazla ayar bit olarak paketlenmiştir:

| Register | Bitler | Ayar |
| --- | --- | --- |
| `ACGENSI` | 0–2 | Mod — 0 oto, 1 soğutma, 2 nem alma, 3 vantilatör, 4 ısıtma, 5 kapalı |
| `ACGENSI` | 3–5 | Fan hızı — 0 oto, 1–5 |
| `ACTEMOT` | 0–3 | Hedef sıcaklık, `°C − 16` olarak |
| `ACFANPO` | 0 / 1–3 / 4–6 / 7 / 8 / 9 | Turbo / dikey kanat / yatay kanat / uyku / iyonizer / eco |
| `ACROOTE` | — | Ölçülen oda sıcaklığı |
| `ACERROR` | — | Arıza kodu, sağlıklıyken `0` |

Komutlar `<REGISTER><5 haneli değer>` biçiminde geri yazılır; örneğin
soğutmayı başlatmak için `ACGENSI00001`. Ayarlar register paylaştığı için
entegrasyon değişiklikleri birleştirir ve register başına tek yazma yapar.

## Güvenlik

**E-posta ve şifren ne için kullanılıyor.** Yalnızca Vestel'in kendi giriş
adresine (`cognito-idp.eu-west-1.amazonaws.com`) token almak için gönderilir —
resmî uygulamanın attığı isteğin aynısı. Başka hiçbir yere gitmez, entegrasyon
üçüncü taraf hiçbir sunucuya bağlanmaz.

**Nerede saklanıyor.** Home Assistant bunları refresh token ile birlikte
`config/.storage/core.config_entries` dosyasında **düz metin** olarak tutar.
Tüm Home Assistant bulut entegrasyonları böyle çalışır; bu depoya hiçbir şey
yazılmaz. Şifre, token'ın süresi dolduğunda entegrasyonun kendi kendine tekrar
giriş yapabilmesi için saklanır.

**Bu senin için ne demek.** Home Assistant yapılandırma klasörünü ya da onun
şifrelenmemiş bir yedeğini okuyabilen herkes bu bilgileri okuyabilir.
Yedeklerini şifrele ve paylaşma.

**Diagnostics dosyasını issue'ya eklemek güvenlidir.** Token, şifre, MAC
adresi, seri numarası ve MQTT topic'leri otomatik olarak maskelenir.

## SSS

**Kumandadan ya da uygulamadan bir şey değiştirdiğimde niçin anında
yansımıyor?** Entegrasyon bulutu sorguluyor, varsayılan olarak 30 saniyede bir;
dışarıdan yapılan değişiklik bir sonraki sorguda görünür. Home Assistant'tan
yaptığın değişiklikler ise anında görünür — yeni değer iyimser olarak uygulanıp
6 saniye sonra cihaza karşı doğrulanıyor. Cihaz anlık güncellemeleri MQTT
üzerinden yayınlıyor ama bu henüz kullanılmıyor.

**Token'larla uğraşmam gerekecek mi?** Hayır. Giriş token'ı bir saat geçerli ve
süresi dolmadan otomatik yenileniyor; yetkisiz dönen bir istek taze token'la bir
kez tekrar deneniyor. Senden bir şey istenmiyor.

**Hesap şifremi değiştirirsem ne olur?** Entegrasyon giriş yapamaz ve Home
Assistant entegrasyon üzerinde yeniden kimlik doğrulama uyarısı gösterir. Yeni
şifreyi oraya gir — kaldırıp tekrar eklemen gerekmez.

**Aynı anda telefon uygulamasını kullanabilir miyim?** Evet. İkisinin de kendi
oturumu var, biri diğerini düşürmüyor.

**Başka bir Vestel modelinde çalışır mı?** Muhtemelen. Modlar, sıcaklık
aralıkları ve ekstralarla ilgili hiçbir şey sabit kodlanmadı — hepsi cihazın
kendi `/device/discovery` belgesinden okunuyor, dolayısıyla farklı bir klima
kendi yetenekleriyle gelir. Yalnızca `deviceType: AC` işleniyor, aynı hesaptaki
diğer beyaz eşyalar yok sayılıyor. Cihazın tuhaf davranırsa diagnostics
dosyasını ekleyerek issue aç.

**Sıcaklık niçin istediğim kadar aşağı/yukarı gitmiyor?** Geçerli aralık moda
göre değişiyor ve cihaz bunu uyguluyor: soğutma ile ısıtmanın sınırları farklı,
Eco'yu açmak aralığı daha da daraltıyor. Entegrasyon bu sınırları tahmin etmiyor,
cihazdan okuyor.

**İnternet olmadan çalışır mı?** Hayır. Her komut Vestel'in bulutundan geçiyor,
tıpkı telefon uygulaması gibi.

**Birden fazla klimam / evim var.** Her ev ayrı bir entegrasyon kaydı olarak
eklenir, o evdeki desteklenen her cihaz da ayrı bir cihaz olur. Hesabında birden
fazla ev varsa kurulumda hangisini ekleyeceğin sorulur.

## Kısıtlar

- Yalnızca bulut sorgulaması. Cihaz anlık güncellemeleri MQTT üzerinden de
  yayınlıyor ancak entegrasyon bunu henüz kullanmıyor.
- Yalnızca klimalar (`deviceType: AC`) desteklenir. Aynı platformdaki diğer
  beyaz eşyalar yok sayılır.
- Yatay kanat protokolde var ama yalnızca bunu bildiren modellerde sunulur.
- Zamanlayıcı ayarları (`AutoOn`, `AutoOff`, `QuickOff`) çözülüyor ama henüz
  varlık olarak sunulmuyor.

## Sorun giderme

Hata ayıklama günlüğünü aç:

```yaml
logger:
  default: info
  logs:
    custom_components.vestel_smarthome: debug
```

Issue açmadan önce entegrasyon sayfasından diagnostics dosyasını indir — token,
seri numarası ve MQTT topic'leri otomatik maskelenir.

## Lisans

MIT
