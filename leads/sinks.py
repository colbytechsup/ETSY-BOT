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


class WebhookSink:
    def __init__(self, url, headers=None, post=post_json):
        self.url, self.headers, self.post = url, headers or {}, post

    def send(self, lead_dict):
        payload = {k: v for k, v in lead_dict.items() if k not in ("dedup_key", "added")}
        return self.post(self.url, payload, self.headers)
