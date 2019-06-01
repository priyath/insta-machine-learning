import flask
from flask import request
from rq import Queue
from flask import jsonify

from core.scrape import init
from core.grab import grab_followers
from core.predict import analyze

from grab_worker import conn1
from scrape_worker import conn2
from ml_worker import conn3

import logging, logging.config, yaml

logging.config.dictConfig(yaml.load(open('./config/logging.conf')))
logger = logging.getLogger(__name__)

app = flask.Flask(__name__)
app.config["DEBUG"] = False

q1 = Queue('Q1', connection=conn1)
q2 = Queue('Q2', connection=conn2)
q3 = Queue('Q3', connection=conn3)

# health check endpoint
@app.route('/', methods=['GET'])
def home():
    return 'ML api is alive'


# endpoint to initiate analysis
@app.route('/api/v1/analyze', methods=['POST'])
def api_analyze():
    content = request.get_json()
    target = content['account']
    scrape_percentage = content['percentage']

    q1_id = target + '-q1'
    q2_id = target + '-q2'
    q3_id = target + '-q3'

    q1_job = q1.fetch_job(q1_id)
    q2_job = q2.fetch_job(q2_id)
    q3_job = q3.fetch_job(q3_id)

    q1_job_status = q1_job.get_status() if q1_job else None
    q2_job_status = q2_job.get_status() if q2_job else None
    q3_job_status = q3_job.get_status() if q3_job else None

    # queue our account id to grab followers
    if not (q1_job_status == 'started' or q2_job_status == 'started' or q3_job_status == 'started'):
        job_1_args = (target, scrape_percentage)
        job_1 = q1.enqueue_call(
            func=grab_followers, args=job_1_args, result_ttl=10, job_id=q1_id, timeout=172800
        )

        job_2 = q2.enqueue_call(
            func=init, depends_on=job_1, args=(target,), result_ttl=10, job_id=q2_id, timeout=172800
        )

        job_3 = q3.enqueue_call(
            func=analyze, depends_on=job_2, args=(target,), result_ttl=10, job_id=q3_id, timeout=172800
        )

        logger.info('[{}] Account is queued for processing'.format(target))
        return jsonify({
            'status': '{} account is queued for processing'.format(target)
        })
    else:
        logger.warning('[{}] Account is already queued.'.format(target))
        return jsonify({
            'status': 'account {} is already being processed.'.format(target)
        })


# endpoint to fetch job status
@app.route('/api/v1/status', methods=['POST'])
def api_status():
    content = request.get_json()
    target = content['account']

    q1_id = target + '-q1'
    q2_id = target + '-q2'
    q3_id = target + '-q3'

    if q1.fetch_job(q1_id):
        # queue our account id to grab followers
        q1_status = q1.fetch_job(q1_id).get_status()
        q2_status = q2.fetch_job(q2_id).get_status()
        q3_status = q3.fetch_job(q3_id).get_status()

        return jsonify({
            '1-grabQueueStatus': q1_status,
            '2-scrapeQueueStatus': q2_status,
            '3-mlQueueStatus': q3_status
        })

    else:
        return jsonify({
            'error': 'Account ID not submitted for processing',
            'additional-info': 'To initiate analysis, submit the account ID to the analyze endpoint.'
        })


if __name__ == '__main__':
    app.run()
