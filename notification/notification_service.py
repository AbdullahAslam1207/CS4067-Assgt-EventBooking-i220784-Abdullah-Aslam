from fastapi import FastAPI, BackgroundTasks
import pika
import json
from pymongo import MongoClient
import asyncio

app = FastAPI()
client = MongoClient("mongodb://localhost:27017/")
db = client["notification_db"]
notifications_collection = db["notifications"]

async def process_messages():
    connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
    channel = connection.channel()
    channel.queue_declare(queue='notification_queue')

    def callback(ch, method, properties, body):
        try:
            booking = json.loads(body.decode("utf-8"))
            notifications_collection.insert_one(booking)
            print(f"Notification stored for booking {booking['_id']}")
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON: {e}")

    channel.basic_consume(queue='notification_queue', on_message_callback=callback, auto_ack=True)
    print("RabbitMQ Consumer started...")
    
    # Run consuming in an async event loop
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, channel.start_consuming)

def publish_message(queue_name, message):
    connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
    channel = connection.channel()
    channel.queue_declare(queue=queue_name)
    channel.basic_publish(exchange='', routing_key=queue_name, body=json.dumps(message))
    connection.close()


@app.on_event("startup")
async def startup_event():
    asyncio.create_task(process_messages())  # Run the consumer as a background task
