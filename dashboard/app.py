from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
from kafka import KafkaConsumer
import json
import threading
import time
import logging
from datetime import datetime
from twilio.rest import Client

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading', logger=True, engineio_logger=True)

# Socket.IO namespace for simulator
SIMULATOR_NAMESPACE = '/simulator'

# Twilio configuration
TWILIO_ACCOUNT_SID = 'ACb972fa95bb0f7612a60d4c35adc8bdde'  # Replace with your Twilio Account SID
TWILIO_AUTH_TOKEN = 'd48051018e8b14b53534c78801d87dce'    # Replace with your Twilio Auth Token
TWILIO_PHONE_NUMBER = '+16074007927'  # Your Twilio phone number
RECIPIENT_PHONE_NUMBER = '+38345988114'  # The phone number to receive SMS

# Initialize Twilio client
twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

def send_sms_alert(message):
    """Send SMS alert using Twilio"""
    try:
        message = twilio_client.messages.create(
            body=message,
            from_=TWILIO_PHONE_NUMBER,
            to=RECIPIENT_PHONE_NUMBER
        )
        logger.info(f"SMS sent successfully: {message.sid}")
    except Exception as e:
        logger.error(f"Error sending SMS: {e}")

def check_distance_alarm(data):
    """Check if distance sensor reading requires an alarm"""
    if data['sensor_type'] == 'distance':
        value = data['value']
        # Critical threshold: distance less than 50cm
        if value < 50:
            location = data['location']
            message = f"CRITICAL ALERT: Distance to next car is {value:.2f}cm at {location['parking_lot']}, Floor {location['floor']}, Section {location['section']}"
            # send_sms_alert(message)
            return True
    return False

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/monitor')
def monitor():
    return render_template('kafka-monitor.html')

@app.route('/alarms')
def alarms():
    return render_template('alarms.html')

def consume_kafka_events():
    """Consume events from Kafka and emit them to connected clients"""
    while True:
        try:
            logger.info("Attempting to connect to Kafka...")
            consumer = KafkaConsumer(
                'sensor_data',
                bootstrap_servers=['localhost:9092'],
                auto_offset_reset='latest',
                enable_auto_commit=True,
                group_id='dashboard_group',
                value_deserializer=lambda x: json.loads(x.decode('utf-8'))
            )
            
            logger.info("Successfully connected to Kafka")
            
            for message in consumer:
                try:
                    data = message.value
                    logger.info(f"Received Kafka event: {data}")
                    
                    # Create a copy of the data with timestamp
                    event_data = {
                        **data,
                        'timestamp': datetime.now().isoformat()
                    }
                    
                    # Check for distance alarms
                    if check_distance_alarm(event_data):
                        logger.info("Distance alarm triggered, SMS sent")
                    
                    # Emit the event to all connected clients
                    with app.app_context():
                        logger.info("Broadcasting event to all clients")
                        socketio.emit('sensor_updated', event_data, namespace='/')
                        logger.info("Event broadcast complete")
                except Exception as e:
                    logger.error(f"Error processing Kafka message: {e}", exc_info=True)
                    
        except Exception as e:
            logger.error(f"Error in Kafka consumer: {e}", exc_info=True)
            logger.info("Retrying connection in 5 seconds...")
            time.sleep(5)  # Wait before retrying

@socketio.on('connect')
def handle_connect():
    logger.info('Client connected')

@socketio.on('disconnect')
def handle_disconnect():
    logger.info('Client disconnected')

@socketio.on('connect', namespace=SIMULATOR_NAMESPACE)
def handle_simulator_connect():
    logger.info('Simulator connected')

@socketio.on('disconnect', namespace=SIMULATOR_NAMESPACE)
def handle_simulator_disconnect():
    logger.info('Simulator disconnected')

@socketio.on('update_sensor')
def handle_sensor_update(data):
    logger.info(f"Received sensor update from client: {data}")
    # Forward the update to the simulator
    socketio.emit('update_sensor', data, namespace=SIMULATOR_NAMESPACE)
    # Broadcast to all dashboard clients
    socketio.emit('sensor_updated', data, namespace='/')
    logger.info("Sensor update broadcast complete")

if __name__ == '__main__':
    # Start Kafka consumer in a background thread
    kafka_thread = threading.Thread(target=consume_kafka_events, daemon=True)
    kafka_thread.start()
    
    logger.info("Starting Flask app...")
    # Start Flask app
    socketio.run(app, debug=True, port=5000) 