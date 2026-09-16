FLOODGUARD BD — WhatsApp Cloud API setup

This version sends WhatsApp through the same Google Apps Script bridge used by email. No Twilio is required.

1) Create a Meta Developer app and add WhatsApp / WhatsApp Business Platform.
2) Create/choose the WhatsApp Business Account (WABA) and a WhatsApp phone number.
3) In the WhatsApp API setup, obtain:
   - WhatsApp phone number ID
   - a production access token (use a System User token for production, not a short-lived test token)
4) In Google Apps Script: Project Settings → Script properties → Add script property.
   Name: WHATSAPP_ACCESS_TOKEN
   Value: your Meta WhatsApp access token
5) Add another property:
   Name: WHATSAPP_PHONE_NUMBER_ID
   Value: your WhatsApp phone number ID
6) Save the properties.
7) Redeploy the existing Web App deployment after the script code changes: Deploy → Manage deployments → Edit → New version → Deploy.

Important production rules:
- Users must explicitly opt in before WhatsApp alerts are sent.
- Outside the 24-hour customer-service window, WhatsApp business-initiated messages generally need an approved message template. For recurring daily/risk-change alerts, create and approve the appropriate utility templates in WhatsApp Manager and use template messages in the app when required.
- Phone numbers must be in international format (e.g. Bangladesh +8801XXXXXXXXX).
