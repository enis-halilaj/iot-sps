import random
import json
import time
import logging
from datetime import datetime
from kafka import KafkaProducer
from socketio import Client

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Kafka configuration
KAFKA_BOOTSTRAP_SERVERS = ['localhost:9092']
KAFKA_TOPIC = 'sensor_data'

# Socket.IO server configuration
SOCKETIO_SERVER = 'http://localhost:5000'
SOCKETIO_NAMESPACE = '/simulator'

# Fixed event rate (events per second)
EVENT_RATE = 1

# Sensor metadata
SENSOR_METADATA = {
    'occupancy': {
        'unit': '%',
        'description': 'Parking spot occupancy status',
        'min': 0,
        'max': 1,
        'default': 0
    },
    'distance': {
        'unit': 'cm',
        'description': 'Distance to next car',
        'min': 0,
        'max': 500,
        'default': 100
    },
    'temperature': {
        'unit': '°C',
        'description': 'Temperature in parking area',
        'min': -10,
        'max': 50,
        'default': 25
    },
    'light': {
        'unit': 'lux',
        'description': 'Light level in parking area',
        'min': 0,
        'max': 1000,
        'default': 500
    },
    'cars_per_sqm': {
        'unit': 'cars/m²',
        'description': 'Car density in parking area',
        'min': 0,
        'max': 0.5,
        'default': 0.1
    },
    'avg_speed': {
        'unit': 'km/h',
        'description': 'Average car speed in parking area',
        'min': 0,
        'max': 20,
        'default': 5
    },
    'co2_level': {
        'unit': 'ppm',
        'description': 'CO2 concentration in parking area',
        'min': 300,
        'max': 2000,
        'default': 400
    },
    'noise_level': {
        'unit': 'dB',
        'description': 'Ambient noise level',
        'min': 30,
        'max': 100,
        'default': 50
    },
    'humidity': {
        'unit': '%',
        'description': 'Relative humidity in parking area',
        'min': 0,
        'max': 100,
        'default': 50
    },
    'wait_time': {
        'unit': 'min',
        'description': 'Average wait time to find parking',
        'min': 0,
        'max': 30,
        'default': 5
    }
}

# Initialize sensor values
sensor_values = {sensor: metadata['default'] for sensor, metadata in SENSOR_METADATA.items()}

# Initialize Kafka producer
producer = KafkaProducer(
    bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
    value_serializer=lambda x: json.dumps(x).encode('utf-8')
)

# Initialize Socket.IO client
sio = Client()

@sio.event(namespace=SOCKETIO_NAMESPACE)
def connect():
    logger.info('Connected to dashboard')

@sio.event(namespace=SOCKETIO_NAMESPACE)
def disconnect():
    logger.info('Disconnected from dashboard')

@sio.on('update_sensor', namespace=SOCKETIO_NAMESPACE)
def handle_sensor_update(data):
    sensor_type = data['sensor_type']
    value = data['value']
    sensor_values[sensor_type] = value
    logger.info(f"Updated {sensor_type} to {value} from UI")
    
    # Send the updated value to Kafka
    event = {
        'timestamp': datetime.utcnow().isoformat(),
        'sensor_type': sensor_type,
        'value': value,
        'metadata': {
            'unit': SENSOR_METADATA[sensor_type]['unit'],
            'description': SENSOR_METADATA[sensor_type]['description']
        },
        'location': {
            'parking_lot': 'A',
            'floor': '1',
            'section': 'B'
        }
    }
    
    producer.send(KAFKA_TOPIC, event)
    producer.flush()

def generate_sensor_value(sensor_type):
    """Generate a random value for a given sensor type within its defined range."""
    metadata = SENSOR_METADATA[sensor_type]
    current_value = sensor_values[sensor_type]
    
    # Generate a small random change (-10% to +10% of the range)
    range_size = metadata['max'] - metadata['min']
    max_change = range_size * 0.1
    change = random.uniform(-max_change, max_change)
    
    # Apply change while staying within bounds
    new_value = current_value + change
    new_value = max(metadata['min'], min(metadata['max'], new_value))
    
    # Update stored value
    sensor_values[sensor_type] = new_value
    
    return new_value

def generate_and_send():
    """Generate and send sensor data to Kafka."""
    while True:
        try:
            # Generate events for all sensors
            for sensor_type in SENSOR_METADATA.keys():
                value = generate_sensor_value(sensor_type)
                
                # Create event
                event = {
                    'timestamp': datetime.utcnow().isoformat(),
                    'sensor_type': sensor_type,
                    'value': value,
                    'metadata': {
                        'unit': SENSOR_METADATA[sensor_type]['unit'],
                        'description': SENSOR_METADATA[sensor_type]['description']
                    },
                    'location': {
                        'parking_lot': 'A',
                        'floor': '1',
                        'section': 'B'
                    }
                }
                
                # Convert to JSON string for logging
                event_json = json.dumps(event, indent=2)
                logger.info(f"Generated event:\n{event_json}")
                
                # Send to Kafka
                producer.send(KAFKA_TOPIC, event)
                producer.flush()
            
            # Sleep for fixed rate
            time.sleep(1/EVENT_RATE)
            
        except Exception as e:
            logger.error(f"Error generating/sending sensor data: {e}")
            time.sleep(5)  # Wait before retrying

if __name__ == '__main__':
    try:
        # Connect to dashboard with namespace
        sio.connect(SOCKETIO_SERVER, namespaces=[SOCKETIO_NAMESPACE])
        
        # Start generating and sending sensor data
        generate_and_send()
    except KeyboardInterrupt:
        logger.info("Shutting down sensor simulator...")
        producer.close()
        sio.disconnect()
    except Exception as e:
        logger.error(f"Error in main loop: {e}")
        producer.close()
        sio.disconnect() 