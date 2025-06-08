# worker.py
import redis
from rq import Queue
from rq.worker import SimpleWorker
import config

if __name__ == "__main__":
    # Connect to Redis
    redis_conn = redis.Redis()

    # Listen on the "default" queue
    queue = Queue('default', connection=redis_conn)

    # Use SimpleWorker instead of Worker (no forking)
    worker = SimpleWorker([queue], connection=redis_conn)
    print("✅ SimpleWorker ready, listening to: default")
    worker.work()
