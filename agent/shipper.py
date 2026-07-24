import requests


class Shipper:
    def __init__(self, hub_url, server_name, api_key):
        self.endpoint = f"{hub_url}/api/events"
        self.server_name = server_name
        self.api_key = api_key

    def ship(self, event):
        payload = {
            "serverName": self.server_name,
            "apiKey": self.api_key,
            "triggeredBy": event["triggered_by"],
            "contextBefore": event["context_before"],
            "lines": event["lines"],
            "startedAt": event["started_at"],
        }
        try:
            r = requests.post(self.endpoint, json=payload, timeout=30)
            r.raise_for_status()
            data = r.json()
            print(f"✅ shipped event id={data['id']}")
            if data.get("diagnosis"):
                print(f"🧠 Jarrvis says: {data['diagnosis']}")
        except requests.RequestException as e:
            print(f"⚠️ ship failed: {e}")