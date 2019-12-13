"""Defines rq worker for background processing"""
import os
import redis
from rq import Worker, Queue, Connection

LISTEN = ['high', 'default', 'low']
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379')
CONN = redis.from_url(REDIS_URL)

if __name__ == '__main__':
    with Connection(CONN):
        WORKER = Worker(map(Queue, LISTEN))
        WORKER.work()
