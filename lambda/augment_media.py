import boto3
import io
import json
import os
import requests

S3 = boto3.client("s3")

def lambda_handler(event, context):
    object_key = event["Records"][0]["s3"]["object"]["key"]
    raw_content = S3.get_object(Bucket=os.environ["bucket"], Key=object_key)["Body"].read()

    tweet = json.loads(raw_content)
    tweet_id = tweet["id"]

    if "media" in tweet.keys():
        save_media_entities(tweet["media"], tweet_id)
    else:
        return {
            'statusCode': 200,
            'body': 'No media found'
        }

    return {
        'statusCode': 200,
        'body': 'Done!'
    }

def save_media_entities(media_data, tweet_id):
    for item in media_data:
        data = requests.get(item["url"])
        file_target = "liked_media/" + str(tweet_id) + "-" + item["url"].split("/")[-1]
        S3.upload_fileobj(io.BytesIO(data.content), os.environ["bucket"], file_target)
