import flask
from flask import request, abort, Response
from rq import Queue
from flask import jsonify

from core.scrape import init
from core.grab import grab_followers
from core.predict import analyze
import core.db as dbHandler


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
    #force = content['force']

    q1_id = target + '-q1'
    q2_id = target + '-q2'
    q3_id = target + '-q3'

    # queue our account id to grab followers
    if dbHandler.should_queue(target):

        dbHandler.insert_account(target)

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
            'account': target,
            'message': 'Account is successfully queued for processing'
        }), 202
    else:
        logger.warning('[{}] Account is already queued.'.format(target))
        return jsonify({
            'account': target,
            'message': 'Account is already queued for processing'
        }), 409


# endpoint to fetch job status
@app.route('/api/v1/status', methods=['POST'])
def api_status():
    content = request.get_json()
    target = content['account']

    return dbHandler.get_status(target), 200


# endpoint to get analysis results
@app.route('/api/v1/results', methods=['POST'])
def api_results():
    content = request.get_json()
    target = content['account']

    return dbHandler.get_results(target), 200


if __name__ == '__main__':
    app.run()
