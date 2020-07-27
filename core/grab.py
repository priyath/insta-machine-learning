from instagram_private_api import Client
import time
import configparser
import logging
import json
import math
import http
import core.db as dbHandler
import codecs
import os.path
from itertools import cycle

logger = logging.getLogger("rq.worker.grab")

config_path = 'config/config.ini'
followers_path = './core/followers/'
settings_file_path = 'config/login_cache_{}.json'

INCREMENT = 5000

CLIENT_CONNECTIONS = []
SCRAPER_ACCOUNTS = []


def to_json(python_object):
    if isinstance(python_object, bytes):
        return {'__class__': 'bytes',
                '__value__': codecs.encode(python_object, 'base64').decode()}
    raise TypeError(repr(python_object) + ' is not JSON serializable')


def from_json(json_object):
    if '__class__' in json_object and json_object['__class__'] == 'bytes':
        return codecs.decode(json_object['__value__'].encode(), 'base64')
    return json_object


def on_login_callback(api, new_settings_file):
    cache_settings = api.settings
    with open(new_settings_file, 'w') as outfile:
        json.dump(cache_settings, outfile, default=to_json)
        logger.info('SAVED: {0!s}'.format(new_settings_file))


def get_client(scraper_username, scraper_password, proxy):
    print('using scraper account: {}'.format(scraper_username))

    settings_path = settings_file_path.format(scraper_username)
    try:
        if not os.path.isfile(settings_path):
            logger.info('[{}] Logging in'.format(scraper_username))
            logger.info('Username: {} Password: {} Proxy: {}'.format(scraper_username, scraper_password, proxy))
            # proxy='http://138.197.49.55:50000'
            return Client(scraper_username, scraper_password, proxy=proxy, on_login=lambda x: on_login_callback(x, settings_path))
        else:
            with open(settings_path) as file_data:
                cached_settings = json.load(file_data, object_hook=from_json)
            logger.info('[{}] Reusing settings: {}'.format(scraper_username, settings_path))

            device_id = cached_settings.get('device_id')
            # reuse auth settings
            return Client(
                scraper_username, scraper_password,
                settings=cached_settings,
                proxy=proxy)
    except Exception as e:
        logger.error('Authentication failed')
        logger.error(e)
        raise


# load configurations from  config.ini
try:
    config = configparser.ConfigParser()
    config.read(config_path)
    username = config.get('Credentials', 'username').strip()
    password = config.get('Credentials', 'password').strip()
    scrape_limit = int(config.get('Scrape', 'scrape_limit').strip())

    # configure scraper accounts
    scraper_accounts = config.get('GrabProxy', 'scraper_accounts').split(',')
    scraper_passwords = config.get('GrabProxy', 'scraper_passwords').split(',')
    scraper_proxy = config.get('GrabProxy', 'scraper_proxy').split(',')

    for i in range(len(scraper_accounts)):
        CLIENT_CONNECTIONS.append(get_client(scraper_accounts[i], scraper_passwords[i], scraper_proxy[i]))

except Exception as e:
    logger.error('Error reading configuration details from config.ini')
    logger.error(e)
    raise

round_robin = cycle(CLIENT_CONNECTIONS)
SLEEP_INTERVAL = 10/len(CLIENT_CONNECTIONS)


def get_next_username_client():
    return round_robin.__next__()


def grab_followers(target_account, scrape_percentage, rescrape):
    api = get_next_username_client()
    target = target_account
    scraper_account = api.authenticated_user_name()
    followers = []

    if not dbHandler.is_complete(target, 1):
        dbHandler.update_queue_status(target, 1, dbHandler.PROCESSING)

        start = time.time()

        try:
            result = api.username_info(target)
            follower_count = result['user']['follower_count']
            user_id = result['user']['pk']

            scrape_limit = math.ceil((follower_count * scrape_percentage)/100)
            logger.info('[{}] Grabbing {} of followers for account {}'.format(scraper_account, scrape_limit, target_account))

            # retrieve first batch of followers
            rank_token = Client.generate_uuid()
            results = api.user_followers(user_id, rank_token=rank_token)
            followers.extend(results.get('users', []))
            next_max_id = results.get('next_max_id')

            count = 1

            # main loop where the scraping happens
            periodic_val = INCREMENT
            while next_max_id:
                try:
                    results = api.user_followers(user_id, rank_token=rank_token, max_id=next_max_id)
                    followers.extend(results.get('users', []))

                    next_max_id = results.get('next_max_id')
                    count += 1
                    logger.info('[{}][{}] : {}/{} followers scraped'.format(scraper_account, target_account, len(followers),
                                                                               scrape_limit))

                    scraped = len(followers)

                    if scraped > periodic_val:
                        logger.info('[{}] Updating progress in db'.format(target_account))
                        ex_time = time.time() - start
                        dbHandler.update_grab_progress(target_account, scraped, ex_time)
                        periodic_val += INCREMENT

                    if len(followers) >= scrape_limit:  # limit scrape
                        break
                    logger.info('[{}][{}] Sleeping for {} seconds'.format(scraper_account, target_account, SLEEP_INTERVAL))
                    time.sleep(SLEEP_INTERVAL)
                    api = get_next_username_client()

                except Exception as e:
                    logger.error('[{}][{}] Something went wrong. Error: {}'.format(target_account, scraper_account, e))
                    time.sleep(10)
                    api = get_next_username_client()
                    continue

        except Exception as e:
            logger.error('[{}] Main loop failed'.format(target_account))
            logger.error(e)
            # dbHandler.update_queue_status(target, 1, dbHandler.FAILED)
            raise

        followers.sort(key=lambda x: x['pk'])
        logger.info('[{}] Grabbing complete'.format(target_account))

        # if this is a rescrape, rename previous result file to identify diff
        if rescrape:
            try:
                logger.info('[{}] Renaming previous grab results'.format(target_account))
                os.rename(followers_path + str(target) + "_followers.txt", followers_path + str(target) + "_followers_previous.txt")
            except Exception as e:
                logger.error('Failed when writing results to file')
                logger.error(e)
                # dbHandler.update_queue_status(target, 1, dbHandler.FAILED)
                raise

        try:
            # write execution results to file
            # TODO: paths to be read from config files
            with open(followers_path + str(target) + "_followers.txt", "w") as text_file:
                for follower in followers:
                    text_file.write("%s\n" % follower['username'])
        except Exception as e:
            logger.error('Failed when writing results to file')
            logger.error(e)
            # dbHandler.update_queue_status(target, 1, dbHandler.FAILED)
            raise

        logger.info('[{}] Successfully written to file'.format(target_account))

        execution_time = (time.time() - start)
        dbHandler.update_grab_progress(target_account, len(followers), execution_time)
        dbHandler.update_queue_status(target, 1, dbHandler.COMPLETE)
    else:
        logger.info('[{}] Grab execution already complete'.format(target_account))
