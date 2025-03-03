from fastapi import FastAPI, HTTPException
from pymongo import MongoClient
from pydantic import BaseModel

app = FastAPI()

# MongoDB Connection
client = MongoClient("mongodb://localhost:27017/")
db = client["payment_db"]
payments_collection = db["payments"]

class PaymentRequest(BaseModel):
    user_id: int
    amount: float

@app.post("/payments")
async def process_payment(request: PaymentRequest):
    if request.amount <= 0:
        raise HTTPException(status_code=400, detail="Invalid payment amount")

    # Store the payment in MongoDB
    payment = {
        "user_id": request.user_id,
        "amount": request.amount,
        "status": "SUCCESS"
    }
    result = payments_collection.insert_one(payment)

    return {
        "status": "SUCCESS",
        
    }
