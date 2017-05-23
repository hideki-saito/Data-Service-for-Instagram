import json

from config import *
from InstagramAPI import Instagram


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
        self.instagram = Instagram(username, password, IGDataPath="/tmp/account_%s" % username)
        self.instagram.login()
        self.userId = self.instagram.username_id

    def get_followers(self):
        followers = []
        max_id = ""
        while True:
            follow_response = self.instagram.getUserFollowers(self.userId, max_id)
            for follower in follow_response.followers:
                followers.append(getAttribute(follower))

            max_id = follow_response.next_max_id
            if max_id is None:
                break

        return followers

    def get_followings(self):
        followings = []
        max_id = ""
        while True:
            following_response = self.instagram.getUserFollowings(self.userId, max_id)
            for following in following_response.followings:
                followings.append(getAttribute(following))

            max_id = following_response.next_max_id
            if max_id is None:
                break

        return followings

    def retrive_posts(self, follower_id):
        posts = []
        max_id = ""
        while True:
            post_response = self.instagram.getUserFeed(follower_id, max_id)
            for post in post_response.items:
                posts.append(getAttribute(post))

            max_id = post_response.next_max_id
            if max_id is None:
                break

        return posts

    def retrive_comments(self, media_id):
        comments = []
        max_id = ""
        while True:
            comment_response = self.instagram.getMediaComments(media_id, max_id)
            for comment in comment_response.comments:
                comments.append(getAttribute(comment))

            max_id = comment_response.next_max_id
            if max_id is None:
                break

        return comments


if __name__ == "__main__":
    username = username
    password = password

    service = Insgram_DataService(username, password)

    followers = service.get_followers()
    followings = service.get_followings()
    # print (json.dumps(followings, indent=2))
    posts = service.retrive_posts(service.userId)
    # print (json.dumps(posts, indent=2))

    comments = service.retrive_comments('1507131452641371245')
    print(json.dumps(comments, indent=2))