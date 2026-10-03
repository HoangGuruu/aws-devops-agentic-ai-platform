import os,unittest
from unittest.mock import patch
import productpage
class IncidentTests(unittest.TestCase):
    def test_fault_is_off_by_default(self):
        with patch.dict(os.environ,{'LAB_FAULT_MODE':'off'}),patch.object(productpage,'getProductDetails',return_value=(200,{})),patch.object(productpage,'getProductReviews',return_value=(200,{})):
            self.assertEqual(productpage.app.test_client().get('/productpage').status_code,200)
    def test_fault_breaks_business_endpoint_but_not_liveness(self):
        with patch.dict(os.environ,{'LAB_FAULT_MODE':'http500'}):
            c=productpage.app.test_client();self.assertEqual(c.get('/productpage').status_code,500);self.assertEqual(c.get('/health').status_code,200)
            metrics=c.get('/metrics').data.decode();self.assertIn('bookinfo_http_responses_total',metrics);self.assertIn('status="500"',metrics)
