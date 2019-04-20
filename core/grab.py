from instagram_private_api import Client
import time
import configparser
import logging
import sys

logger = logging.getLogger("rq.worker.grab")

start = time.time()

# load configurations from  config.ini
try:
    config = configparser.ConfigParser()
    config.read('config/config.ini')
    username = config.get('Credentials', 'username').strip()
    password = config.get('Credentials', 'password').strip()
    scrape_limit = int(config.get('Scrape', 'scrape_limit').strip())
except Exception as e:
    logger.error('Error reading configuration details from config.ini')
    logger.error(e)
    sys.exit()


def grab_followers(target_account):
    logger.info('[{}] Grabbing {}% of followers for account {}'.format(target_account, scrape_limit, target_account))
    target = target_account
    followers = []

    # authenticate
    try:
        api = Client(username, password)
    except Exception as e:
        logger.error('Authentication failed')
        logger.error(e)
        sys.exit()

    try:
        result = api.username_info(target)
        user_id = result['user']['pk']

        # retrieve first batch of followers
        rank_token = Client.generate_uuid()
        results = api.user_followers(user_id, rank_token=rank_token)
        followers.extend(results.get('users', []))
        next_max_id = results.get('next_max_id')

        count = 1

        # main loop where the scraping happens
        while next_max_id:
            results = api.user_followers(user_id, rank_token=rank_token, max_id=next_max_id)
            followers.extend(results.get('users', []))
            if len(followers) >= scrape_limit:  # limit scrape
                break
            next_max_id = results.get('next_max_id')
            count += 1
            time.sleep(2)
    except Exception as e:
        logger.error('Main loop failed')
        logger.error(e)
        sys.exit()

    followers.sort(key=lambda x: x['pk'])
    logger.info('[{}] Grabbing complete'.format(target_account))
    execution_time = (time.time() - start)

    try:
        # write execution results to file
        # TODO: paths to be read from config files
        with open("./core/followers/" + str(target) + "_followers.txt", "w") as text_file:
            for follower in followers:
                text_file.write("%s\n" % follower['username'])
    except Exception as e:
        logger.error('Failed when writing results to file')
        logger.error(e)
        sys.exit()

    logger.info('[{}] Successfully written to file'.format(target_account))