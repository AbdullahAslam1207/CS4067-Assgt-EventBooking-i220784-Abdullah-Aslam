from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from pymongo import MongoClient
from bson import ObjectId
from typing import List, Optional
from datetime import date
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# CORS middleware to allow frontend requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5500"],  # Adjust this to your frontend's origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Set up MongoDB connection using PyMongo
client = MongoClient("mongodb://localhost:27017/")
db = client["events_db"]  # Replace with your actual database name
events_collection = db["events"]

print("Connected to MongoDB: events_db")

# Event model
class Event(BaseModel):
    id: Optional[str] = None
    name: str
    venue: str
    date: date  # Using a proper date type

    class Config:
        allow_population_by_field_name = True
        extra = "forbid"  # Forbid extra fields except those defined
        json_encoders = {
            ObjectId: str,
            date: lambda v: v.isoformat()
        }

# Endpoint to list all events
@app.get("/events", response_model=List[Event])
def list_events():
    events = []
    for doc in events_collection.find():
        # Convert ObjectId to string and store in 'id'
        doc["id"] = str(doc["_id"])
        doc.pop("_id", None)
        if "venue" not in doc:
            doc["venue"] = "Unknown"
        events.append(doc)
    return events

# Endpoint to create a new event
@app.post("/events", response_model=Event)
def create_event(event: Event):
    event_dict = event.dict(by_alias=True)
    print("Received event creation request:", event_dict)
    event_dict.pop("_id", None)
    result = events_collection.insert_one(event_dict)
    created_event = events_collection.find_one({"_id": result.inserted_id})
    print("Event created successfully with ID:", result.inserted_id)
    # Convert _id to id
    if created_event and "_id" in created_event:
        created_event["id"] = str(created_event["_id"])
        created_event.pop("_id", None)
    return Event(**created_event)

# Endpoint to delete an event
@app.delete("/events/{id}")
def delete_event(id: str):
    print(f"Received delete request for event ID: {id}")
    result = events_collection.delete_one({"_id": ObjectId(id)})
    if result.deleted_count == 0:
        print("Event not found:", id)
        raise HTTPException(status_code=404, detail="Event not found")
    print("Event deleted successfully:", id)
    return {"message": "Event deleted successfully"}

# Run the app with: uvicorn your_file_name:app --reload