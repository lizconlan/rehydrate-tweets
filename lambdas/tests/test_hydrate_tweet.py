import sys
sys.path.append("lambdas")
from hydrate_tweet import lambda_handler

import json
import unittest
from unittest.mock import MagicMock, patch, DEFAULT
from io import StringIO

class DotDict(dict):
    """A dictionary that supports dot notation as well as dictionary access notation.
    It's a solution for conveniently accessing dictionary elements.
    """
    def __init__(self, *args, **kwargs):
        dict.__init__(self, *args, **kwargs)
        self.__dict__ = self

class TestHydrateTweet(unittest.TestCase):
    def setUp(self):
        self.target_bucket = "target-bucket"
        self.tweet_id = "1234567890123456789"
        self.bucket_key = "raw_data/" + self.tweet_id + ".json"
        self.event = json.loads("""{
            "body": {
                "tweet_link": "https://twitter.com/Twitter/status/1234567890123456789"
            }
        }""")

        # Mock user response from Twitter API
        with open("lambdas/tests/fixtures/example_user.json") as f:
            self.author_data = DotDict(json.load(f))

        # Mock tweet response from Twitter API
        with open("lambdas/tests/fixtures/example_tweet.json") as f:
            self.tweet_data = DotDict(json.load(f))

        self.context = MagicMock()

    @patch('sys.stdout', new_callable=StringIO)
    @patch("hydrate_tweet.os.environ")
    @patch("hydrate_tweet.author_data")
    @patch("hydrate_tweet.tweepy.Client")
    def test_lambda_handler(self, mock_tweepy_client, mock_author_data, mock_os_env, *_):
        # Mocking author_data()
        mock_author_data.return_value = self.author_data

        # Mocking os.environ
        mock_os_env.return_value = {"target_bucket": self.target_bucket}

        # Mocking tweepy.Client
        mock_tweepy_client.return_value.get_tweet.return_value.data = self.tweet_data

        with patch.multiple('hydrate_tweet', get_secret=DEFAULT, save_linked_tweets=DEFAULT, stash_profile_image=DEFAULT, save_tweet_data=DEFAULT) as mocks:
            mocks['get_secret'].return_value = {"token": "abcd1234"}
            mocks['save_linked_tweets'].return_value = {"ResponseMetadata": {"HTTPStatusCode": 200}}
            mocks['stash_profile_image'].return_value = "profile_images/9876543210/abcdefg_normal.jpg"
            mocks['save_tweet_data'].return_value = True

            # Running the lambda handler
            response = lambda_handler(self.event, self.context)

            # Asserting successful response
            self.assertEqual(response, {"message": "Done"})

    @patch('sys.stdout', new_callable=StringIO)
    @patch("hydrate_tweet.os.environ")
    @patch("hydrate_tweet.author_data")
    @patch("hydrate_tweet.tweepy.Client")
    def test_saving_linked_tweets(self, mock_tweepy_client, mock_author_data, mock_os_env, *_):
        # Mocking author_data()
        mock_author_data.return_value = self.author_data

        # Mocking os.environ
        mock_os_env.return_value = {"target_bucket": self.target_bucket}

        # Mocking tweepy.Client
        mock_tweepy_client.return_value.get_tweet.return_value.data = self.tweet_data

        with patch.multiple('hydrate_tweet', get_secret=DEFAULT, save_linked_tweets=DEFAULT, stash_profile_image=DEFAULT, save_tweet_data=DEFAULT) as mocks:
            mocks['get_secret'].return_value = {"token": "abcd1234"}
            mocks['save_linked_tweets'].return_value = {"ResponseMetadata": {"HTTPStatusCode": 200}}
            mocks['stash_profile_image'].return_value = "profile_images/9876543210/abcdefg_normal.jpg"
            mocks['save_tweet_data'].return_value = True

            # Running the lambda handler
            response = lambda_handler(self.event, self.context)

            # Asserting the linked tweets
            mocks['save_linked_tweets'].assert_called_once()
            self.assertEqual(mocks['save_linked_tweets'].mock_calls[0][1][0][0]['expanded_url'], "https://example.com")

    @patch('sys.stdout', new_callable=StringIO)
    @patch("hydrate_tweet.os.environ")
    @patch("hydrate_tweet.author_data")
    @patch("hydrate_tweet.tweepy.Client")
    def test_saving_profile_image(self, mock_tweepy_client, mock_author_data, mock_os_env, *_):
        # Mocking author_data()
        mock_author_data.return_value = self.author_data

        # Mocking os.environ
        mock_os_env.return_value = {"target_bucket": self.target_bucket}

        # Mocking tweepy.Client
        mock_tweepy_client.return_value.get_tweet.return_value.data = self.tweet_data

        with patch.multiple('hydrate_tweet', get_secret=DEFAULT, save_linked_tweets=DEFAULT, stash_profile_image=DEFAULT, save_tweet_data=DEFAULT) as mocks:
            mocks['get_secret'].return_value = {"token": "abcd1234"}
            mocks['save_linked_tweets'].return_value = {"ResponseMetadata": {"HTTPStatusCode": 200}}
            mocks['stash_profile_image'].return_value = "profile_images/9876543210/abcdefg_normal.jpg"
            mocks['save_tweet_data'].return_value = True

            # Running the lambda handler
            response = lambda_handler(self.event, self.context)

        # Asserting saving the profile image
        mocks['stash_profile_image'].assert_called_once()

    @patch('sys.stdout', new_callable=StringIO)
    @patch("hydrate_tweet.os.environ")
    @patch("hydrate_tweet.author_data")
    @patch("hydrate_tweet.tweepy.Client")
    def test_saving_tweet_data(self, mock_tweepy_client, mock_author_data, mock_os_environ, *_):
        # Mocking author_data()
        mock_author_data.return_value = self.author_data

        # Mocking os.environ
        mock_os_environ.return_value = {"target_bucket": self.target_bucket}

        # Mocking tweepy.Client
        mock_tweepy_client.return_value.get_tweet.return_value.data = self.tweet_data

        with patch.multiple('hydrate_tweet', get_secret=DEFAULT, save_linked_tweets=DEFAULT, stash_profile_image=DEFAULT, save_tweet_data=DEFAULT) as mocks:
            mocks['get_secret'].return_value = {"token": "abcd1234"}
            mocks['save_linked_tweets'].return_value = {"ResponseMetadata": {"HTTPStatusCode": 200}}
            mocks['stash_profile_image'].return_value = "profile_images/9876543210/abcdefg_normal.jpg"
            mocks['save_tweet_data'].return_value = True

            # Running the lambda handler
            response = lambda_handler(self.event, self.context)

            # Asserting saving the tweet data
            mocks['save_tweet_data'].assert_called_once()

if __name__ == '__main__':
    unittest.main()
