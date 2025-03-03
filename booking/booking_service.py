from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
import requests
import pika
import json
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import Column, Integer, String, Float, MetaData, Table

DATABASE_URL = "postgresql+asyncpg://postgres:1234@localhost:5432/booking_db"

engine = create_async_engine(DATABASE_URL, echo=True)
async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
metadata = MetaData()

bookings_table = Table(
    "bookings", metadata,
    Column("id", Integer, primary_key=True, index=True),
    Column("user_id", Integer),
    Column("event_id", String),
    Column("tickets", Integer),
    Column("status", String),
)

app = FastAPI()

class BookingRequest(BaseModel):
    user_id: int
    event_id: str
    tickets: int

class PaymentRequest(BaseModel):
    user_id: int
    amount: float

async def get_db():
    async with async_session() as session:
        yield session

@app.post("/bookings")
async def create_booking(request: BookingRequest, db: AsyncSession = Depends(get_db)):
    event_availability = requests.get(f"http://localhost:8001/events/{request.event_id}/availability").json()
    if not event_availability.get("available"):
        raise HTTPException(status_code=400, detail="Event is fully booked")

    # Call the payment service
    payment_response = requests.post("http://localhost:8004/payments", json={"user_id": request.user_id, "amount": 100}).json()
    if payment_response.get("status") != "SUCCESS":
        raise HTTPException(status_code=400, detail="Payment failed")

    # Save booking in PostgreSQL
    insert_query = bookings_table.insert().values(
        user_id=request.user_id,
        event_id=request.event_id,
        tickets=request.tickets,
        status="CONFIRMED"
    ).returning(bookings_table.c.id)

    result = await db.execute(insert_query)
    booking_id = result.scalar()
    await db.commit()
    await db.flush()  # Add this to ensure data is written

    # Publish confirmation message to RabbitMQ
    connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
    channel = connection.channel()
    channel.queue_declare(queue='notification_queue')
    
    booking_data = {
        "id": booking_id,
        "user_id": request.user_id,
        "event_id": request.event_id,
        "tickets": request.tickets,
        "status": "CONFIRMED"
    }
    channel.basic_publish(exchange='', routing_key='notification_queue', body=json.dumps(booking_data))
    connection.close()

    return {"message": "Booking confirmed", "booking_id": booking_id}