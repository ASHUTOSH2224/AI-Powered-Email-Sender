import smtplib

your_email = "sales@scalixity.com"
app_password = "BEPSyBs4qJbc"  # Paste here for now

try:
    server = smtplib.SMTP("smtp.zoho.in", 587)
    server.starttls()
    server.login(your_email, app_password)
    print("✅ SMTP login successful!")
    server.quit()
except smtplib.SMTPAuthenticationError as e:
    print(f"❌ Authentication failed: {e}")
