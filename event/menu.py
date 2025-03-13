import requests
import json
import os
from datetime import datetime

# Update BASE_URL to match your FastAPI service URL
BASE_URL = "http://127.0.0.1:8001/events"

def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")

def create_event():
    print("\n--- Create Event ---")
    name = input("Enter event name: ")
    venue = input("Enter event venue: ")
    date_str = input("Enter event date (YYYY-MM-DD): ")
    
    # Validate date format
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        print("❌ Invalid date format! Use YYYY-MM-DD.")
        return
    
    data = {"name": name, "venue": venue, "date": date_str}
    try:
        response = requests.post(BASE_URL, json=data)
        print("Response:", response.json())
    except Exception as e:
        print("Error creating event:", e)

def list_events():
    print("\n--- List All Events ---")
    try:
        response = requests.get(BASE_URL)
    except Exception as e:
        print("Error fetching events:", e)
        return

    if response.status_code == 200:
        events = response.json()
        if not events:
            print("⚠️ No events found.")
        else:
            print("📅 Events List:")
            for event in events:
                print(f"🆔 ID: {event.get('_id')}")
                print(f"📛 Name: {event.get('name')}")
                print(f"📍 Venue: {event.get('venue')}")
                print(f"📆 Date: {event.get('date')}")
                print("-" * 40)
    else:
        print("❌ Failed to fetch events. Status Code:", response.status_code)
        print("Response:", response.text)

def update_event():
    list_events()
    print("\n--- Update Event ---")
    event_id = input("Enter event ID to update: ")
    name = input("Enter new event name (leave blank to skip): ")
    venue = input("Enter new event venue (leave blank to skip): ")
    date_str = input("Enter new event date (YYYY-MM-DD, leave blank to skip): ")
    
    data = {}
    if name:
        data["name"] = name
    if venue:
        data["venue"] = venue
    if date_str:
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
            data["date"] = date_str
        except ValueError:
            print("❌ Invalid date format! Use YYYY-MM-DD.")
            return

    try:
        response = requests.put(f"{BASE_URL}/{event_id}", json=data)
        print("Response:", response.json())
    except Exception as e:
        print("Error updating event:", e)

def delete_event():
    print("\n--- Delete Event ---")
    event_id = input("Enter event ID to delete: ")
    try:
        response = requests.delete(f"{BASE_URL}/{event_id}")
        print("Response:", response.json())
    except Exception as e:
        print("Error deleting event:", e)

def menu():
    while True:
        clear_screen()
        print("\n🎟️ Event Management CLI 🎟️")
        print("1. Create Event")
        print("2. List All Events")
        print("3. Update Event")
        print("4. Delete Event")
        print("5. Exit")
        choice = input("\nEnter choice: ")
        
        if choice == "1":
            create_event()
        elif choice == "2":
            list_events()
        elif choice == "3":
            update_event()
        elif choice == "4":
            delete_event()
        elif choice == "5":
            print("👋 Exiting... Goodbye!")
            break
        else:
            print("❌ Invalid choice. Try again.")
        
        input("\nPress Enter to continue...")  # Pause before showing menu again

if __name__ == "__main__":
    menu()
