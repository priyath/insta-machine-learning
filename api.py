import flask
from flask import request
from rq import Queue

from core.scrape import init
from core.grab import grab_followers
from grab_worker import conn1
from scrape_worker import conn2

app = flask.Flask(__name__)
app.config["DEBUG"] = False

q1 = Queue('Q1', connection=conn1)
q2 = Queue('Q2', connection=conn2)


# health check endpoint
@app.route('/', methods=['GET'])
def home():
    return 'ML api is alive'


# endpoint to initiate analysis
@app.route('/api/v1/analyze', methods=['POST'])
def api_all():
    content = request.get_json()
    target = content['account']

    # queue our account id to grab followers
    job_1 = q1.enqueue_call(
        func=grab_followers, args=(target, ), result_ttl=5000
    )

    # queue our account id to grab follower details
    job_2 = q2.enqueue_call(
        func=init, depends_on=job_1, args=(target, ), result_ttl=5000
    )

    print(job_1.get_id())
    return job_1.get_id()


if __name__ == '__main__':
    import logging, logging.config, yaml
    logging.config.dictConfig(yaml.load(open('./config/logging.conf')))
    app.run()
