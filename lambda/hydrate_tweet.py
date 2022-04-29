import json
import boto3
import tweepy
import os

S3 = boto3.client("s3")

def lambda_handler(event, context):
    object_key = event["object_key"]
    raw_content = S3.get_object(Bucket=os.environ["source-bucket"], Key=object_key)["Body"].read()
    tweet_id = json.loads(raw_content)["like"]["tweetId"]

    # Connect to Twitter API v2
    client = tweepy.Client(os.environ["token"])

    response = client.get_tweet(tweet_id,
                                expansions=["author_id", "entities.mentions.username", "attachments.media_keys"],
                                tweet_fields=["created_at", "entities"],
                                user_fields=["username", "verified", "protected", "description", "name"],
                                media_fields=["alt_text", "url"])

    tweet = response.data

    if "media" in response.includes.keys():
        media = media_entities(response.includes["media"])
    else:
        media = []

    if "urls" in tweet.entities.keys():
        links = url_entities(tweet.entities["urls"])
    else:
        links = []

    author = author_data(tweet.author_id, response.includes["users"])
    others = non_author_list(tweet.author_id, response.includes["users"])

    data = {
        "id": tweet.id,
        "text": tweet.text,
        "tweeted_at": str(tweet.created_at),
        "author_id": tweet.author_id,
        "author_name": author.username,
        "media": media,
        "external_links": links,
        "mentions": others
    }

    return data

    # return {
    #     'statusCode': 200,
    #     'body': json.loads(response)
    # }

def author_data(author_id, user_data):
    for user in user_data:
        if user["id"] == author_id:
            return user

def non_author_list(author_id, user_data):
    if len(user_data) < 2:
        return []
    else:
        list = []
        for user in user_data:
            if user.id == author_id:
                continue
            else:
                list.append(
                    {
                        "user_id": user.id,
                        "user_name": user.username,
                        "protected": user.protected,
                        "verified": user.verified
                    })
        return list

def url_entities(url_data):
    links = []
    for link in url_data:
        if link["display_url"].startswith("pic.twitter.com"):
            continue
        else:
            links.append(
                {
                    "display_url": link["display_url"],
                    "expanded_url": link["expanded_url"],
                    "title": link["title"]
                })
    return links

def media_entities(media_data):
    media = []
    for item in media_data:
        media.append({
            "alt_text": item["alt_text"],
            "media_key": item["media_key"],
            "type": item["type"],
            "url": item["url"]
        })
    return media
