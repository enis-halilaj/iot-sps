from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col, window, to_timestamp, avg, min, max
from pyspark.sql.types import StructType, StructField, StringType, DoubleType, TimestampType, MapType

# Define the schema for our sensor data
schema = StructType([
    StructField("sensor_id", StringType()),
    StructField("sensor_type", StringType()),
    StructField("value", DoubleType()),
    StructField("timestamp", StringType()),
    StructField("location", MapType(StringType(), DoubleType())),
    StructField("metadata", MapType(StringType(), StringType()))
])

def create_spark_session():
    return (SparkSession.builder
            .appName("IoT Sensor Data Processor")
            .config("spark.jars.packages", "org.apache.spark:spark-sql-kafka-0-10_2.12:3.4.1,com.datastax.spark:spark-cassandra-connector_2.12:3.4.1")
            .config("spark.cassandra.connection.host", "localhost")
            .config("spark.cassandra.connection.port", "9042")
            .getOrCreate())

def process_stream(spark):
    # Read from Kafka
    df = spark.readStream \
        .format("kafka") \
        .option("kafka.bootstrap.servers", "localhost:9092") \
        .option("subscribe", "sensor_data") \
        .option("startingOffsets", "latest") \
        .load()

    # Parse JSON and cast timestamp
    parsed_df = df.select(
        from_json(col("value").cast("string"), schema).alias("data")
    ).select(
        "data.sensor_id",
        "data.sensor_type",
        "data.value",
        to_timestamp("data.timestamp").alias("timestamp"),  # Cast to timestamp
        "data.location",
        "data.metadata"
    )

    # Apply watermark and window
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

    # Add window_start and window_end columns
    windowed_df = windowed_df \
        .withColumn("window_start", col("window.start")) \
        .withColumn("window_end", col("window.end")) \
        .drop("window")

    # Write to Cassandra
    query = windowed_df.writeStream \
        .foreachBatch(lambda batch_df, batch_id: write_to_cassandra(batch_df)) \
        .outputMode("complete") \
        .start()

    query.awaitTermination()

def write_to_cassandra(batch_df):
    # Write to Cassandra
    (batch_df.write
     .format("org.apache.spark.sql.cassandra")
     .mode("append")
     .options(table="sensor_aggregates", keyspace="iot_data")
     .save())

def create_cassandra_schema():
    # This would typically be done using CQL commands
    # For now, we'll assume the schema is created manually
    pass

if __name__ == "__main__":
    spark = create_spark_session()
    process_stream(spark) 