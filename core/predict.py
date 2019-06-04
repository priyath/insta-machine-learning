# Save Model Using Pickle
import json
import pickle
import time
import pandas
import logging
import sys
import core.db as dbHandler

logger = logging.getLogger("rq.worker.ml")

filename = './core/prediction_model.sav'
model_data_path = './core/followers/'
analysis_results_path = './core/analysis/'

def analyze(target):
    logger.info('[{}] Analysing account {}'.format(target, target))
    if not dbHandler.is_complete(target, 3):
        dbHandler.update_queue_status(target, 3, dbHandler.PROCESSING)
        try:
            # load the model from disk
            loaded_model = pickle.load(open(filename, 'rb'), encoding='latin1')

            # Load dataset to be analyzed
            names_ = ['username','numberPosts','numberFollowing','numberFollowers','hasProfilePicture','isPrivate','isVerified','recentCount','recentLikeCount','recentCommentCount','followersFollowingRatio','followingPostsRatio','followersPostsRatio','differenceRatio', 'rating']
            dataset_ = pandas.read_csv(model_data_path + target + '_model_data.csv', names=names_)
        except Exception as e:
            logger.error('[{}] Something went wrong while loading model and/or model data to memory'.format(target))
            logger.error(e)
            # dbHandler.update_queue_status(target, 3, dbHandler.FAILED)
            raise

        try:
            # get usernames
            usernameArray = dataset_.values
            usernames = usernameArray[:,0]

            # delete columns that we don't need
            del dataset_['username']
            #del dataset['numberPosts']
            #del dataset['numberFollowing']
            #del dataset['numberFollowers']
            #del dataset['hasProfilePicture']
            #del dataset['isPrivate']
            #del dataset['isVerified']
            #del dataset_['followersFollowingRatio']
            #del dataset_['followingPostsRatio']
            #del dataset_['followersPostsRatio']
            #del dataset_['ratioDifference']
            #del dataset['rating']

            # x data set
            array = dataset_.values
            X_data = array[:,0:13]

            # make a prediction
            Y_predict = loaded_model.predict(X_data)

            # build analysis results
            total_account_count = len(X_data)
            count = 0
            fake_count = 0
            influencer_count = 0
            mass_count = 0
            results = "username, prediction\n"

            for i in range(total_account_count):
                post_count = int(X_data[i][0])
                follower_count = int(X_data[i][2])
                following_count = int(X_data[i][1])
                has_prof_pic = int(X_data[i][3])
                username = usernames[i]
                rating = 'real'
                count = count + 1

                if Y_predict[i] == 1:
                    fake_count = fake_count + 1
                    rating = 'fake'
                # print  "username: %s prediction: %s" % (username, rating)
                result = "%s, %s\n" % (username, rating)
                results += str(result)

                # count influencers
                if (follower_count > 5000):
                    influencer_count = influencer_count + 1

                # mass following accounts
                if (following_count > 1000):
                    mass_count = mass_count + 1

            account_statistics = {
                "account_name": target,
                "total_accounts": total_account_count,
                "fake_accounts": fake_count,
                "real_accounts": (total_account_count - fake_count),
                "breakdown": {
                    "influencer_accounts": influencer_count,
                    "suspicious_accounts": None,
                    "mass_accounts": mass_count
                }
            }

            logger.info('[{}] Analysis complete. Writing to file'.format(target))
        except Exception as e:
            logger.error('[{}] Something went wrong while performing analysis'.format(target))
            logger.error(e)
            # dbHandler.update_queue_status(target, 3, dbHandler.FAILED)
            raise

        try:
            # write output to file
            ts = time.time()
            with open(analysis_results_path + target + '_analysis_details.csv', 'w') as csv_file:
                csv_file.write(results)

            with open(analysis_results_path + target + '_account_stats.json', 'w') as json_file:
                json.dump(account_statistics, json_file)
        except Exception as e:
            logger.error('[{}] Something went wrong while writing analysis results to file'.format(target))
            logger.error(e)
            # dbHandler.update_queue_status(target, 3, dbHandler.FAILED)
            raise
        dbHandler.write_results(target, json.dumps(account_statistics))
        dbHandler.update_queue_status(target, 3, dbHandler.COMPLETE)
    else:
        logger.info('[{}] Predict execution is already complete.'.format(target))









