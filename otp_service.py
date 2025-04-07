import os
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, String, Integer, Table, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
import subprocess

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:80", "http://localhost"],  # Allow only your frontend
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods (GET, POST, etc.)
    allow_headers=["*"],  # Allow all headers
)

# Database setup
# Load environment variables from .env file (if it exists)
load_dotenv()

# Retrieve environment variables
DB_USER = os.getenv('DB_USER', 'default_user')  # Default values are used if env vars aren't found
DB_PASSWORD = os.getenv('DB_PASSWORD', 'default_password')
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_NAME = os.getenv('DB_NAME', 'otp_db')

# Database connection string
DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:3306/{DB_NAME}"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Models
class SMSProviderDB(Base):
    __tablename__ = "sms_providers"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(255), unique=True, index=True)
    host = Column(String(255))
    username = Column(String(255))
    password = Column(String(255))
    port = Column(Integer)

class ClientDB(Base):
    __tablename__ = "clients"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(255), unique=True, index=True)

class AllowedSenderDB(Base):
    __tablename__ = "allowed_senders"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    client_id = Column(Integer, ForeignKey("clients.id"))
    sender = Column(String(255))
    client = relationship("ClientDB", back_populates="allowed_senders")

ClientDB.allowed_senders = relationship("AllowedSenderDB", back_populates="client")

Base.metadata.create_all(bind=engine)

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class SMSProvider(BaseModel):
    name: str
    host: str
    username: str
    password: str
    port: int

class Client(BaseModel):
    name: str
    allowed_senders: list[str]

# Function to send commands to Jasmin CLI via telnet
def send_jasmin_command(command):
    try:
        tn = telnetlib.Telnet("jasmin", 8990)
        tn.read_until(b"jcli : ")
        tn.write(command.encode("ascii") + b"\n")
        time.sleep(1)
        response = tn.read_very_eager().decode("ascii")
        tn.close()
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error communicating with Jasmin CLI: {e}")

# Function to add an SMPP provider to Jasmin
def add_smpp_provider(provider: SMSProvider):
    connector_name = provider.name.replace(" ", "_").lower()
    send_jasmin_command(f"smppccm -a {connector_name}")
    send_jasmin_command(f"smppccm -u {connector_name} -p host {provider.host}")
    send_jasmin_command(f"smppccm -u {connector_name} -p port {provider.port}")
    send_jasmin_command(f"smppccm -u {connector_name} -p username {provider.username}")
    send_jasmin_command(f"smppccm -u {connector_name} -p password {provider.password}")
    send_jasmin_command("smppccm -1")

# Endpoint to add an SMS provider
@app.post("/add_provider/")
def add_provider(provider: SMSProvider, db: SessionLocal = Depends(get_db)):
    db_provider = SMSProviderDB(**provider.dict())
    db.add(db_provider)
    db.commit()
    db.refresh(db_provider)
    add_smpp_provider(provider)
    return {"message": "SMS provider added successfully"}

# Endpoint to register a client
@app.post("/add_client/")
def add_client(client: Client, db: SessionLocal = Depends(get_db)):
    db_client = ClientDB(name=client.name)
    db.add(db_client)
    db.commit()
    db.refresh(db_client)
    for sender in client.allowed_senders:
        db_sender = AllowedSenderDB(client_id=db_client.id, sender=sender)
        db.add(db_sender)
    db.commit()
    return {"message": "Client registered successfully"}

# Endpoint to remove a client
@app.delete("/remove_client/{client_name}")
def remove_client(client_name: str, db: SessionLocal = Depends(get_db)):
    db_client = db.query(ClientDB).filter(ClientDB.name == client_name).first()
    if not db_client:
        raise HTTPException(status_code=404, detail="Client not found")
    db.query(AllowedSenderDB).filter(AllowedSenderDB.client_id == db_client.id).delete()
    db.delete(db_client)
    db.commit()
    return {"message": "Client removed successfully"}

# Endpoint to list providers
@app.get("/list_providers/")
def list_providers(db: SessionLocal = Depends(get_db)):
    return db.query(SMSProviderDB).all()

# Endpoint to list clients
@app.get("/list_clients/")
def list_clients(db: SessionLocal = Depends(get_db)):
    return db.query(ClientDB).all()
