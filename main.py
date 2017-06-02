import os
import sys
import logging
import codecs
import json
import argparse
from datetime import datetime, timedelta
from pymongo import MongoClient

from config import *
try:
    from instagram_private_api import (
        Client, ClientError, ClientLoginError,
        ClientCookieExpiredError, ClientLoginRequiredError,
        __version__ as client_version)
except ImportError:
    import sys
    sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
    from instagram_private_api import (
        Client, ClientError, ClientLoginError,
        ClientCookieExpiredError, ClientLoginRequiredError,
        __version__ as client_version)


def to_json(python_object):
    if isinstance(python_object, bytes):
        return {'__class__': 'bytes',
                '__value__': codecs.encode(python_object, 'base64').decode()}
    raise TypeError(repr(python_object) + ' is not JSON serializable')

def from_json(json_object):
    if '__class__' in json_object and json_object['__class__'] == 'bytes':
        return codecs.decode(json_object['__value__'].encode(), 'base64')
    return json_object

def onlogin_callback(api, new_settings_file):
    cache_settings = api.settings
    with open(new_settings_file, 'w') as outfile:
        json.dump(cache_settings, outfile, default=to_json)
        print('SAVED: {0!s}'.format(new_settings_file))

def getAttribute(obj):
    output = {}
    for key, value in obj.__dict__.items():
        if type(value) is list:
            output[key] = [getAttribute(item) for item in value]
        else:
            try:
                output[key] = getAttribute(value)
            except:
                output[key] = value

    return output

class Instagram_DataService():
    '''Main class of the project'''
    def __init__(self, username, password):
        '''
        :param username: Instagram Login Username
        :param password: Instagram Login Password
        '''
        device_id = None
        try:
            settings_file = settings_file_path
            if not os.path.isfile(settings_file):
                # settings file does not exist
                print('Unable to find file: {0!s}'.format(settings_file_path))

                # login new
                self.client = Client(
                    username, password,
                    on_login=lambda x: onlogin_callback(x, settings_file_path))
            else:
                with open(settings_file) as file_data:
                    cached_settings = json.load(file_data, object_hook=from_json)
                print('Reusing settings: {0!s}'.format(settings_file))

                device_id = cached_settings.get('device_id')
                # reuse auth settings
                self.client = Client(
                    username, password,
                    settings=cached_settings)

        except (ClientCookieExpiredError, ClientLoginRequiredError) as e:
            print('ClientCookieExpiredError/ClientLoginRequiredError: {0!s}'.format(e))

            # Login expired
            # Do relogin but use default ua, keys and such
            self.client = Client(
                username, password,
                device_id=device_id,
                on_login=lambda x: onlogin_callback(x, settings_file_path))

        except ClientLoginError as e:
            print('ClientLoginError {0!s}'.format(e))
            exit(9)
        except ClientError as e:
            print('ClientError {0!s} (Code: {1:d}, Response: {2!s})'.format(e.msg, e.code, e.error_response))
            exit(9)
        except Exception as e:
            print('Unexpected Exception: {0!s}'.format(e))
            exit(99)

        self.user_id = self.client.username_info(username)['user']['pk']
        client = MongoClient(host, port)
        self.db = client.instagram

    def get_followers(self):
        '''
        get info per follower as a json format and store into followers collection of mongodb.
        '''
        follower_collection = self.db.followers

        max_id = ""
        while True:
            follower_response = self.client.user_followers(self.user_id, max_id=max_id)
            for follower in follower_response['users']:
                follower_collection.update({'pk': follower['pk']}, {"$set": follower}, upsert=True)

            max_id = follower_response.get('next_max_id')
            if max_id is None:
                break

    def get_followings(self):
        '''
            get info per following as a json format and store into followings collection of mongodb.
        '''

        following_collection  = self.db.followings

        max_id = ""
        while True:
            following_response = self.client.user_following(self.user_id, max_id=max_id)
            for following in following_response['users']:
                following_collection.update({'pk': following['pk']}, {"$set": following}, upsert=True)

            max_id = following_response.get('next_max_id')
            if max_id is None:
                break

    def retrive_posts(self, user_id):
        '''
        :param user_id: pk of user in instagram

         get posts as a json format and store into posts collection of mongodb. And then for every posts, get comments
         and store into comments collection.

        '''
        post_collection = self.db.posts

        max_id = ""
        while True:
            post_response = self.client.user_feed(user_id, max_id=max_id, min_timestamp=min_timestamp)
            logger.info(post_response)
            for post in post_response['items']:
                logger.info('postId: %d' %post['pk'])
                post_collection.update({'pk': post['pk']}, {"$set": post}, upsert=True)
                self.retrive_comments(post['pk'])

            max_id = post_response.get('next_max_id')
            if max_id is None:
                break

    def retrive_comments(self, media_id):
        '''
        :param media_id: pk of post in instagram
        get comments and store into comments collection.
        '''
        comment_collection = self.db.comments

        max_id = ""
        while True:
            comment_response = self.client.media_comments(media_id, max_id=max_id)
            for comment in comment_response['comments']:
                comment_collection.update({'pk': comment['pk']}, {"$set": comment}, upsert=True)

            max_id = comment_response.get('next_max_id')
            if max_id is None:
                break

if __name__ == "__main__":
    # Calculate unix timestamp x minutes before current time.
    if len(sys.argv)>1:
        min_timestamp = int((datetime.utcnow() - timedelta(minutes=int(sys.argv[1]))).timestamp())
    else:
        min_timestamp = ""

    # Making logger cutomized
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    # Get username and password from config.py
    username = username
    password = password

    # Generate Instagram_DataService object with above username and password
    service = Instagram_DataService(username, password)

    # Get followers and follwings from instagram and store into mogodb.
    service.get_followers()
    service.get_followings()

    logger.info("Done getting followers and followings\n")
    logger.info("Getting posts of followers")

    # Get followerIds from mongodb and fetch posts and comments for these
    followerIds = [item['pk'] for item in list(service.db.followers.find({}, {'pk': 1}))]
    for followerId in followerIds:

        logger.info("\n")
        logger.info('followerId: %d\n' %followerId)

        try:
            service.retrive_posts(followerId)
        except Exception as ex:
            pass



