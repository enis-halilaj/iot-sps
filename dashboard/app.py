from flask import Flask, render_template
from flask_socketio import SocketIO
from kafka import KafkaConsumer
import json
import threading
import time
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

# Socket.IO namespace for simulator
SIMULATOR_NAMESPACE = '/simulator'

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
    consumer = KafkaConsumer(
        'sensor_data',
        bootstrap_servers=['localhost:9092'],
        auto_offset_reset='latest',
        enable_auto_commit=True,
        group_id='dashboard-group',
        value_deserializer=lambda x: json.loads(x.decode('utf-8'))
    )
    
    logger.info("Starting Kafka consumer...")
    
    while True:
        try:
            for message in consumer:
                event = message.value
                logger.info(f"Received Kafka event: {event}")
                
                # Emit to all connected clients
                socketio.emit('kafka_event', event)
                socketio.emit('sensor_updated', event)
                logger.info(f"Emitted event to UI: {event['sensor_type']} = {event['value']}")
        except Exception as e:
            logger.error(f"Error consuming Kafka events: {e}")
            time.sleep(5)  # Wait before retrying

@socketio.on('connect')
def handle_connect():
    logger.info('Client connected to dashboard')

@socketio.on('disconnect')
def handle_disconnect():
    logger.info('Client disconnected from dashboard')

@socketio.on('connect', namespace=SIMULATOR_NAMESPACE)
def handle_simulator_connect():
    logger.info('Simulator connected')

@socketio.on('disconnect', namespace=SIMULATOR_NAMESPACE)
def handle_simulator_disconnect():
    logger.info('Simulator disconnected')

@socketio.on('update_sensor')
def handle_sensor_update(data):
    logger.info(f"Received sensor update from UI: {data}")
    # Forward the update to the simulator
    socketio.emit('update_sensor', data, namespace=SIMULATOR_NAMESPACE)
    # Also broadcast to all dashboard clients
    socketio.emit('sensor_updated', data)
    logger.info(f"Forwarded sensor update: {data}")

if __name__ == '__main__':
    # Start Kafka consumer in a background thread
    kafka_thread = threading.Thread(target=consume_kafka_events)
    kafka_thread.daemon = True
    kafka_thread.start()
    
    logger.info("Starting Flask app...")
    # Start Flask app
    socketio.run(app, debug=True, port=5000) 