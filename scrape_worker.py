import os

import redis
from rq import Worker, Queue, Connection

listen = ['Q2']

redis_url = os.getenv('REDISTOGO_URL', 'redis://localhost:6379')

conn2 = redis.from_url(redis_url)

if __name__ == '__main__':
    with Connection(conn2):
        worker = Worker(list(map(Queue, listen)))
        worker.work()