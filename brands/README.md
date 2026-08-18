# Brand assets

This directory is the master copy of the brand artwork, kept here so the source
files stay together at full resolution. It is not shipped to users.

Two places consume it:

1. **`custom_components/vestel_smarthome/brand/`** — `icon.png` and `logo.png`
   are copied there. HACS validation requires an `icon.png` at that exact path
   unless the domain is already listed in the brands repository, so keep the
   copies in sync when the artwork changes.
2. **[home-assistant/brands](https://github.com/home-assistant/brands)** — the
   pull request described below, which is what makes Home Assistant show the
   icon instead of the generic placeholder.

| File          | Size    | Purpose            |
| ------------- | ------- | ------------------ |
| `icon.png`    | 256×256 | Integration icon   |
| `icon@2x.png` | 512×512 | Retina icon        |
| `logo.png`    | 249×54  | Wordmark           |
| `logo@2x.png` | 499×108 | Retina wordmark    |

All four are PNG with a transparent background and no surrounding padding.

## Submitting

Copy them into a fork of `home-assistant/brands` under:

```
custom_integrations/vestel_smarthome/
```

then open a pull request. Only `icon.png` and `icon@2x.png` are mandatory.

## Trademark note

The icon is derived from the Vestel wordmark. This integration is unofficial and
not affiliated with or endorsed by Vestel; the mark is used only to identify the
appliances the integration talks to.
