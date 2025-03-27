from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import smpplib.client
import smpplib.consts
import uuid

# Database setup
DATABASE_URL = "mysql+pymysql://user:password@localhost/otp_db"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Models
class OTP(Base):
    __tablename__ = "otps"
    id = Column(Integer, primary_key=True, index=True)
    provider = Column(String, index=True)
    otp_code = Column(String, index=True)
    phone_number = Column(String, index=True)
    status = Column(String, default="pending")

Base.metadata.create_all(bind=engine)

# FastAPI setup
app = FastAPI()

# Request Models
class OTPRequest(BaseModel):
    provider: str
    phone_number: str
    otp_code: str

# SMPP Client Setup
def send_sms_via_smpp(phone_number: str, otp_code: str):
    client = smpplib.client.Client("smpp.server.com", 2775)
    client.connect()
    client.bind_transmitter(system_id="smpp_user", password="smpp_pass")

    message_id = uuid.uuid4().hex
    client.send_message(
        source_addr="OTPService",
        destination_addr=phone_number,
        short_message=f"Your OTP is: {otp_code}",
        esm_class=smpplib.consts.SMPP_MSGTYPE_DEFAULT,
    )

    client.unbind()
    client.disconnect()
    return message_id

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
