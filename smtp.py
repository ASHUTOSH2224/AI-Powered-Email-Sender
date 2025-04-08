import smtplib

your_email = "ashutosh2224@zohomail.in"
app_password = "9j08s3v02WJj"  # Paste here for now

try:
    server = smtplib.SMTP("smtp.zoho.in", 587)
    server.starttls()
    server.login(your_email, app_password)
    print("✅ SMTP login successful!")
    server.quit()
except smtplib.SMTPAuthenticationError as e:
    print(f"❌ Authentication failed: {e}")
