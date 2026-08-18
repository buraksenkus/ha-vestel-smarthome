# Brand assets

These files are **not** used by the integration itself. They are prepared for a
pull request to [home-assistant/brands](https://github.com/home-assistant/brands),
which is what makes Home Assistant and HACS show a proper icon instead of the
generic placeholder.

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
