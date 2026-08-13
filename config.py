import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        "sqlite:///" + str(BASE_DIR / "instance" / "ipcms.db")
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID", "")
    RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET", "")
    RAZORPAY_WEBHOOK_SECRET = os.getenv("RAZORPAY_WEBHOOK_SECRET", "")
    RAZORPAY_CURRENCY = os.getenv("RAZORPAY_CURRENCY", "INR")
    RAZORPAY_AUTO_CAPTURE = os.getenv("RAZORPAY_AUTO_CAPTURE", "1") == "1"
