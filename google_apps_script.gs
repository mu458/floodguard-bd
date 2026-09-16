// FloodGuard BD - Google Apps Script email bridge
// Deploy as Web app: Execute as Me, Who has access: Anyone.
function doGet() {
  return ContentService
    .createTextOutput(JSON.stringify({ok:true,service:'FloodGuard BD Email Service'}))
    .setMimeType(ContentService.MimeType.JSON);
}

function doPost(e) {
  try {
    const data = JSON.parse(e.postData.contents || '{}');
    if (data.action !== 'send_email') throw new Error('Invalid action');
    const to = String(data.to || '').trim();
    const subject = String(data.subject || 'FloodGuard BD Alert').trim();
    const body = String(data.body || '').trim();
    if (!to) throw new Error('Recipient email is required');
    if (!body) throw new Error('Email body is required');
    GmailApp.sendEmail(to, subject, body);
    return ContentService.createTextOutput(JSON.stringify({ok:true,message:'Email sent successfully'}))
      .setMimeType(ContentService.MimeType.JSON);
  } catch (err) {
    return ContentService.createTextOutput(JSON.stringify({ok:false,error:String(err)}))
      .setMimeType(ContentService.MimeType.JSON);
  }
}
