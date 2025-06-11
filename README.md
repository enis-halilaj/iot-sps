# IoT Smart Parking System

A real-time parking monitoring system that simulates sensor data, processes it through Kafka and Spark, and visualizes it through a web dashboard.

## System Architecture

The system consists of these core components:

1. **Sensor Simulator**: Python-based simulator generating parking sensor data
2. **Kafka**: Message broker for real-time data streaming
3. **Spark**: Stream processing engine for data aggregation
4. **Cassandra**: Database for storing processed data
5. **Web Dashboard**: Real-time visualization and monitoring interface

## Components in Detail

### 1. Sensor Simulator (`sensor_simulator.py`)

The sensor simulator generates realistic parking sensor data with these implemented features:

#### Sensor Types
- **Occupancy** (0-100%): Parking spot availability
- **Distance** (0-500cm): Space between parked cars
- **Temperature** (-10°C to 50°C): Parking area temperature
- **Light** (0-1000 lux): Ambient light levels
- **Cars per Square Meter** (0-0.5 cars/m²): Parking density
- **Average Speed** (0-20 km/h): Vehicle movement speed
- **CO2 Level** (300-2000 ppm): Air quality
- **Noise Level** (30-100 dB): Ambient noise
- **Humidity** (0-100%): Moisture levels
- **Wait Time** (0-30 minutes): Parking search time

#### Data Generation
```python
def generate_sensor_value(sensor_type):
    metadata = SENSOR_METADATA[sensor_type]
    current_value = sensor_values[sensor_type]
    range_size = metadata['max'] - metadata['min']
    max_change = range_size * 0.1
    change = random.uniform(-max_change, max_change)
    new_value = current_value + change
    new_value = max(metadata['min'], min(metadata['max'], new_value))
    return new_value
```

#### Communication
- Sends data to Kafka topic 'sensor_data'
- Connects to dashboard via Socket.IO
- Supports manual value updates through dashboard

### 2. Kafka Message Broker

Implemented with these configurations:
```yaml
kafka:
  image: confluentinc/cp-kafka:latest
  ports:
    - "9092:9092"
  environment:
    KAFKA_BROKER_ID: 1
    KAFKA_ZOOKEEPER_CONNECT: zookeeper:2181
    KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://kafka:29092,PLAINTEXT_HOST://localhost:9092
```

### 3. Spark Processing Engine (`spark_processor.py`)

Implements real-time data processing with:

```python
def process_stream(spark):
    # Read from Kafka
    df = spark.readStream \
        .format("kafka") \
        .option("kafka.bootstrap.servers", "localhost:9092") \
        .option("subscribe", "sensor_data") \
        .load()

    # Process data in 1-minute windows
    windowed_df = parsed_df \
        .withWatermark("timestamp", "1 minute") \
        .groupBy(
            window("timestamp", "1 minute"),
            "sensor_type"
        ) \
        .agg(
            avg("value").alias("avg_value"),
            min("value").alias("min_value"),
            max("value").alias("max_value")
        )
```

Features:
- 1-minute sliding windows
- Aggregations: average, minimum, maximum values
- Direct writing to Cassandra

### 4. Cassandra Database

Implemented schema:
```sql
CREATE KEYSPACE iot_data WITH replication = {
    'class': 'SimpleStrategy',
    'replication_factor': 1
};

CREATE TABLE sensor_aggregates (
    window_start timestamp,
    window_end timestamp,
    sensor_type text,
    avg_value double,
    min_value double,
    max_value double,
    PRIMARY KEY ((sensor_type), window_start, window_end)
);
```

### 5. Web Dashboard

Implemented features:
- Real-time sensor data display
- Historical data visualization
- Interactive controls for sensor simulation
- Alarm configuration and monitoring
- Filtering and search capabilities

## Data Flow

1. **Data Generation**:
   - Sensor simulator generates data
   - Data includes timestamp, sensor type, value, and metadata
   - Data is sent to Kafka topic

2. **Data Processing**:
   - Spark reads from Kafka
   - Applies 1-minute windows
   - Calculates aggregations
   - Writes results to Cassandra

3. **Data Storage**:
   - Raw data in Kafka (temporary)
   - Aggregated data in Cassandra (long-term)

4. **Data Visualization**:
   - Real-time updates via Socket.IO
   - Historical data queries from Cassandra
   - Interactive dashboard display

## Setup and Installation

1. **Prerequisites**:
   - Docker and Docker Compose
   - Python 3.11+
   - Virtual environment

2. **Installation**:
   ```bash
   # Clone the repository
   git clone <repository-url>
   cd iot-parking-system

   # Create virtual environment
   python -m venv venv
   source venv/bin/activate  # or `venv\Scripts\activate` on Windows

   # Install dependencies
   pip install -r requirements.txt
   ```

3. **Start Services**:
   ```bash
   docker-compose up -d
   ```

4. **Run Components**:
   ```bash
   # Start sensor simulator
   python sensor_simulator.py

   # Start Spark processor
   python spark_processor.py

   # Start dashboard
   cd dashboard
   python app.py
   ```

## Monitoring

1. **Kafka Monitoring**:
   - Access Kafka Manager at `localhost:9092`
   - Monitor topic partitions and consumer groups

2. **Spark Monitoring**:
   - Access Spark UI at `localhost:8080`
   - Monitor jobs and stages

3. **Cassandra Monitoring**:
   - Use `nodetool` for cluster status
   - Monitor keyspace metrics

4. **System Logs**:
   - Check component-specific log files
   - Monitor error rates and system health
