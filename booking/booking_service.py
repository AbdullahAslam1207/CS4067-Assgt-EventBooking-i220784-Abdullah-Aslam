from typing import List
from fastapi import FastAPI, HTTPException, Depends, Query
from pydantic import BaseModel
import pika
import json
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import Column, Integer, String, MetaData, Table, select, update, insert
from fastapi.middleware.cors import CORSMiddleware
from pymongo import MongoClient

# PostgreSQL database connection for booking service
DATABASE_URL = "postgresql+asyncpg://postgres:1234@localhost:5432/booking_db"
engine = create_async_engine(DATABASE_URL, echo=True)
async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
metadata = MetaData()

# Define bookings table (PostgreSQL)
bookings_table = Table(
    "bookings", metadata,
    Column("id", Integer, primary_key=True, index=True),
    Column("user_id", Integer),
    Column("event_id", String),
    Column("tickets", Integer),
    Column("status", String),
)

app = FastAPI()

# CORS middleware to allow frontend requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5500"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Connect to MongoDB for payment records
payment_client = MongoClient("mongodb://localhost:27017/")
payment_db = payment_client["payment_db"]
payments_collection = payment_db["payment"]

# Booking request model
class BookingRequest(BaseModel):
    user_id: int
    event_id: str
    tickets: int

# Model for returning booking data
class Booking(BaseModel):
    id: int
    user_id: int
    event_id: str
    tickets: int
    status: str

# Payment request model
class PaymentRequest(BaseModel):
    user_id: int
    amount: int

# Dependency to get PostgreSQL database session
async def get_db():
    async with async_session() as session:
        yield session

# POST endpoint to create a booking
@app.post("/bookings")
async def create_booking(request: BookingRequest, db: AsyncSession = Depends(get_db)):
    print("Received booking request:", request.dict())
    
    # Save booking in PostgreSQL
    insert_query = bookings_table.insert().values(
        user_id=request.user_id,
        event_id=request.event_id,
        tickets=request.tickets,
        status="CONFIRMED"
    ).returning(bookings_table.c.id)
    
    try:
        result = await db.execute(insert_query)
        booking_id = result.scalar()
        await db.commit()
        print("Booking Saved with ID:", booking_id)
    except Exception as e:
        print("Error saving booking:", str(e))
        raise HTTPException(status_code=500, detail="Error saving booking")
    
    # Publish confirmation message to RabbitMQ (optional)
    booking_data = {
        "id": booking_id,
        "user_id": request.user_id,
        "event_id": request.event_id,
        "tickets": request.tickets,
        "status": "CONFIRMED"
    }
    try:
        connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
        channel = connection.channel()
        channel.queue_declare(queue='notification_queue')
        channel.basic_publish(exchange='', routing_key='notification_queue', body=json.dumps(booking_data))
        connection.close()
        print("Confirmation message published to RabbitMQ:", booking_data)
    except Exception as e:
        print("Error publishing to RabbitMQ:", str(e))
        raise HTTPException(status_code=500, detail="Error publishing notification")
    
    return {"message": "Booking confirmed", "booking_id": booking_id}

# GET endpoint to list all bookings (for debugging or admin)
@app.get("/bookings")
async def get_bookings(db: AsyncSession = Depends(get_db)):
    query = select(bookings_table)
    results = await db.execute(query)
    rows = results.fetchall()
    bookings = [dict(row._mapping) for row in rows]
    return bookings

# GET endpoint to list bookings for a specific user (confirmed and pending)
@app.get("/bookings/me", response_model=List[Booking])
async def get_my_bookings(
    user_id: int = Query(..., description="ID of the logged-in user"),
    db: AsyncSession = Depends(get_db)
):
    query = select(bookings_table).where(
        bookings_table.c.user_id == user_id,
        bookings_table.c.status.in_(["CONFIRMED", "PENDING"])
    )
    results = await db.execute(query)
    rows = results.fetchall()
    bookings = [dict(row._mapping) for row in rows]
    return bookings

# POST endpoint to process payment
@app.post("/payments")
async def process_payment(request: PaymentRequest, db: AsyncSession = Depends(get_db)):
    # Query bookings for the user with status CONFIRMED or PENDING
    query = select(bookings_table).where(
        bookings_table.c.user_id == request.user_id,
        bookings_table.c.status.in_(["CONFIRMED", "PENDING"])
    )
    results = await db.execute(query)
    rows = results.fetchall()
    bookings = [dict(row._mapping) for row in rows]
    
    if not bookings:
        raise HTTPException(status_code=404, detail="No pending bookings found for this user")
    
    # Calculate total due (each ticket costs ₹500)
    total_due = sum(booking["tickets"] * 500 for booking in bookings if booking["status"] in ["CONFIRMED", "PENDING"])
    if request.amount != total_due:
        raise HTTPException(status_code=400, detail=f"Amount does not match total due: ₹{total_due}")
    
    # Update each booking to 'PAID' and insert a payment record into MongoDB
    for booking in bookings:
        update_stmt = bookings_table.update().where(bookings_table.c.id == booking["id"]).values(status="PAID")
        await db.execute(update_stmt)
        payment_cost = booking["tickets"] * 500
        payment_document = {
            "user_id": request.user_id,
            "event_id": booking["event_id"],
            "cost": payment_cost
        }
        payments_collection.insert_one(payment_document)
    
    await db.commit()
    
    return {"message": "Payment successful and bookings updated", "total_paid": total_due}

# End of file
