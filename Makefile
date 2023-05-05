install:
	brew install jq localstack
	pip3 install awscli-local

.ONESHELL:
TOKEN?='dummy-token'
generate_secrets:
	# pass in Twitter credentials via
	# make setup TOKEN=value CLIENT_ID=value ACCESS_TOKEN=value

	# SecretsManager secrets for Twitter credentials
	$(eval SECRETS_ARN=$(shell awslocal --endpoint-url=http://localhost:4566 secretsmanager create-secret --name secret_arn --secret-string '{"token":"$(TOKEN)", "client_id":"$(CLIENT_ID)", "access_token":"$(ACCESS_TOKEN)"}' | jq -r .ARN))
	echo $(SECRETS_ARN)

.ONESHELL:
CLIENT_ID?='dummy-client-id'
ACCESS_TOKEN?='dummy-access-token'
SECRETS_ARN?='dummy-arn'
setup:
	# Create S3 bucket
	awslocal s3 mb s3://dev-datalake

	# Create a local layer for tweepy
	$(eval LAYER_ARN=$(shell awslocal lambda publish-layer-version --layer-name tweepy --zip-file fileb://layers/tweepy_layer.zip | jq -r .LayerVersionArn))
	echo $(LAYER_ARN)

	# Make a fresh zip file
	cd lambda; zip ../tmp/zips/hydrate_tweet.py.zip hydrate_tweet.py
	sleep 4

	# Create main Lambda function
	awslocal lambda create-function \
		--function-name hydrate_tweet \
		--runtime python3.9 \
		--zip-file fileb://tmp/zips/hydrate_tweet.py.zip \
		--handler hydrate_tweet.lambda_handler \
		--role arn:aws:iam::000000000000:role/lambda-role \
		--environment Variables="{target_bucket=dev-datalake,secret_arn=$(SECRETS_ARN)}" \
		--timeout 10 \
		--layers $(LAYER_ARN)

	awslocal apigatewayv2 create-api --name 'Twitter Capture' --protocol-type HTTP --target arn:aws:lambda:us-east-1:000000000000:function:hydrate_tweet
