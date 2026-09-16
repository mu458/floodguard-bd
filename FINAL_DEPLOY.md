# FloodGuard BD — Final Alert System

This is the final one-time website package.

## Email automation
- Welcome email: sent immediately when a logged-in user turns alerts ON for the first time after being disabled.
- Test email: sent to the logged-in user's own email.
- Zone update email: manual button, sent to the logged-in user's email.
- Risk-change email: sent once for every risk-category transition in either direction (e.g. NORMAL→WARNING or WARNING→NORMAL). Failed sends are retried.
- Daily email: at most once per user per calendar day.
- Recipient is the email saved on the user's FloodGuard account; it is not hard-coded to the Google Apps Script owner.

## Google Apps Script
The Flask app calls the configured Google Apps Script Web App URL. The Apps Script should use the current doPost() bridge that accepts `to`, `subject`, and `body`, then calls GmailApp.sendEmail().

## Render
Start command:
`gunicorn --bind 0.0.0.0:$PORT app:app`

The app includes an in-process alert worker. It checks every 60 seconds by default (`ALERT_CHECK_SECONDS` can override this). A Render instance that is sleeping cannot run the background worker; for guaranteed 24/7 daily alerts on a sleeping/free service, use a scheduled external trigger later. For a continuously running instance, the worker handles daily and risk-change checks automatically.

## Important
- The public dashboard does not require login.
- Data state is clearly distinguished as LIVE / FFWC SNAPSHOT / SIMULATION.
- Google Apps Script uses the Gmail account that owns the script as the sending account; recipients can be any valid email address allowed by Gmail/App Script quotas.
