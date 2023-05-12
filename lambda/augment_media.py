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
    print(media_data)
    for item in media_data:
        if item["type"] == "photo":
            save_photo(item["url"], tweet_id)
        elif item["type"] == "video":
            save_video(item["url"], tweet_id)

def save_photo(photo_url, tweet_id):
    data = requests.get(photo_url)
    file_target = "liked_media/" + str(tweet_id) + "-" + photo_url.split("/")[-1]
    S3.upload_fileobj(io.BytesIO(data.content), os.environ["bucket"], file_target)

def save_video(video_url, tweet_id):
    file_target = "liked_media/" + str(tweet_id) + "-" + video_url.split("/")[-1].split('?tag')[0]

    print("file_target: " + file_target)
    print("video_url: " + video_url)

    multipart_upload = S3.create_multipart_upload(
        Bucket=os.environ["bucket"],
        ContentType="video/mp4",
        Key=file_target
    )
    uploadID = multipart_upload['UploadId']

    parts = []
    part_number = 1

    with requests.get(video_url) as datastream:
        # Use the suggested default (minimum) size of 5MB - chunk_size is in bytes
        for chunk in datastream.iter_content(chunk_size=1024 * 1024 * 5):
            if chunk:
                uploadPart = S3.upload_part(
                    Body=chunk,
                    Bucket=os.environ["bucket"],
                    Key=file_target,
                    PartNumber=part_number,
                    UploadId=uploadID
                )

                parts.append({
                    'PartNumber': part_number,
                    'ETag': uploadPart['ETag']
                })

                part_number += 1
                print("part_number is now:")
                print(part_number)

    print("done making parts")

    completeResult = S3.complete_multipart_upload(
        Bucket=os.environ["bucket"],
        Key=file_target,
        MultipartUpload={ 'Parts': parts },
        UploadId=multipart_upload['UploadId']
    )

    print("and we're out!")
    print(completeResult)
