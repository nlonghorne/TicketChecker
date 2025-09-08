import os
import requests
import time
import smtplib
from dotenv import load_dotenv
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

load_dotenv()

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
API_KEY = os.getenv("API_KEY")
REFRESH_TOKEN = os.getenv("REFRESH_TOKEN")

# Cached ID token and expiry
id_token = None
expiry_time = 0

def send_email(subject, body):
    msg = MIMEMultipart()
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = EMAIL_ADDRESS
    msg["Subject"] = subject

    msg.attach(MIMEText(body, "plain"))

    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls()
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        server.sendmail(EMAIL_ADDRESS, EMAIL_ADDRESS, msg.as_string())

def get_id_token():
    global id_token, expiry_time

    # If token still valid, reuse it
    if id_token and time.time() < expiry_time:
        return id_token

    url = f"https://securetoken.googleapis.com/v1/token?key={API_KEY}"
    payload = {
        "grant_type": "refresh_token",
        "refresh_token": REFRESH_TOKEN
    }

    res = requests.post(url, data=payload)
    res.raise_for_status()
    ticket_data = res.json()

    # Save ID token + expiry
    id_token = ticket_data["id_token"]
    expires_in = int(ticket_data["expires_in"])  # usually 3600
    expiry_time = time.time() + expires_in - 60  # refresh 1 min early

    return id_token


def call_resale_api():
    token = get_id_token()
    url = "https://marketplace.ticketek.com.au/search/api/products"

    params = {
        "content_id": "TESADO0126",
        "sort": "date asc"
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36",
        "Accept": "application/json",
        "Authorization": f"Bearer {token}",
        "Referer": "https://marketplace.ticketek.com.au/purchase/searchlist/products?keyword=ashes%20sydney&content_id=TESSCG0126",
        "sec-ch-ua": '"Not;A=Brand";v="99", "Google Chrome";v="139", "Chromium";v="139"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"macOS"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin"
    }

    resp = requests.get(url, headers=headers, params=params)
    resp.raise_for_status()
    ticket_data = resp.json()

    # Define the target dates
    target_dates = {"2025-12-17"}

    # Filter tickets by date
    filtered = []
    for product in ticket_data.get("results", []):
        if product.get("available_tickets_count") == 2:
            product_fields = product.get("fields")
            date = product_fields.get("date")
            if date:
                date_only = date.split("T")[0]  # keep just YYYY-MM-DD
                if date_only in target_dates:
                    filtered.append(product)

    email_text = "Dear Nat,\n\nAshes Tickets have been found for the following days:\n"

    if len(filtered):
        for ticket in filtered:
            email_text += ticket.get("fields").get("when")
            email_text += "\n"
        email_text += "\nCheck here now:\nhttps://marketplace.ticketek.com.au/purchase/searchlist/products?keyword=ashes%20adelaide&content_id=TESADO0126"
        email_text += "\n\nLove from,\nYourself <3"
        send_email("Ashes Tickets Found!!", email_text)
        print("Tickets Found!")
    else:
        print("No tickets found :(")

    if resp.status_code != 200:
        err_msg = "Dear Nat,\n\nYour ticket script has an error with the request status code, take a look."
        err_msg += f"\n\nStatus Code:\n{resp.status_code}\n\nFrom,\nYourself"
        send_email("Oops there's a problem...", err_msg)
    print(f"Request Status Code:{resp.status_code}")


if __name__ == "__main__":
    call_resale_api()