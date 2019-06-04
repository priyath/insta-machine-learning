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


def validate_request(content):

    if 'account' not in content:
        return False, 'required parameter account is missing'
    if 'percentage' in content and not str(content['percentage']).replace('.', '', 1).isdigit():
        return False, 'percentage should be a number'
    if 'percentage' in content and float(content['percentage']) > 100:
        return False, 'percentage value should be less than 100'

    return True, None


# health check endpoint
@app.route('/', methods=['GET'])
def home():
    return 'ML api is alive'


# endpoint to initiate analysis
@app.route('/api/v1/analyze', methods=['POST'])
def api_analyze():
    content = request.get_json()

    is_valid_request, error_message = validate_request(content)

    if not is_valid_request:
        abort(400, error_message)

    target = content['account']
    scrape_percentage = float(content['percentage']) if 'percentage' in content else 100
    # force = content['force']

    logger.info(
        '[{}] Account received for processing. account: {} percentage: {}'.format(target, target, scrape_percentage))
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
@app.route('/api/v1/status', methods=['GET'])
def api_status():
    account = request.args.get('account')

    if not account:
        abort(400, 'required query parameter account is missing')

    logger.info(
        '[{}] Account received for status. account: {}'.format(account, account))
    return dbHandler.get_status(account), 200


if __name__ == '__main__':
    app.run()
