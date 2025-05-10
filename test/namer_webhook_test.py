"""
Test webhook notification functionality in namer.py
"""

import json
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

from loguru import logger

from namer.namer import send_webhook_notification
from test import utils
from test.utils import sample_config, environment, new_ea


class WebhookTest(unittest.TestCase):
    """
    Test the webhook notification functionality.
    """

    def __init__(self, method_name='runTest'):
        super().__init__(method_name)

        if not utils.is_debugging():
            logger.remove()

    def test_webhook_disabled(self):
        """
        Test that no webhook is sent when the feature is disabled.
        """
        config = sample_config()
        config.webhook_enabled = False
        config.webhook_url = 'http://example.com/webhook'

        with patch('requests.request') as mock_post:
            send_webhook_notification(Path('/some/path/movie.mp4'), config)
            mock_post.assert_not_called()

    def test_webhook_no_url(self):
        """
        Test that no webhook is sent when the URL is not configured.
        """
        config = sample_config()
        config.webhook_enabled = True
        config.webhook_url = ''

        with patch('requests.request') as mock_post:
            send_webhook_notification(Path('/some/path/movie.mp4'), config)
            mock_post.assert_not_called()

    def test_webhook_success(self):
        """
        Test that a webhook is successfully sent when enabled and URL is configured.
        """
        config = sample_config()
        config.webhook_enabled = True
        config.webhook_url = 'http://example.com/webhook'

        with patch('requests.request') as mock_post:
            mock_response = MagicMock()
            mock_response.raise_for_status.return_value = None
            mock_post.return_value = mock_response

            send_webhook_notification(Path('/some/path/movie.mp4'), config)

            mock_post.assert_called_once()
            # Verify payload structure
            args, kwargs = mock_post.call_args
            self.assertEqual(args[0], 'POST')
            self.assertEqual(args[1], 'http://example.com/webhook')
            self.assertEqual(kwargs['data'].decode('UTF-8'), json.dumps({'target_movie_file': str(Path('/some/path/movie.mp4'))}, separators=(',', ':')))

    def test_webhook_failure(self):
        """
        Test that webhook errors are properly handled.
        """
        config = sample_config()
        config.webhook_enabled = True
        config.webhook_url = 'http://example.com/webhook'

        with patch('requests.request') as mock_post:
            mock_post.side_effect = Exception('Connection error')

            # Should not raise an exception
            send_webhook_notification(Path('/some/path/movie.mp4'), config)

            mock_post.assert_called_once()

    def test_integration_with_file_processing(self):
        """
        Test that webhook is triggered when a file is successfully processed.
        """
        with environment() as (temp_dir, fake_tpdb, config):
            config.webhook_enabled = True
            config.webhook_url = 'http://example.com/webhook'

            with patch('namer.namer.send_webhook_notification') as mock_webhook:
                targets = [new_ea(temp_dir, use_dir=False)]

                # Process the file
                from namer.namer import main

                main(['-f', str(targets[0].file), '-c', str(config.config_file)])

                # Verify webhook was called
                mock_webhook.assert_called()


if __name__ == '__main__':
    unittest.main()
