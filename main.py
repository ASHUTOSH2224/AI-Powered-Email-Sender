import os
import time
import pandas as pd
import smtplib
from dotenv import load_dotenv
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from langchain_groq import ChatGroq
from langchain.schema import HumanMessage, SystemMessage
from email.mime.base import MIMEBase
from email import encoders

# Load environment variables
load_dotenv()
groq_api_key = os.getenv("GROQ_API_KEY")
sender_email = os.getenv("ZOHO_EMAIL")
sender_password = os.getenv("ZOHO_APP_PASSWORD")

# Validate .env variables
if not all([groq_api_key, sender_email, sender_password]):
    print("❌ Missing environment variables. Please check your .env file.")
    exit()

# Load email template
with open("email_template_prompt.txt", "r") as f:
    template = f.read()

# Load dataset
df = pd.read_csv("companies_data.csv").dropna(subset=["Email", "Profile", "Sector", "State"])

# Ask for optional filters
selected_sector = input("Enter Sector to filter (press Enter to include all): ").strip().lower()
selected_state = input("Enter State to filter (press Enter to include all): ").strip().lower()

# Apply filters if provided
if selected_sector:
    df = df[df["Sector"].str.lower() == selected_sector]
if selected_state:
    df = df[df["State"].str.lower() == selected_state]

if df.empty:
    print("❌ No matching records found with the given filters.")
    exit()

# Initialize Groq Chat model
chat = ChatGroq(api_key=groq_api_key, model_name="llama3-70b-8192")

# Function to generate personalized email using Groq
def generate_email(row):
    try:
        prompt = template.format(
            company_name=row.get("Name of the Exhibitor", "your company"),
            contact_person=row.get("Contact Person", "there"),
            sector=row.get("Sector", "your industry"),
            profile=row.get("Profile", "your company profile")
        )

        messages = [
            SystemMessage(content="You are an expert email writer for business communication."),
            HumanMessage(content=prompt)
        ]

        response = chat(messages)
        email_text = response.content.strip()

        # Clean generic intro line if present
        lines = email_text.splitlines()
        if lines and "business development email" in lines[0].lower():
            email_text = "\n".join(lines[1:]).strip()

        return email_text

    except Exception as e:
        print(f"❌ Error generating email for {row.get('Contact Person', 'Unknown')}: {e}")
        return "Hi, I wanted to reach out regarding a potential collaboration opportunity."

# ✅ Function to append Calendly link to email message
def append_calendly_link(message_body, contact_person):
    calendly_link = "https://calendly.com/scalixitydevops/meet"
    friendly_line = (
        f"\n\nIf you're interested in scheduling a meeting, please use this link to book a time that works for you: "
        f"{calendly_link}\n\nLooking forward to connecting, {contact_person}!"
    )
    return message_body.strip() + friendly_line

# Email sending function (Zoho-compatible)
def send_email(to_email, contact_person, generated_message, sender_email, sender_password, attachment=None):
    try:
        smtp_server = "smtp.zoho.in"
        smtp_port = 587
        subject = "Let's Collaborate!"

        msg = MIMEMultipart()
        msg["From"] = sender_email
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(generated_message, 'plain'))

        # Attach file if provided
        if attachment:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(attachment.read())
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', f'attachment; filename={attachment.filename}')
            msg.attach(part)

        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, to_email, msg.as_string())

        print(f"✅ Email sent to {contact_person} ({to_email})")
        return True

    except Exception as e:
        print(f"❌ Failed to send email to {contact_person} ({to_email}): {e}")
        return False

# Group by Sector and State
grouped = df.groupby(["Sector", "State"])

# Loop through each group
for (sector, state), group_data in grouped:
    print(f"\n📂 Processing Sector: {sector} | State: {state} | Companies: {len(group_data)}")

    for _, row in group_data.iterrows():
        to_email = row.get("Email")
        contact_person = row.get("Contact Person", "there")
        generated_msg = generate_email(row)

         # ✅ Add Calendly booking link
        final_message = append_calendly_link(generated_msg, contact_person)

        print(f"\n📝 Email Preview for {contact_person} ({to_email}):\n{generated_msg}\n")
        send_email(to_email, contact_person, final_message, sender_email, sender_password)
        time.sleep(1.5)  # Prevent SMTP rate-limiting
