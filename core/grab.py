from instagram_private_api import Client
import time
import configparser
import logging
import sys
import math
import http
import core.db as dbHandler

logger = logging.getLogger("rq.worker.grab")

config_path = 'config/config.ini'
followers_path = './core/followers/'

start = time.time()

# load configurations from  config.ini
try:
    config = configparser.ConfigParser()
    config.read(config_path)
    username = config.get('Credentials', 'username').strip()
    password = config.get('Credentials', 'password').strip()
    scrape_limit = int(config.get('Scrape', 'scrape_limit').strip())
except Exception as e:
    logger.error('Error reading configuration details from config.ini')
    logger.error(e)
    raise


def grab_followers(target_account, scrape_percentage):
    target = target_account
    followers = []

    if not dbHandler.is_complete(target, 1):
        dbHandler.grab_insert(target, 1, dbHandler.PROCESSING)
        # authenticate
        try:
            logger.info('[{}] Logging in'.format(target_account))
            api = Client(username, password)
        except Exception as e:
            logger.error('Authentication failed')
            logger.error(e)
            dbHandler.grab_insert(target, 1, dbHandler.FAILED)
            raise

        try:
            result = api.username_info(target)
            follower_count = result['user']['follower_count']
            user_id = result['user']['pk']

            scrape_limit = math.ceil((follower_count * scrape_percentage)/100)
            logger.info('[{}] Grabbing {} of followers for account {}'.format(target_account, scrape_limit, target_account))

            # retrieve first batch of followers
            rank_token = Client.generate_uuid()
            results = api.user_followers(user_id, rank_token=rank_token)
            followers.extend(results.get('users', []))
            next_max_id = results.get('next_max_id')

            count = 1

            # main loop where the scraping happens
            while next_max_id:
                try:
                    results = api.user_followers(user_id, rank_token=rank_token, max_id=next_max_id)
                    followers.extend(results.get('users', []))
                    if len(followers) >= scrape_limit:  # limit scrape
                        break
                    next_max_id = results.get('next_max_id')
                    count += 1
                    logger.info('[{}] Followers scraped: {}'.format(target_account, len(followers)))
                    time.sleep(2)
                except http.client.IncompleteRead as e:
                    logger.error('[{}] Incomplete read exception. Lets retry'.format(target_account))
                    continue

        except Exception as e:
            logger.error('[{}] Main loop failed'.format(target_account))
            logger.error(e)
            dbHandler.grab_insert(target, 1, dbHandler.FAILED)
            raise

        followers.sort(key=lambda x: x['pk'])
        logger.info('[{}] Grabbing complete'.format(target_account))
        execution_time = (time.time() - start)

        try:
            # write execution results to file
            # TODO: paths to be read from config files
            with open(followers_path + str(target) + "_followers.txt", "w") as text_file:
                for follower in followers:
                    text_file.write("%s\n" % follower['username'])
        except Exception as e:
            logger.error('Failed when writing results to file')
            logger.error(e)
            dbHandler.grab_insert(target, 1, dbHandler.FAILED)
            raise

        logger.info('[{}] Successfully written to file'.format(target_account))
        dbHandler.grab_insert(target, 1, dbHandler.COMPLETE)
    else:
        logger.info('[{}] Grab execution already complete'.format(target_account))