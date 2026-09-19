import os
from dotenv import load_dotenv
import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException

load_dotenv()

configuration = sib_api_v3_sdk.Configuration()
configuration.api_key["api-key"] = os.getenv("BREVO_API_KEY")

BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:8000")


def send_negotiation_email(to_email: str, customer_name: str, offers: list[dict]) -> bool:
    api_instance = sib_api_v3_sdk.TransactionalEmailsApi(sib_api_v3_sdk.ApiClient(configuration))

    offer_lines = "".join(
        f"<li>{o['original_name']} is out of stock — we're offering "
        f"<strong>{o['alternative_name']}</strong> at {o['discount_percent']}% off instead.</li>"
        for o in offers
        if o["alternative_name"]
    )

    html_content = f"""
    <p>Hi {customer_name},</p>
    <p>Part of your order needs your input:</p>
    <ul>{offer_lines}</ul>
     <p><a href="{BASE_URL}/respond?order_id={offers[0]['order_id']}&decision=accept">Accept alternative</a>
    | <a href="{BASE_URL}/respond?order_id={offers[0]['order_id']}&decision=decline">Decline, refund instead</a></p>"""


    email = sib_api_v3_sdk.SendSmtpEmail(
        to=[{"email": to_email, "name": customer_name}],
        sender={"name": "OrderOps AI", "email": "sohaibshakeel796@gmail.com"},
        subject="Action needed: item substitution for your order",
        html_content=html_content,
    )

    try:
        api_instance.send_transac_email(email)
        print(f"[email] Sent negotiation offer to {to_email}")
        return True
    except ApiException as e:
        print(f"[email] Failed to send to {to_email}: {e}")
        return False