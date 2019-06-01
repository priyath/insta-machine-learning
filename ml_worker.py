import os, sys

import redis
from rq import Worker, Queue, Connection
import logging, logging.config, yaml
from logging.handlers import RotatingFileHandler

logger = None
listen = ['Q3']

redis_url = os.getenv('REDISTOGO_URL', 'redis://localhost:6379')

conn3 = redis.from_url(redis_url)


def ml_exception_handler(job, exc_type, exc_value, traceback):
    logger.error('job {} execution failed. status: {}'.format(job.id, job.get_status()))
    return False


if __name__ == '__main__':
    # TODO: move log file name to config file
    logger = logging.getLogger('rq.worker')

    # configure file handler
    rfh = RotatingFileHandler('logs/worker_ml.log', maxBytes=10*1024*1024, backupCount=10)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    rfh.setFormatter(formatter)
    logger.addHandler(rfh)

    # configure stream handler
    sh = logging.StreamHandler()
    sh.setFormatter(formatter)
    logging.getLogger().addHandler(sh)
    #logging.config.dictConfig(yaml.load(open('./config/logging-workers.conf')))

    with Connection(conn3):
        worker = Worker(list(map(Queue, listen)), exception_handlers=[ml_exception_handler])
        worker.work()