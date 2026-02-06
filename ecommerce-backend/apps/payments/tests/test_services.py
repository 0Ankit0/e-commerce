from django.test import TestCase

from apps.payments.services.payment_gateway import process_payment, process_refund


class PaymentGatewayTests(TestCase):
    def test_process_payment(self):
        result = process_payment(100.00, "USD")
        self.assertTrue(result["success"])
        self.assertEqual(result["status"], "COMPLETED")
        self.assertEqual(result["amount"], 100.00)
        self.assertTrue(result["transaction_id"].startswith("txn_"))

    def test_process_refund(self):
        result = process_refund("txn_123")
        self.assertTrue(result["success"])
        self.assertEqual(result["status"], "REFUNDED")
        self.assertEqual(result["original_payment_id"], "txn_123")
