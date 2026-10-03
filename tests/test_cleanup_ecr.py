"""Guard destructive cleanup using mocked AWS calls only."""
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

spec = importlib.util.spec_from_file_location('cleanup_ecr', Path(__file__).resolve().parents[1] / 'scripts/cleanup_ecr_images.py')
cleanup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cleanup)


class CleanupTests(unittest.TestCase):
    def run_helper(self, *, account='111122223333', answer='DELETE COURSE IMAGES', wrong_repo=False, count=0, fail=False):
        ecr = Mock()
        ecr.get_paginator.return_value.paginate.return_value = [{'imageIds': [{'imageDigest': f'sha256:{i:064x}'} for i in range(count)]}]
        ecr.batch_delete_image.return_value = {'failures': [{'failureCode': 'denied'}]} if fail else {'failures': []}
        sts = Mock()
        sts.get_caller_identity.return_value = {'Account': account}
        session = Mock(region_name='us-east-1')
        session.client.side_effect = lambda service: sts if service == 'sts' else ecr
        sdk = SimpleNamespace(Session=lambda: session)
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / 'inventory.json'
            data = {s: f'111122223333.dkr.ecr.us-east-1.amazonaws.com/devops-course-develop/{s}' for s in ['productpage', 'details', 'ratings', 'reviews']}
            if wrong_repo:
                data['reviews'] = '111122223333.dkr.ecr.us-east-1.amazonaws.com/another-project/reviews'
            p.write_text(json.dumps(data))
            with patch.dict(sys.modules, {'boto3': sdk}), patch.object(sys, 'argv', ['cleanup', '--inventory', str(p)]), patch('builtins.input', return_value=answer), patch('builtins.print'):
                try:
                    cleanup.main()
                    error = None
                except (SystemExit, RuntimeError) as exc:
                    error = exc
        return ecr, error

    def test_wrong_repository_denied(self):
        client, error = self.run_helper(wrong_repo=True)
        self.assertIsInstance(error, SystemExit)
        client.batch_delete_image.assert_not_called()

    def test_wrong_account_denied(self):
        client, error = self.run_helper(account='999900001111')
        self.assertIsInstance(error, SystemExit)
        client.batch_delete_image.assert_not_called()

    def test_cancel_does_not_delete(self):
        client, error = self.run_helper(answer='no')
        self.assertIsInstance(error, SystemExit)
        client.batch_delete_image.assert_not_called()

    def test_batches_only_expected_repositories(self):
        client, error = self.run_helper(count=201)
        self.assertIsNone(error)
        self.assertEqual(client.batch_delete_image.call_count, 12)
        for call in client.batch_delete_image.call_args_list:
            self.assertLessEqual(len(call.kwargs['imageIds']), 100)
            self.assertTrue(call.kwargs['repositoryName'].startswith('devops-course-develop/'))

    def test_aws_failure_stops_cleanup(self):
        client, error = self.run_helper(count=1, fail=True)
        self.assertIsInstance(error, RuntimeError)
        self.assertEqual(client.batch_delete_image.call_count, 1)


if __name__ == '__main__':
    unittest.main()
