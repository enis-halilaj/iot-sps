# IoT Data Pipeline

This project implements a complete IoT data pipeline using Kafka, Spark, and Cassandra. It simulates sensor data, processes it in real-time, and stores the results.

## Architecture

- **Sensor Simulator**: Python-based simulator that generates random sensor data
- **Apache Kafka**: Message broker for handling sensor data streams
- **Apache Spark**: Stream processing engine for real-time data analysis
- **Apache Cassandra**: Time-series database for storing processed data

## Prerequisites

- Docker and Docker Compose
- Python 3.8+
- pip (Python package manager)

## Setup

1. Install Python dependencies:
```bash
pip install -r requirements.txt
```

2. Start the infrastructure:
```bash
docker-compose up -d
```

3. Create Cassandra keyspace and table:
```sql
cqlsh -e "
CREATE KEYSPACE IF NOT EXISTS iot_data WITH replication = {'class': 'SimpleStrategy', 'replication_factor': 1};

CREATE TABLE IF NOT EXISTS iot_data.sensor_aggregates (
    window_start timestamp,
    window_end timestamp,
    sensor_type text,
    avg_value double,
    min_value double,
    max_value double,
    PRIMARY KEY ((sensor_type), window_start, window_end)
);"
```

## Running the System

1. Start the sensor simulator:
```bash
python sensor_simulator.py
```

2. Start the Spark processor:
```bash
python spark_processor.py
```

## Monitoring

- Kafka: http://localhost:9092
- Spark UI: http://localhost:8080
- Cassandra: localhost:9042

## Data Flow

1. The sensor simulator generates random sensor data and sends it to Kafka
2. Spark reads the data from Kafka, processes it in real-time
3. Processed data is stored in Cassandra with aggregations by time window

## Data Structure

The sensor data includes:
- Sensor ID
- Sensor Type (temperature, humidity, pressure, light, motion)
- Value
- Timestamp
- Location (latitude, longitude)
- Metadata (manufacturer, model, battery level)

## Stopping the System

1. Stop the Python processes (Ctrl+C)
2. Stop the infrastructure:
```bash
docker-compose down
``` 