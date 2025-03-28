import os
import uuid
import smpplib.client
import smpplib.consts
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, Boolean
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
DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}"

# Set up SQLAlchemy
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Models
class OTP(Base):
    __tablename__ = "otps"
    id = Column(Integer, primary_key=True, index=True)
    provider = Column(String(255), index=True)
    otp_code = Column(String(6), index=True)
    phone_number = Column(String(15), index=True)
    status = Column(String(255), default="pending")

Base.metadata.create_all(bind=engine)

# Request Models
class OTPRequest(BaseModel):
    provider: str
    phone_number: str
    otp_code: str

# SMPP Client Setup
def send_sms_via_smpp(phone_number: str, otp_code: str):
    print("Sending OTP via SMPP...")
    # Connect to Jasmin SMPP Gateway running on local server
    client = smpplib.client.Client("localhost", 2775)  # Adjust the host to localhost
    client.connect()
    print("Connected to SMPP Gateway")

    # Bind as a transmitter to Jasmin using the correct system_id and password
    sys_id = os.getenv('SMPP_USER', 'user')
    pwd = os.getenv('SMPP_PASSWORD', 'pass')
    print(f"Binding as a transmitter with system_id: {sys_id} and password: {pwd}")

    client.bind_transmitter(system_id=sys_id, password=pwd)
    print("Bound as a transmitter")


    # Create a unique message ID for the OTP request
    message_id = uuid.uuid4().hex

    # Send the OTP message
    client.send_message(
        source_addr="OTPService",  # Sender ID (can be configured in Jasmin)
        destination_addr=phone_number,  # Recipient phone number
        short_message=f"Your OTP is: {otp_code}",  # The OTP message
        esm_class=smpplib.consts.SMPP_MSGTYPE_DEFAULT,  # Default message type
    )
    print("OTP message sent successfully")

    # Unbind from the SMPP service and disconnect
    client.unbind()
    client.disconnect()
    print("Disconnected from SMPP Gateway")

    return message_id

# FastAPI setup
app = FastAPI()

# API Endpoints
@app.post("/send-otp/")
def send_otp(request: OTPRequest):
    db = SessionLocal()
    otp_entry = OTP(provider=request.provider, phone_number=request.phone_number, otp_code=request.otp_code, status="sent")
    db.add(otp_entry)
    db.commit()
    db.refresh(otp_entry)

    try:
        send_sms_via_smpp(request.phone_number, request.otp_code)
        otp_entry.status = "delivered"
    except Exception as e:
        otp_entry.status = "failed"
        db.commit()
        db.close()
        raise HTTPException(status_code=500, detail=str(e))

    db.commit()
    db.close()
    return {"message": "OTP sent successfully", "id": otp_entry.id}

@app.get("/logs/")
def get_logs():
    db = SessionLocal()
    logs = db.query(OTP).all()
    db.close()
    return logs
