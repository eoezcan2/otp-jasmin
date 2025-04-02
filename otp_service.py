import os
import uuid
import smpplib.client
import smpplib.consts
import requests
from requests.auth import HTTPBasicAuth
import datetime
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Load environment variables from .env file (if it exists)
load_dotenv()

# Retrieve environment variables
DB_USER = os.getenv('DB_USER', 'default_user')  # Default values are used if env vars aren't found
DB_PASSWORD = os.getenv('DB_PASSWORD', 'default_password')
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_NAME = os.getenv('DB_NAME', 'otp_db')

# Database connection string
DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:3306/{DB_NAME}"

print(DATABASE_URL)

# Set up SQLAlchemy
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# API sends out SMS OTPs using a third-party service and saves information about the OTPs in the database
# OTP Model: id, phone number, text, provider, created_at
class OTP(Base):
    __tablename__ = "otp"

    id = Column(Integer, primary_key=True, index=True)
    provider = Column(String(50))
    phone_number = Column(String(15), index=True)
    text = Column(String(255))
    status = Column(String(50), default="pending")
    created_at = Column(DateTime, default=datetime.datetime.now)

# Create the database tables and update the schema if needed
Base.metadata.create_all(bind=engine)

# FastAPI instance
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:80", "http://localhost"],  # Allow only your frontend
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods (GET, POST, etc.)
    allow_headers=["*"],  # Allow all headers
)

sid = os.getenv('SMS_SERVICE_API_KEY')
auth_token = os.getenv('SMS_SERVICE_API_SECRET')

# POST Endpoint to send OTP
class OTPRequest(BaseModel):
    provider: str
    phone_number: str
    text: str

@app.post("/send_otp/")
async def send_otp(otp_request: OTPRequest):
    # Send the OTP via HTTP API Request
    request_url = f'https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json'
    request_body = {
        "From": os.getenv('SMS_SERVICE_FROM'),
        "To": otp_request.phone_number,
        "Body": otp_request.text
    }
    response = requests.post(request_url, data=request_body, auth=HTTPBasicAuth(sid, auth_token))
    response_json = response.json()
    print(response_json)

    # Save the OTP in the database
    db = SessionLocal()
    db_otp = OTP(phone_number=otp_request.phone_number, provider=otp_request.provider, text=otp_request.text)

    if response_json.get('error_code'):
        db_otp.status = "failed"
    else:
        db_otp.status = "sent"

    db.add(db_otp)
    db.commit()
    db.refresh(db_otp)
    db.close()

    return response_json

@app.get("/get_otp/")
async def get_otp():
    # Retrieve all OTPs from the database
    db = SessionLocal()
    otps = db.query(OTP).all()
    db.close()

    return otps
