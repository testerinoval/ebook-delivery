from dotenv import load_dotenv
import os
load_dotenv()

from redis import Redis
from rq import Queue, SimpleWorker   # ← only these two are needed

redis_url  = os.getenv("REDIS_URL", "redis://localhost:6379")
redis_conn = Redis.from_url(redis_url)

if __name__ == "__main__":
    queue  = Queue(name="default", connection=redis_conn)
    worker = SimpleWorker([queue], connection=redis_conn)
    print("✅ RQ worker ready, listening to: default")
    worker.work()
