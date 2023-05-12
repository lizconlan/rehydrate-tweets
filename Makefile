install:
	brew install jq localstack
	pip3 install awscli-local

.ONESHELL:
TOKEN?='dummy-token'
CLIENT_ID?='dummy-client-id'
ACCESS_TOKEN?='dummy-access-token'
SECRETS_ARN?='dummy-arn'
BUCKET=dev-datalake
setup:
	$(eval SECRETS_ARN=$(shell awslocal --endpoint-url=http://localhost:4566 secretsmanager create-secret --name secret_arn --secret-string '{"token":"$(TOKEN)", "client_id":"$(CLIENT_ID)", "access_token":"$(ACCESS_TOKEN)"}' | jq -r .ARN))
	echo $(SECRETS_ARN)

	# Create S3 bucket
	awslocal s3 mb s3://$(BUCKET)

	# Create a local layer for tweepy
	$(eval LAYER_ARN=$(shell awslocal lambda publish-layer-version --layer-name tweepy --zip-file fileb://layers/tweepy_layer.zip | jq -r .LayerVersionArn))
	echo $(LAYER_ARN)

	# Make a fresh zip file for the tweet hydrator
	cd lambda; zip ../tmp/zips/hydrate_tweet.py.zip hydrate_tweet.py

	# Create hydrate Lambda function
	awslocal lambda create-function \
		--function-name hydrate_tweet \
		--runtime python3.9 \
		--zip-file fileb://tmp/zips/hydrate_tweet.py.zip \
		--handler hydrate_tweet.lambda_handler \
		--role arn:aws:iam::000000000000:role/lambda-role \
		--environment Variables="{target_bucket=$(BUCKET),secret_arn=$(SECRETS_ARN)}" \
		--timeout 10 \
		--layers $(LAYER_ARN)

	# Make a fresh zip file for the media augmenter
	cd lambda; zip ../tmp/zips/augment_media.py.zip augment_media.py

	# Create augment_media Lambda function
	awslocal lambda create-function \
		--function-name augment_media \
		--runtime python3.9 \
		--zip-file fileb://tmp/zips/augment_media.py.zip \
		--handler augment_media.lambda_handler \
		--role arn:aws:iam::000000000000:role/lambda-role \
		--timeout 10 \
		--environment Variables="{bucket=$(BUCKET)}" \
		--layers $(LAYER_ARN)

	# Allow the lambda to be invoked by the S3 trigger
	awslocal lambda add-permission \
        --function-name augment_media \
        --action lambda:InvokeFunction \
        --statement-id lambda \
        --principal lambda.amazonaws.com

	# Create a trigger that fires when new file is added to the raw_data prefix (folder)
	awslocal s3api put-bucket-notification-configuration \
		--bucket $(BUCKET) \
		--notification-configuration file://configs/notification-config.json

	# Create the HTTP apigateway endpoint
	awslocal apigatewayv2 create-api \
		--name 'Twitter Capture' \
		--protocol-type HTTP \
		--route-key '/tweet/sync' \
		--target arn:aws:lambda:us-east-1:000000000000:function:hydrate_tweet
