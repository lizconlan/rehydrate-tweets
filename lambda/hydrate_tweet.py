import json
import base64
import boto3
import tweepy
import os
import io

from botocore.exceptions import ClientError

S3 = boto3.client("s3")

def lambda_handler(event, context):
    object_key = event["object_key"]
    raw_content = S3.get_object(Bucket=os.environ["source_bucket"], Key=object_key)["Body"].read()
    tweet_id = json.loads(raw_content)["like"]["tweetId"]

    # Connect to Twitter API v2
    client = tweepy.Client(get_secret()["token"])

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
        "timestamp": str(tweet.created_at),
        "author": {
            "id": tweet.author_id,
            "username": author.username,
            "description": author.description,
            "display_name": author.name,
            "protected": author.protected,
            "verified": author.verified
        },
        "media": media,
        "external_links": links,
        "mentions": others
    }

    try:
        response = S3.upload_fileobj(io.BytesIO(json.dumps(data).encode("utf-8")), os.environ["target_bucket"], tweet_id + ".json")
    except ClientError as e:
        return {
            'statusCode': 500,
            body: e
        }

    return {
        'statusCode': 200,
        'body': data
    }

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

def get_secret():
    secret_name = os.environ["secret_arn"]
    region_name = "us-east-1"

    # Create a Secrets Manager client
    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager',
        region_name=region_name
    )

    # In this sample we only handle the specific exceptions for the 'GetSecretValue' API.
    # See https://docs.aws.amazon.com/secretsmanager/latest/apireference/API_GetSecretValue.html
    # We rethrow the exception by default.

    try:
        get_secret_value_response = client.get_secret_value(
            SecretId=secret_name
        )
    except ClientError as e:
        if e.response['Error']['Code'] == 'DecryptionFailureException':
            # Secrets Manager can't decrypt the protected secret text using the provided KMS key.
            # Deal with the exception here, and/or rethrow at your discretion.
            raise e
        elif e.response['Error']['Code'] == 'InternalServiceErrorException':
            # An error occurred on the server side.
            # Deal with the exception here, and/or rethrow at your discretion.
            raise e
        elif e.response['Error']['Code'] == 'InvalidParameterException':
            # You provided an invalid value for a parameter.
            # Deal with the exception here, and/or rethrow at your discretion.
            raise e
        elif e.response['Error']['Code'] == 'InvalidRequestException':
            # You provided a parameter value that is not valid for the current state of the resource.
            # Deal with the exception here, and/or rethrow at your discretion.
            raise e
        elif e.response['Error']['Code'] == 'ResourceNotFoundException':
            # We can't find the resource that you asked for.
            # Deal with the exception here, and/or rethrow at your discretion.
            raise e
    else:
        # Decrypts secret using the associated KMS key.
        # Depending on whether the secret is a string or binary, one of these fields will be populated.
        if 'SecretString' in get_secret_value_response:
            secret = get_secret_value_response['SecretString']
            return json.loads(secret)
        else:
            decoded_binary_secret = base64.b64decode(get_secret_value_response['SecretBinary'])
            return json.loads(decoded_binary_secret)
