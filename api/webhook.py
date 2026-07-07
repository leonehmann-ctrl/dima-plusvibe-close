"""
PlusVibe → Close CRM Webhook (Vercel Serverless Function)
==========================================================
Client:   DIMA Concept
Endpoint: POST /api/webhook

Receives ALL_POSITIVE_REPLIES events from PlusVibe (DIMA Concept workspace),
creates a new lead in Close CRM with status "‼️ Leads NEU Mailing",
and sends an email notification to lead@dimaconcept.de.

Environment variables (set in Vercel dashboard):
  CLOSE_API_KEY   – Close CRM API key
  SMTP_PASSWORD   – IONOS SMTP password for newlead@instant-page.com
"""

import json
import os
import smtplib
from base64 import b64encode
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from http.server import BaseHTTPRequestHandler

import requests

# ─── Config ──────────────────────────────────────────────────────────────────
CLOSE_API_KEY     = os.environ.get("CLOSE_API_KEY", "")
CLOSE_STATUS_ID   = "stat_Hqveykbf0snz8sFxVDOTQDaWmE4oSW1Tv8NBCN6sJqq"  # ‼️ Leads NEU Mailing
CLOSE_BASE_URL    = "https://api.close.com/api/v1"

PLUSVIBE_WORKSPACE_ID = "673748c6292c2d7ea644671b"  # DIMA Concept

# Custom field IDs in DIMA's Close CRM
CF_BRANCHE     = "cf_A7RkR6MIlol3GiWjsfVkByWLcnNNYNoJ21VV80a8GC2"  # 1.01 Branche
CF_LEADQUELLE  = "cf_0eCOnaAOIBG30ZYXQumUtEPqlwMMVP0Ukr3XOQbqOVI"  # 1.02 Leadquelle

# Lead owner: Leon Ehmann (user-type custom field)
CF_LEAD_OWNER  = "cf_vVzqicxXtvyHk3sn8OmL6Pdh80fCXUVGXr1s2K6D0AT"  # 3.0 Lead Owner
LEAD_OWNER_ID  = "user_VKAbb03k5f7NwrwZ0bjNoN55EO575PnHQQkpAVmpGY6"

SMTP_HOST     = "smtp.ionos.de"
SMTP_PORT     = 465
SMTP_USER     = "newlead@instant-page.com"
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
NOTIFY_TO     = "lead@dimaconcept.de"
NOTIFY_FROM   = "newlead@instant-page.com"


def create_close_lead(payload: dict) -> str:
    """Create a new lead in Close CRM. Returns the lead ID."""
    first_name   = payload.get("first_name", "")
    last_name    = payload.get("last_name", "")
    from_email   = payload.get("from_email") or payload.get("email", "")
    phone_number = payload.get("phone_number", "")
    company_name = payload.get("company_name", "")
    campaign     = payload.get("campaign_name", "")
    workspace    = payload.get("workspace_name", "")
    text_body    = payload.get("text_body") or payload.get("snippet", "")
    label        = payload.get("label", "")
    created_at   = payload.get("created_at", "")
    job_title    = payload.get("job_title", "")
    linkedin     = payload.get("linkedin_person_url", "")

    city        = payload.get("city", "")

    lead_name = company_name or f"{first_name} {last_name}".strip() or from_email

    contact: dict = {"name": f"{first_name} {last_name}".strip() or from_email}

    addresses = []
    if city:
        addresses = [{"city": city, "label": "business"}]
    if from_email:
        contact["emails"] = [{"email": from_email, "type": "office"}]
    if phone_number:
        contact["phones"] = [{"phone": phone_number, "type": "office"}]

    desc_parts = []
    if campaign:   desc_parts.append(f"Kampagne: {campaign}")
    if workspace:  desc_parts.append(f"Workspace: {workspace}")
    if label:      desc_parts.append(f"Label: {label}")
    if job_title:  desc_parts.append(f"Position: {job_title}")
    if linkedin:   desc_parts.append(f"LinkedIn: {linkedin}")
    if created_at: desc_parts.append(f"Antwort erhalten: {created_at}")

    auth = b64encode(f"{CLOSE_API_KEY}:".encode()).decode()
    headers = {"Authorization": f"Basic {auth}", "Content-Type": "application/json"}

    resp = requests.post(
        f"{CLOSE_BASE_URL}/lead/",
        headers=headers,
        json={
            "name": lead_name,
            "status_id": CLOSE_STATUS_ID,
            "contacts": [contact],
            **(({"addresses": addresses}) if addresses else {}),
            "description": "\n".join(desc_parts),
            f"custom.{CF_BRANCHE}": "Immobilien Makler",
            f"custom.{CF_LEADQUELLE}": "Positive Reply Call, Instant Lead",
            "custom.3.0 Lead Owner": LEAD_OWNER_ID,
        },
        timeout=20,
    )
    resp.raise_for_status()
    lead_id = resp.json().get("id", "")

    if text_body and lead_id:
        requests.post(
            f"{CLOSE_BASE_URL}/activity/note/",
            headers=headers,
            json={"lead_id": lead_id, "note": f"📧 PlusVibe Antwort:\n\n{text_body}"},
            timeout=20,
        )

    return lead_id


def send_notification(payload: dict, close_lead_id: str) -> None:
    """Send HTML email notification about the new lead."""
    first_name   = payload.get("first_name", "")
    last_name    = payload.get("last_name", "")
    from_email   = payload.get("from_email") or payload.get("email", "")
    company_name = payload.get("company_name", "")
    campaign     = payload.get("campaign_name", "")
    workspace    = payload.get("workspace_name", "")
    text_body    = payload.get("text_body") or payload.get("snippet", "")
    phone_number = payload.get("phone_number", "")
    job_title    = payload.get("job_title", "")
    linkedin     = payload.get("linkedin_person_url", "")
    label        = payload.get("label", "")

    full_name  = f"{first_name} {last_name}".strip() or from_email
    close_url  = f"https://app.close.com/leads/{close_lead_id}/" if close_lead_id else "#"
    subject    = f"🔥 Neuer Interessent: {full_name} ({campaign})"

    rows = [("Name", full_name), ("E-Mail", f'<a href="mailto:{from_email}">{from_email}</a>')]
    if phone_number: rows.append(("Telefon", phone_number))
    if company_name: rows.append(("Unternehmen", company_name))
    if job_title:    rows.append(("Position", job_title))
    rows.append(("Kampagne", campaign))
    rows.append(("Workspace", workspace))
    rows.append(("Label", label))
    if linkedin:     rows.append(("LinkedIn", f'<a href="{linkedin}">{linkedin}</a>'))
    rows.append(("Close CRM", f'<a href="{close_url}" style="color:#007bff;">Lead öffnen →</a>'))

    table_html = "".join(
        f"<tr><td style='padding:8px 0;color:#666;width:140px;'><strong>{k}</strong></td>"
        f"<td style='padding:8px 0;'>{v}</td></tr>"
        for k, v in rows
    )

    html = f"""<html><body style="font-family:Arial,sans-serif;background:#f5f5f5;padding:20px;">
  <div style="max-width:600px;margin:0 auto;background:white;border-radius:8px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,.1);">
    <div style="background:#1a1a2e;padding:24px;color:white;">
      <h1 style="margin:0;font-size:22px;">🔥 Neuer Interessent aus PlusVibe</h1>
      <p style="margin:8px 0 0;opacity:.8;">Automatisch in Close CRM eingetragen – DIMA Concept</p>
    </div>
    <div style="padding:24px;">
      <table style="width:100%;border-collapse:collapse;">{table_html}</table>
      <div style="margin-top:20px;padding:16px;background:#f8f9fa;border-left:4px solid #007bff;border-radius:4px;">
        <strong style="color:#333;">Antwort des Leads:</strong>
        <p style="margin:8px 0 0;color:#555;white-space:pre-wrap;">{(text_body or 'Kein Text')[:1000]}</p>
      </div>
    </div>
    <div style="padding:16px 24px;background:#f5f5f5;color:#999;font-size:12px;">
      Automatisch versendet von PlusVibe → Close CRM Integration (DIMA Concept)
    </div>
  </div>
</body></html>"""

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = NOTIFY_FROM
    msg["To"]      = NOTIFY_TO
    msg.attach(MIMEText(html, "html", "utf-8"))

    with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=20) as server:
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.sendmail(NOTIFY_FROM, [NOTIFY_TO], msg.as_string())


class handler(BaseHTTPRequestHandler):
    """Vercel Python serverless handler."""

    def log_message(self, format, *args):
        pass

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"status": "ok", "client": "DIMA Concept"}).encode())

    def do_POST(self):
        try:
            length  = int(self.headers.get("Content-Length", 0))
            payload = json.loads(self.rfile.read(length))
        except Exception:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b'{"error":"invalid payload"}')
            return

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()

        event        = payload.get("webhook_event", "")
        workspace_id = payload.get("workspace_id", "")

        # Filter: only DIMA Concept workspace
        if workspace_id != PLUSVIBE_WORKSPACE_ID:
            self.wfile.write(json.dumps({"skipped": "wrong workspace"}).encode())
            return

        # Only process ALL_POSITIVE_REPLIES – ignore all other events to avoid duplicates
        if event != "ALL_POSITIVE_REPLIES":
            self.wfile.write(json.dumps({"skipped": f"event {event} ignored"}).encode())
            return

        try:
            lead_id = create_close_lead(payload)
            send_notification(payload, lead_id)
            self.wfile.write(json.dumps({"success": True, "close_lead_id": lead_id}).encode())
        except requests.HTTPError as e:
            self.wfile.write(json.dumps({"error": f"Close API: {e.response.status_code}"}).encode())
        except Exception as e:
            self.wfile.write(json.dumps({"error": str(e)}).encode())
