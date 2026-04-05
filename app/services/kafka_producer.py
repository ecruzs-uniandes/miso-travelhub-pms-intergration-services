import logging
from app.config import settings

logger = logging.getLogger(__name__)

_producer = None


def get_producer():
    global _producer
    if not settings.KAFKA_ENABLED:
        return None
    if _producer is None:
        try:
            from confluent_kafka import Producer
            _producer = Producer({
                "bootstrap.servers": settings.KAFKA_BOOTSTRAP_SERVERS,
                "client.id": settings.SERVICE_NAME,
                "acks": "all",
                "retries": 3,
                "linger.ms": 10,
            })
        except Exception as e:
            logger.error(f"Failed to create Kafka producer: {e}")
            return None
    return _producer


def delivery_callback(err, msg):
    if err:
        logger.error(f"Kafka delivery failed: {err}")
    else:
        logger.info(f"Message delivered to {msg.topic()} [{msg.partition()}] @ offset {msg.offset()}")


def publish_sync_command(hotel_id: str, message: str) -> bool:
    if not settings.KAFKA_ENABLED:
        logger.info(f"Kafka disabled — logging command: {message[:200]}")
        return True

    producer = get_producer()
    if producer is None:
        logger.warning("Kafka producer unavailable — logging command instead")
        logger.info(f"SyncCommand: {message[:200]}")
        return True

    try:
        producer.produce(
            topic=settings.KAFKA_TOPIC_PMS_SYNC,
            key=hotel_id.encode("utf-8"),
            value=message.encode("utf-8"),
            callback=delivery_callback,
        )
        producer.poll(0)
        return True
    except Exception as e:
        logger.error(f"Failed to publish to Kafka: {e}")
        return False


def flush_producer():
    producer = get_producer()
    if producer:
        producer.flush()


def close_producer():
    global _producer
    if _producer:
        _producer.flush()
        _producer = None
