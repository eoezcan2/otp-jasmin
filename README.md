# OTP Service API

This project provides an infrastructure for receiving and sending one-time passwords (OTPs) via SMS. The backend is built with FastAPI and integrates with an SMPP service for OTP delivery.

## Features
- Receive OTPs from different providers
- Store OTPs in a MySQL/PostgreSQL database
- Send OTPs via SMPP
- REST API for integration with a control panel
- Logging and status tracking

## Prerequisites
- Python 3.x
- MySQL or PostgreSQL database
- SMPP server for sending messages

## Setup Instructions

### 1. Clone the Repository
```bash
git clone https://github.com/your-repo/otp-service.git
cd otp-service
```

### 2. Create a Virtual Environment
```bash
python -m venv venv
```

### 3. Activate the Virtual Environment
- **Windows**:
  ```bash
  venv\Scripts\activate
  ```
- **Mac/Linux**:
  ```bash
  source venv/bin/activate
  ```

### 4. Install Dependencies
```bash
pip install -r requirements.txt
```

### 5. Configure the Database
Update the `DATABASE_URL` in `otp_service.py` to match your MySQL/PostgreSQL connection string:
```python
DATABASE_URL = "mysql+pymysql://user:password@localhost/otp_db"
```

### 6. Run the FastAPI Server
```bash
uvicorn otp_service:app --host 0.0.0.0 --port 8000 --reload
```

### 7. Access the API
- Swagger UI: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- ReDoc: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

## Running with Docker (Optional)
If you prefer using Docker, create a `Dockerfile` and `docker-compose.yml`.

## License
This project is licensed under the MIT License.

---

Now your OTP service is ready! 🚀
