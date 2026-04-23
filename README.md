# DIMA Concept – PlusVibe → Close CRM Webhook

Vercel serverless function that receives `ALL_POSITIVE_REPLIES` events from PlusVibe (DIMA Concept workspace), creates a new lead in Close CRM with status **"‼️ Leads NEU Mailing"**, and sends an email notification to `lead@dimaconcept.de`.

## Webhook URL (after Vercel deploy)

```
POST https://<your-vercel-domain>/api/webhook
```

## Setup in PlusVibe

1. Go to **Settings → Webhooks** in PlusVibe
2. Click **Add Webhook**
3. Enter the URL above
4. Select event: `ALL_POSITIVE_REPLIES`
5. Select workspace: **DIMA Concept**
6. Save

## Environment Variables (set in Vercel Dashboard)

| Variable | Description |
|---|---|
| `CLOSE_API_KEY` | DIMA Concept Close CRM API key |
| `SMTP_PASSWORD` | IONOS SMTP password for newlead@instant-page.com |

## Configuration

| Setting | Value |
|---|---|
| PlusVibe Workspace | DIMA Concept (`673748c6292c2d7ea644671b`) |
| Close CRM Status | ‼️ Leads NEU Mailing |
| Notification Email | lead@dimaconcept.de |
| Sender Email | newlead@instant-page.com |
