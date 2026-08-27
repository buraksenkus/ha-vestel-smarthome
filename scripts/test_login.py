#!/usr/bin/env python3
"""Verify that e-mail + password login works before installing the integration.

Run it from the repository root:

    python3 scripts/test_login.py

The password is read with getpass, so it is never echoed or stored.
"""

from __future__ import annotations

import base64
import getpass
import hashlib
import hmac
import json
import sys
import urllib.error
import urllib.request

sys.path.insert(0, "custom_components/vestel_smarthome")

from const import API_BASE, CLIENT_ID, CLIENT_SECRET, COGNITO_URL, USER_AGENT, SUPPORTED_DEVICE_TYPES  # noqa: E402


def post(url: str, body: dict, headers: dict) -> tuple[int, dict]:
    request = urllib.request.Request(
        url, data=json.dumps(body).encode(), headers=headers
    )
    try:
        with urllib.request.urlopen(request) as response:
            return response.status, json.load(response)
    except urllib.error.HTTPError as err:
        return err.code, json.load(err)


def main() -> int:
    email = input("E-posta: ").strip()
    password = getpass.getpass("Sifre (ekranda gorunmez): ")

    secret_hash = base64.b64encode(
        hmac.new(
            CLIENT_SECRET.encode(), (email + CLIENT_ID).encode(), hashlib.sha256
        ).digest()
    ).decode()

    print("\n[1/3] Cognito girisi...")
    status, body = post(
        COGNITO_URL,
        {
            "AuthFlow": "USER_PASSWORD_AUTH",
            "ClientId": CLIENT_ID,
            "AuthParameters": {
                "USERNAME": email,
                "PASSWORD": password,
                "SECRET_HASH": secret_hash,
            },
        },
        {
            "Content-Type": "application/x-amz-json-1.1",
            "X-Amz-Target": "AWSCognitoIdentityProviderService.InitiateAuth",
        },
    )
    if status != 200:
        print(f"  BASARISIZ ({status}): {body.get('__type')} - {body.get('message')}")
        return 1
    if "AuthenticationResult" not in body:
        print(f"  Beklenmeyen challenge: {body.get('ChallengeName')}")
        print("  Bu hesap MFA veya sifre degistirme istiyor olabilir.")
        return 1

    result = body["AuthenticationResult"]
    print("  OK - IdToken alindi, RefreshToken:", "var" if result.get("RefreshToken") else "YOK")

    print("\n[2/3] Evler okunuyor...")
    request = urllib.request.Request(
        f"{API_BASE}/homes",
        headers={
            "Accept": "application/json",
            "User-Agent": USER_AGENT,
            "Token": result["IdToken"],
        },
    )
    with urllib.request.urlopen(request) as response:
        homes = json.load(response).get("items", [])
    for home in homes:
        print(f"  - {home.get('homeName')}  ({home.get('homeId')})")
    if not homes:
        print("  Hic ev bulunamadi.")
        return 1

    print("\n[3/3] Cihazlar okunuyor...")
    total_supported = 0
    for home in homes:
        request = urllib.request.Request(
            f"{API_BASE}/homes/{home['homeId']}/devices",
            headers={
                "Accept": "application/json",
                "User-Agent": USER_AGENT,
                "Token": result["IdToken"],
            },
        )
        with urllib.request.urlopen(request) as response:
            devices = json.load(response)["items"]["homeappliances"]
        for device in devices:
            supported = "DESTEKLENIYOR" if device.get("deviceType") in SUPPORTED_DEVICE_TYPES else "atlanacak"
            online = "cevrimici" if device.get("connected") else "CEVRIMDISI"
            print(
                f"  - {device.get('deviceName')} [{device.get('deviceType')}] "
                f"{device.get('deviceModel')} - {online} - {supported}"
            )
            if supported == "DESTEKLENIYOR":
                total_supported += 1

    if total_supported == 0:
        print("\nUYARI: Giris basarili ancak hicbir cihaz bulunamadi. Entegrasyon beklendigi gibi calisamayacak.")
        return 0
    print(f"\nSonuc: Desteklenen {total_supported} cihaz bulundu. Entegrasyon calisacak.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
