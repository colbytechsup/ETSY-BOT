"""Where parsed leads go next. WebhookSink posts JSON to whatever your marketing tool accepts
(a Zapier/Make catch hook, a HubSpot/Mailchimp workflow endpoint, your own server).
The payload is the Lead fields plus `campaign`; map them on the receiving side."""
import json
import re
import urllib.error
import urllib.request


class SinkError(RuntimeError):
    """HTTP error from the CRM, with the response body so the reason is visible."""


def post_json(url, payload, headers=None):
    body = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=body, method="POST",
                                 headers={"Content-Type": "application/json", **(headers or {})})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            text = r.read().decode("utf-8", "replace")
            try:
                return json.loads(text) if text else r.status
            except ValueError:
                return text[:500]
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")[:1000]
        raise SinkError(f"HTTP {e.code} from {url}\n{detail}") from None


def enrich(lead_dict):
    """Payload for a CRM webhook (GoHighLevel inbound-webhook workflows map these by name):
    the Lead fields plus first_name / last_name split from name and a tags list."""
    payload = {k: v for k, v in lead_dict.items() if k not in ("dedup_key", "added")}
    first, _, last = (payload.get("name") or "").strip().partition(" ")
    payload["first_name"], payload["last_name"] = first, last.strip()
    companies = [re.sub(r"[^a-z0-9]+", "_", c.lower()).strip("_") for c in (payload.get("company") or "").split(",")]
    payload["tags"] = [t for t in [payload.get("campaign"), payload.get("source"), *companies] if t]
    return payload


class WebhookSink:
    def __init__(self, url, headers=None, post=post_json):
        self.url, self.headers, self.post = url, headers or {}, post

    def send(self, lead_dict):
        return self.post(self.url, enrich(lead_dict), self.headers)


class GhlSink:
    """Create/update a GoHighLevel contact through the public API with a Private Integration
    token (sub-account Settings > Private Integrations, scope contacts.write). API calls are
    not Premium Workflow Actions, so there is no per-execution charge that I know of; verify.

    Endpoint and header values are my understanding of the v2 API (marketplace.gohighlevel.com
    /docs): POST {base}/contacts/upsert with `Authorization: Bearer <token>` and a `Version`
    date header. The upsert matches on email/phone per the location's duplicate setting.
    If GHL returns 401/422, check the token scopes and LEADS_GHL_VERSION first."""
    base = "https://services.leadconnectorhq.com"

    def __init__(self, token, location_id, version="2021-07-28", post=post_json):
        self.token, self.location, self.version, self.post = token, location_id, version, post

    def send(self, lead_dict):
        p = enrich(lead_dict)
        body = {"locationId": self.location, "firstName": p["first_name"], "lastName": p["last_name"],
                "name": p.get("name") or "", "email": p.get("email") or None,
                "phone": p.get("phone") or None, "source": p.get("source") or "",
                "tags": p["tags"], "companyName": "", "customFields": []}
        body = {k: v for k, v in body.items() if v not in (None, "", [])}
        if p.get("job_title"):
            body["customFields"] = [{"key": "job_applied_for", "field_value": p["job_title"]}]
        headers = {"Authorization": f"Bearer {self.token}", "Version": self.version, "Accept": "application/json"}
        return self.post(f"{self.base}/contacts/upsert", body, headers)


def sink_from_env(env):
    """Pick the configured sink: GHL API if LEADS_GHL_TOKEN is set, else webhook, else None."""
    if env.get("LEADS_GHL_TOKEN") and env.get("LEADS_GHL_LOCATION"):
        return GhlSink(env["LEADS_GHL_TOKEN"], env["LEADS_GHL_LOCATION"],
                       env.get("LEADS_GHL_VERSION", "2021-07-28"))
    if env.get("LEADS_WEBHOOK"):
        return WebhookSink(env["LEADS_WEBHOOK"])
    return None
