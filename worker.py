from dotenv import load_dotenv
import os
load_dotenv()

from redis import Redis
from rq.connections import Connection          # ← NEW
from rq.simple import SimpleWorker             # ← NEW (avoids fork issues)

redis_url  = os.getenv("REDIS_URL", "redis://localhost:6379")
redis_conn = Redis.from_url(redis_url)

if __name__ == "__main__":
    with Connection(redis_conn):
        worker = SimpleWorker(["default"])     # use SimpleWorker
        print("✅ RQ worker ready, listening to: default")
        worker.work()
