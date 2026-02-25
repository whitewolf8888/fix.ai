"""Client-side license verification helper."""

import json
import os
import platform
import socket
import urllib.request


def verify_license(license_key: str) -> None:
    """Send a heartbeat to the license verification endpoint."""
    api_base = os.environ.get("VULNSENTINEL_API_BASE", "https://your-api-domain.com")
    url = f"{api_base}/api/license/verify"

    payload = {
        "license_key": license_key,
        "client_metadata": {
            "hostname": socket.gethostname(),
            "platform": platform.platform(),
        },
    }

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})

    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            _ = response.read().decode("utf-8")
    except Exception:
        # Fail silently to avoid breaking client apps
        return
