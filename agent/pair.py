import sys

import requests

from config import load_config


def main():
    if len(sys.argv) != 2:
        print("usage: python pair.py <code>")
        sys.exit(1)

    cfg = load_config()
    r = requests.post(
        f"{cfg['hub']['url']}/api/pairing/redeem",
        json={"code": sys.argv[1], "apiKey": cfg["hub"]["api_key"]},
        timeout=10,
    )
    if r.status_code == 200:
        print("✅ Paired. Your dashboard should unlock now.")
    elif r.status_code == 410:
        print("⏰ Code expired — refresh the dashboard for a new one.")
    elif r.status_code == 401:
        print("❌ This server isn't registered with the hub yet — is the agent running?")
    else:
        print("❌ Invalid code.")


if __name__ == "__main__":
    main()