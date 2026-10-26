"""Where parsed leads go next. WebhookSink posts JSON to whatever your marketing tool accepts
(a Zapier/Make catch hook, a HubSpot/Mailchimp workflow endpoint, your own server).
The payload is the Lead fields plus `campaign`; map them on the receiving side."""
import json
import urllib.request


def post_json(url, payload, headers=None):
    body = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=body, method="POST",
                                 headers={"Content-Type": "application/json", **(headers or {})})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.status


def enrich(lead_dict):
    """Payload for a CRM webhook (GoHighLevel inbound-webhook workflows map these by name):
    the Lead fields plus first_name / last_name split from name and a tags list."""
    payload = {k: v for k, v in lead_dict.items() if k not in ("dedup_key", "added")}
    first, _, last = (payload.get("name") or "").strip().partition(" ")
    payload["first_name"], payload["last_name"] = first, last.strip()
    payload["tags"] = [t for t in (payload.get("campaign"), payload.get("source")) if t]
    return payload


class WebhookSink:
    def __init__(self, url, headers=None, post=post_json):
        self.url, self.headers, self.post = url, headers or {}, post

    def send(self, lead_dict):
        return self.post(self.url, enrich(lead_dict), self.headers)
