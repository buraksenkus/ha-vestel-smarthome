# Vestel Smart Home for Home Assistant

[![Release](https://img.shields.io/github/v/release/mehmetaktas/ha-vestel-smarthome)](https://github.com/mehmetaktas/ha-vestel-smarthome/releases)
[![Downloads](https://img.shields.io/github/downloads/mehmetaktas/ha-vestel-smarthome/total.svg)](https://github.com/mehmetaktas/ha-vestel-smarthome/releases)
[![Validate](https://github.com/mehmetaktas/ha-vestel-smarthome/actions/workflows/validate.yml/badge.svg)](https://github.com/mehmetaktas/ha-vestel-smarthome/actions/workflows/validate.yml)
[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

🇹🇷 [Türkçe](README.tr.md)

Unofficial Home Assistant integration for air conditioners managed by the
Vestel **Akıllı Yaşam** / **Evin Aklı** mobile app (the `homevsmart` cloud
platform).

> Not affiliated with, endorsed by, or supported by Vestel. It talks to the same
> cloud API the official app uses, which can change without notice.

![The device page in Home Assistant](https://raw.githubusercontent.com/mehmetaktas/ha-vestel-smarthome/main/images/device-page.png)

## Features

| Entity | What it does |
| --- | --- |
| `climate` | Off / auto / cool / dry / fan only / heat, target temperature, fan speed, louvre position, room temperature |
| `switch` | Turbo, Eco, Ionizer, Sleep mode — only the ones your model reports |
| `sensor` | Room temperature |
| `binary_sensor` | Connectivity and fault state (with the raw error code as an attribute) |

Capabilities are read from the appliance's own `/device/discovery` document
rather than hard coded, so modes, temperature ranges and available extras match
whatever your unit actually supports. Temperature limits follow the appliance
rules, including the narrower ranges that apply while Eco is on.

## Requirements

- Home Assistant 2024.12 or newer
- A Vestel Akıllı Yaşam account with the air conditioner already paired in the app

## Installation

### HACS (recommended)

[![Open this repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=mehmetaktas&repository=ha-vestel-smarthome&category=integration)

Click the button above, or add it by hand:

1. HACS → Integrations → ⋮ → **Custom repositories**
2. Add `https://github.com/mehmetaktas/ha-vestel-smarthome` as category **Integration**
3. Install **Vestel Smart Home**, then restart Home Assistant

### Manual

Copy `custom_components/vestel_smarthome` into your Home Assistant
`config/custom_components/` directory and restart.

## Setup

[![Start setting up a new integration in your Home Assistant instance.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=vestel_smarthome)

**Settings → Devices & Services → Add Integration → Vestel Smart Home**, then
sign in with the same e-mail and password you use in the app. If the account has
more than one home you will be asked which one to add.

The polling interval defaults to 30 seconds and can be changed in the
integration options.

## Dashboard examples

Two optional cards. Neither is required — the integration works without them —
but they cover the two things people ask for most: a compact control and a
"turn it off in a while" timer.

Replace `climate.oturma_odasi_klima` with your own entity ID everywhere.

### Climate tile

![Climate tile card](https://raw.githubusercontent.com/mehmetaktas/ha-vestel-smarthome/main/images/card-climate.png)

Shows the appliance name, its current mode and target temperature, the measured
room temperature, and a row of buttons that switch the mode. There is no
separate on button: picking `cool` or `dry` turns the unit on, `off` turns it
off.

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

| Option | Meaning | Accepted values |
| --- | --- | --- |
| `entity` | The climate entity. Required. | your `climate.*` entity |
| `vertical` | Icon above the text instead of beside it | `true`, `false` (default) |
| `features_position` | Where the button row sits | `bottom` (default), `inline` |
| `hvac_modes` | Which mode buttons to show, in this order | `"off"`, `auto`, `cool`, `dry`, `fan_only`, `heat` — whichever your model reports |

`"off"` must be quoted. Unquoted YAML reads `off` as the boolean `false` and the
button silently disappears. Omitting `hvac_modes` shows every mode the
appliance supports.

**What else you can add.** Each entry below is another item under `features:`.
The tile renders them stacked in the order you list them.

| Feature | What it adds | Options |
| --- | --- | --- |
| `target-temperature` | Plus/minus control for the target temperature | none |
| `climate-fan-modes` | Fan speed selector | `fan_modes:` — `auto`, `1`, `2`, `3`, `4`, `5`; `style:` `dropdown` (default) or `icons` |
| `climate-swing-modes` | Louvre position selector | `swing_modes:` — `"off"`, `1`–`6`; `style:` `dropdown` or `icons` |

A fuller version:

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

The appliance restricts some combinations and the integration enforces them:
fan speed cannot be changed while Turbo is on, `fan_only` has no auto speed, and
the valid temperature range narrows while Eco is on. Rejected values raise a
visible error instead of being sent to the appliance.

Turbo, Eco, Ionizer and Sleep are separate `switch` entities, so they belong in
their own card rather than in the tile's feature row.

### Shutdown timer

![Timer card](https://raw.githubusercontent.com/mehmetaktas/ha-vestel-smarthome/main/images/card-timer.png)

Pick a duration, press **Başlat** (Start), and the card counts down. When it
reaches zero the air conditioner is turned off and a notification is sent.
Because the countdown lives in a `timer` helper, it survives a Home Assistant
restart — a plain `delay:` in a script does not.

Four pieces are needed.

**1. Helpers** — Settings → Devices & Services → Helpers → Create helper

| Helper | Type | Entity ID |
| --- | --- | --- |
| Duration input | **Date and/or time** → *Time* only | `input_datetime.klima_kapatma_suresi` |
| Countdown | **Timer** | `timer.klima_kapatma` |

**2. Script** — reads the duration and starts the countdown

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

**3. Automation** — turns the unit off when the countdown ends

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

Swap `persistent_notification.create` for `notify.mobile_app_<your_phone>` to
get a push notification instead of an in-app one. The notification only fires
when the timer turns the unit off, never when you switch it off yourself.

**4. Card**

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

| Row | Reads / does | Values |
| --- | --- | --- |
| Duration input | How long to wait before switching off | `00:01`–`23:59`, entered as hours:minutes |
| Countdown | Time left | `idle` when stopped, otherwise counts down |
| Start button | Runs the script, which starts the timer | — |

The duration helper is interpreted as a *length of time*, not a clock time:
`01:30` means "in one and a half hours", not "at half past one".

Pressing Start again while a countdown is running restarts it with the current
value. To cancel, call `timer.cancel` on `timer.klima_kapatma` — a second button
row with `perform_action: timer.cancel` does the job.

## How it works

The appliance exposes its state as a handful of numeric registers. Several
settings are bit packed into each one:

| Register | Bits | Setting |
| --- | --- | --- |
| `ACGENSI` | 0–2 | Mode — 0 auto, 1 cool, 2 dry, 3 fan only, 4 heat, 5 off |
| `ACGENSI` | 3–5 | Fan speed — 0 auto, 1–5 |
| `ACTEMOT` | 0–3 | Target temperature, as `°C − 16` |
| `ACFANPO` | 0 / 1–3 / 4–6 / 7 / 8 / 9 | Turbo / vertical swing / horizontal swing / sleep / ionizer / eco |
| `ACROOTE` | — | Measured room temperature |
| `ACERROR` | — | Fault code, `0` when healthy |

Commands are written back as `<REGISTER><5-digit value>`, for example
`ACGENSI00001` to start cooling. Because settings share registers, the
integration merges changes into a single write per register.

## Security

**What your e-mail and password are used for.** They are sent only to Vestel's
own login endpoint (`cognito-idp.eu-west-1.amazonaws.com`) to obtain an access
token — the same request the official app makes. Nothing is sent anywhere else,
and the integration contacts no third-party server.

**Where they are stored.** Home Assistant keeps them in
`config/.storage/core.config_entries`, in plain text, together with the refresh
token. This is how every Home Assistant cloud integration works — nothing is
written into this repository. The password is kept so the integration can sign
in again by itself when the token eventually expires.

**What this means for you.** Anyone who can read your Home Assistant
configuration folder, or an unencrypted backup of it, can read those
credentials. Encrypt your backups and do not share them.

**Diagnostics are safe to attach to an issue.** Tokens, passwords, MAC
addresses, serial numbers and MQTT topics are redacted automatically.

## FAQ

**Why doesn't the state update the instant I change something on the remote or in
the app?** The integration polls the cloud, by default every 30 seconds, so an
external change shows up on the next poll. Changes you make from Home Assistant
appear immediately — the new value is applied optimistically and then confirmed
against the appliance 6 seconds later. The appliance does push instant updates
over MQTT, but that is not implemented yet.

**Do I have to keep dealing with tokens?** No. The login token lasts an hour and
is refreshed automatically before it expires; a request that comes back
unauthorised is retried once with a fresh token. Nothing is asked of you.

**What happens if I change my account password?** The integration can no longer
sign in and Home Assistant shows a *Reconfigure* / re-authentication prompt on
the integration. Enter the new password there — no need to remove and re-add it.

**Can I use the phone app at the same time?** Yes. Both hold their own session
and neither logs the other out.

**Will it work with another Vestel model?** Possibly. Nothing about the modes,
temperature ranges or extras is hard coded — it is all read from the appliance's
own `/device/discovery` document, so a different air conditioner should come up
with its own capabilities. Only `deviceType: AC` is handled, so other appliances
on the same account are ignored. If your unit misbehaves, open an issue with the
diagnostics file attached.

**Why won't the temperature go as low or as high as I want?** The valid range
depends on the mode and the appliance enforces it: cooling and heating have
different limits, and turning Eco on narrows them further. The integration takes
these limits from the appliance rather than guessing.

**Does it work without internet?** No. Every command goes through Vestel's
cloud, exactly like the phone app.

**I have more than one air conditioner / home.** Each home is added as its own
integration entry, and every supported appliance in that home becomes a separate
device. If your account has several homes, setup asks which one to add.

## Limitations

- Cloud polling only. The appliance also publishes over MQTT for instant
  updates, which this integration does not use yet.
- Only air conditioners (`deviceType: AC`) are handled. Other appliances on the
  same platform are ignored.
- Horizontal swing exists in the protocol but is only offered by models that
  report it.
- Timer settings (`AutoOn`, `AutoOff`, `QuickOff`) are decoded but not exposed
  as entities yet.

## Troubleshooting

Enable debug logging:

```yaml
logger:
  default: info
  logs:
    custom_components.vestel_smarthome: debug
```

Download diagnostics from the integration page before opening an issue — tokens,
serial numbers and MQTT topics are redacted automatically.

## License

MIT
