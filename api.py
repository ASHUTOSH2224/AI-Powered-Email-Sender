from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import os
import time
import uvicorn
import smtplib
from dotenv import load_dotenv
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from langchain_groq import ChatGroq
from langchain.schema import HumanMessage, SystemMessage
import io
import traceback

print("Starting API server initialization...")

# Load environment variables
load_dotenv()
groq_api_key = os.getenv("GROQ_API_KEY")
sender_email = os.getenv("ZOHO_EMAIL")
sender_password = os.getenv("ZOHO_APP_PASSWORD")

# Debug environment variables
print(f"GROQ_API_KEY loaded: {'Yes' if groq_api_key else 'No'}")
print(f"ZOHO_EMAIL loaded: {'Yes' if sender_email else 'No'}")
print(f"ZOHO_APP_PASSWORD loaded: {'Yes' if sender_password else 'No'}")

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, you should specify your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

print("Loading email template...")
# Load email template
try:
    with open("email_template_prompt.txt", "r") as f:
        template = f.read()
    print("Email template loaded successfully")
except Exception as e:
    print(f"Error loading email template: {e}")
    template = "Write a business development email to {company_name}. The contact person is {contact_person}. They are in the {sector} sector. Here is their profile: {profile}"

# Function to generate personalized email using Groq
def generate_email(row, custom_prompt=""):
    try:
        print(f"Generating email for: {row.get('Contact Person', 'Unknown contact')}")
        prompt = template.format(
            company_name=row.get("Name of the Exhibitor", "your company"),
            contact_person=row.get("Contact Person", "there"),
            sector=row.get("Sector", "your industry"),
            profile=row.get("Profile", "your company profile")
        )
        
        # Add custom prompt if provided
        if custom_prompt:
            prompt += f"\n\nAdditional instructions: {custom_prompt}"

        messages = [
            SystemMessage(content="You are an expert email writer for business communication."),
            HumanMessage(content=prompt)
        ]

        # Initialize Groq Chat model
        print("Initializing Groq Chat model...")
        chat = ChatGroq(api_key=groq_api_key, model_name="llama3-70b-8192")
        print("Calling Groq API...")
        response = chat(messages)
        email_text = response.content.strip()

        # Clean generic intro line if present
        lines = email_text.splitlines()
        if lines and "business development email" in lines[0].lower():
            email_text = "\n".join(lines[1:]).strip()

        print("Email generated successfully")
        return email_text

    except Exception as e:
        print(f"❌ Error generating email: {e}")
        traceback.print_exc()
        return "Hi, I wanted to reach out regarding a potential collaboration opportunity."

# Email sending function (Zoho-compatible)
def send_email(to_email, contact_person, generated_message, sender_email, sender_password):
    try:
        print(f"Sending email to {to_email}...")
        smtp_server = "smtp.zoho.in"
        smtp_port = 587
        subject = "Let's Collaborate!"

        msg = MIMEMultipart()
        msg["From"] = sender_email
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(generated_message, 'plain'))

        print(f"Connecting to SMTP server {smtp_server}:{smtp_port}...")
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            print("Logging in to SMTP server...")
            server.login(sender_email, sender_password)
            print("Sending email...")
            server.sendmail(sender_email, to_email, msg.as_string())

        print(f"✅ Email sent to {contact_person} ({to_email})")
        return True

    except Exception as e:
        print(f"❌ Failed to send email to {contact_person} ({to_email}): {e}")
        traceback.print_exc()
        return False

@app.post("/send-emails")
async def send_emails(
    file: UploadFile = File(None),
    prompt: str = Form(""),
    sector: str = Form(""),
    state: str = Form(""),
):
    print(f"Received request with parameters: prompt='{prompt}', sector='{sector}', state='{state}', file={file is not None}")
    
    # Validate environment variables
    if not all([groq_api_key, sender_email, sender_password]):
        error_msg = "Missing environment variables. Please check your .env file."
        print(f"Error: {error_msg}")
        raise HTTPException(status_code=500, detail=error_msg)
    
    try:
        # Process the uploaded CSV file or use the default one
        if file:
            print("Reading uploaded CSV file...")
            contents = await file.read()
            df = pd.read_csv(io.BytesIO(contents)).dropna(subset=["Email"])
            print(f"CSV file loaded with {len(df)} rows")
        else:
            print("Using default CSV file...")
            df = pd.read_csv("companies_data.csv").dropna(subset=["Email", "Profile", "Sector", "State"])
            print(f"Default CSV file loaded with {len(df)} rows")
        
        # Apply filters if provided
        if sector:
            print(f"Filtering by sector: {sector}")
            df = df[df["Sector"].str.lower() == sector.lower()]
        if state:
            print(f"Filtering by state: {state}")
            df = df[df["State"].str.lower() == state.lower()]

        print(f"After filtering: {len(df)} rows remaining")
        if df.empty:
            error_msg = "No matching records found with the given filters."
            print(f"Error: {error_msg}")
            raise HTTPException(status_code=404, detail=error_msg)
        
        # Process emails
        results = []
        for _, row in df.iterrows():
            to_email = row.get("Email")
            contact_person = row.get("Contact Person", "there")
            print(f"Processing email for {contact_person} ({to_email})")
            
            generated_msg = generate_email(row, prompt)
            
            success = send_email(to_email, contact_person, generated_msg, sender_email, sender_password)
            results.append({
                "email": to_email,
                "contact": contact_person,
                "success": success
            })
            time.sleep(1.5)  # Prevent SMTP rate-limiting
        
        response_msg = f"Processed {len(results)} emails"
        print(f"Success: {response_msg}")
        return {"message": response_msg, "results": results}
    
    except Exception as e:
        error_msg = f"An error occurred: {str(e)}"
        print(f"Error: {error_msg}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=error_msg)

print("API setup complete, starting server...")
if __name__ == "__main__":
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True) 