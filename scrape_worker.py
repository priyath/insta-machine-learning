import os

import redis
from rq import Worker, Queue, Connection
import logging, logging.config, yaml
from logging.handlers import RotatingFileHandler
import core.db as dbHandler

logger = None

listen = ['Q2']

redis_url = os.getenv('REDISTOGO_URL', 'redis://localhost:6379')

conn2 = redis.from_url(redis_url)


def scrape_exception_handler(job, exc_type, exc_value, traceback):
    account = job.id.split('-')[0].strip()
    logger.error('[{}] job {} execution failed. status: {}'.format(account, job.id, job.get_status()))
    dbHandler.update_queue_status(account, 2, dbHandler.FAILED)
    return False


if __name__ == '__main__':
    # TODO: move log file name to config file
    logger = logging.getLogger('rq.worker')

    # configure file handler
    rfh = RotatingFileHandler('logs/worker_scrape.log', maxBytes=10*1024*1024, backupCount=10)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    rfh.setFormatter(formatter)
    logger.addHandler(rfh)

    # configure stream handler
    sh = logging.StreamHandler()
    sh.setFormatter(formatter)
    logging.getLogger().addHandler(sh)
    #logging.config.dictConfig(yaml.load(open('./config/logging-workers.conf')))

    with Connection(conn2):
        worker = Worker(list(map(Queue, listen)), exception_handlers=[scrape_exception_handler])
        worker.work()