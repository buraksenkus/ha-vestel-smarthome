"""Constants for the Vestel Smart Home integration."""

from __future__ import annotations

from datetime import timedelta

DOMAIN = "vestel_smarthome"

# Cloud endpoints used by the "Akilli Yasam" / "Evin Akli" mobile app.
COGNITO_URL = "https://cognito-idp.eu-west-1.amazonaws.com/"
API_BASE = "https://sh-native-api.homevsmart.com/v1.0"

# Public app client credentials embedded in the mobile app.
CLIENT_ID = "6tl8koi5fis9j7i3u3jnv15vr7"
CLIENT_SECRET = "mc4j2r13mctk8u46poaic9snm83khk458c8a1uupk6sqoqar90c"

USER_AGENT = (
    "AkilliYasam Production/4.2401.39 "
    "(com.vestel.SmartHome; build:2; iOS 26.5.0) Alamofire/5.12.0"
)

CONF_HOME_ID = "home_id"
CONF_REFRESH_TOKEN = "refresh_token"
CONF_SCAN_INTERVAL_SECONDS = "scan_interval_seconds"

DEFAULT_SCAN_INTERVAL = timedelta(seconds=30)
MIN_SCAN_INTERVAL_SECONDS = 10
MAX_SCAN_INTERVAL_SECONDS = 600

SUPPORTED_DEVICE_TYPES = {"AC"}
