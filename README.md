# Rehydrate Tweets

A hastily implemented AWS-based toy I made to grab and store my Twitter Favourites before the API goes dark.

When you download your data archive from Twitter, it includes your Likes, but there's not much more than the the basic message text and the status_id in there. The concept was always that if you wanted the original message back - assuming it was still available - you'd have to "rehydrate" it by calling the API with the status_id…

## Application overview

![Diagram showing the basic application outline. The users's request from their commmand line goes via an AWS Gateway (HTTP API) to the Hydrate Tweet Lambda which gets data for an individual tweet and writes a JSON representation of the data to an S3 Bucket. The object creation causes an S3 trigger to fire, launching the Augment Media Lambda which grabs the media connected to the tweet and writes it back to the S3 Bucket](https://github.com/lizconlan/rehydrate-tweets/blob/main/hydrate_tweets.jpg?raw=true)

## Principal Cast (Data collection)

* Docker
* Some S3 buckets
* Event notifications on the S3 bucket
* Secrets Manager
* Cloudwatch logging
* An untidy pile of Python-based Lambda functions
* A Lambda layer to import the tweepy (Twitter client) library
* API Gateway v2 (HTTP flavour)

(The last 2 necessitate a Localstack Pro key. I started out using a v1 REST API locally then realised I needed Pro anyway and switched to something closer to my actual implementation)

## Supporting crew (Data loading / analysis)

* Athena
* Glue

## Foolish assumptions

* You already have python3 on your machine
* You happen to be using a Mac
* You have homebrew installed
* You have curl installed (or are prepared to add it)

## You will also need

* A Localstack Pro key (a trial key is fine)
* A Twitter developer account

## How to play with it

### First time setup

Run `make install` to get jq and localstack (using homebrew) and the awscli-local tool, using python's pip package system

(If you're not using a Mac, sorry for the rubbish instructions! You'll need to install jq, localstack and the awscli-local pip package manually rather than using `make install`; although copy pasting the install command from the Makefile's setup should work for the pip install bit)

### Starting up the app

1. Set your key in your local shell per the instructions (basically `export LOCALSTACK_API_KEY=<YOUR_API_KEY>`)
1. Run `localstack start`
1. In a new terminal window (or tab, I like tabs for this sort of thing) run:<br><br>`make setup TOKEN=<YOUR_TWITTER_BEARER_TOKEN>`<br><br>
1. Right at the end you'll see some output including the address of the newly created endpoint, that looks something like this:<br><br>`"ApiEndpoint": "1234abcd.execute-api.localhost.localstack.cloud:4566"`<br><br>Copy that (just the second bit, not the ApiEndpoint text) for use in the next step

### Play with your new toy

Use the API endpoint in a curl POST command, like this:

```
curl -H "Content-Type: application/json" \
     -XPOST https://1234abcd.execute-api.localhost.localstack.cloud:4566/tweet/sync \
     -d '{ "tweet_link": "https://twitter.com/dog_rates/status/1519015795904315392" }'
```

(You can also use a shortform version of the JSON body like this: `{ "tweet_link": "1519015795904315392" }`, but seeing which account the tweet was posted from - and having the option of pasting the url into a web browser first - is more reasssuring for an example. It's more fun if you don't do that though!)

Right, Hopefully that ended with the message `{"message":"Done"}` in the time it took for you to read that (it's calling an actual API over the internet, it might need a few seconds)

To see what you got, do this:

`awslocal s3 ls dev-datalake/liked_media/`

You should see a file called `1519015795904315392-FRSg0JBVUAEhiXF.jpg`

Download that file from your local cloud bucket like this:

`awslocal s3 cp s3://dev-datalake/liked_media/1519015795904315392-FRSg0JBVUAEhiXF.jpg .`

Take a look :)

You should also have a json file with a slightly customised version of the original tweet data:

`awslocal s3 ls dev-datalake/raw_data/`

You should see a file called `1519015795904315392.json`

Download that file as well:

`awslocal s3 cp s3://dev-datalake/raw_data/1519015795904315392.json .`

Then open the file in your favourite text editor, or print it straight to the terminal using `cat 1519015795904315392.json`

## Credits

Diagram made using https://app.diagrams.net/

And inspired by the diagram from [LocalStack's Demo app](https://github.com/localstack/localstack-demo#localstack-demo)

## License

This code is available under the MIT License
