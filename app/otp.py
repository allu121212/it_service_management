import random
from datetime import datetime, timedelta


def generate_otp() -> str:
    """Generate a 6-digit OTP code as a string."""
    return f"{random.randint(100000, 999999)}"


def otp_expiry(minutes: int = 15) -> datetime:
    """OTP expires after N minutes."""
    return datetime.utcnow() + timedelta(minutes=minutes)


def send_otp_email(to_email: str, otp_code: str, name: str) -> None:
    """
    In production, this would send an email via SMTP/SendGrid.
    For the demo, we print the OTP to the server terminal so the
    presenter can read it and demonstrate the flow.
    """
    print("\n" + "=" * 60)
    print(f"📧 OTP EMAIL — DEMO MODE")
    print(f"   To:      {to_email}")
    print(f"   Name:    {name}")
    print(f"   OTP:     {otp_code}")
    print(f"   Expires: 15 minutes")
    print("=" * 60 + "\n")