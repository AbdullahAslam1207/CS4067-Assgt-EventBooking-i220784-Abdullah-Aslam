from fastapi import FastAPI, HTTPException
from pymongo import MongoClient

app = FastAPI()
client = MongoClient("mongodb://localhost:27017/")
db = client["event_db"]
events_collection = db["events"]

@app.get("/events")
def get_events():
    events = list(events_collection.find({}, {"_id": 0}))
    return events

@app.get("/events/{event_id}/availability")
def check_event_availability(event_id: str):
    event = events_collection.find_one({"event_id": event_id}, {"_id": 0})
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    available = event.get("available", False)  # Ensure the event document has an 'available' field
    return {"event_id": event_id, "available": available}
