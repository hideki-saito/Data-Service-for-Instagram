import sys
import logging
from datetime import datetime, timedelta
from pymongo import MongoClient

from config import *
from instagram_private_api import Client

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

class Insgram_DataService():
    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.client = Client(username, password)
        self.user_id = self.client.username_info(username)['user']['pk']
        client = MongoClient(host, port)
        self.db = client.instagram

    def get_followers(self):
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

    if len(sys.argv)>1:
        min_timestamp = int((datetime.utcnow() - timedelta(minutes=int(sys.argv[1]))).timestamp())

    else:
        min_timestamp = ""

    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    username = username
    password = password

    service = Insgram_DataService(username, password)

    service.get_followers()
    service.get_followings()

    logger.info("Done getting followers and followings\n")

    logger.info("Getting posts of followers")
    followerIds = [item['pk'] for item in list(service.db.followings.find({}, {'pk': 1}))]
    for followerId in followerIds:
        logger.info("\n")
        logger.info('followerId: %d\n' %followerId)

        try:
            service.retrive_posts(followerId)
        except Exception as ex:
            # print (service.db.followers.find_one({'pk': followerId})['username'])
            pass

    # mediaIds = [item['pk'] for item in list(service.db.posts.find({}, {'pk':1}))]
    # for mediaId in mediaIds:
    #     print ('comment', mediaId)
    #     try:
    #         service.retrive_comments(mediaId)
    #     except Exception as ex:
    #         pass


