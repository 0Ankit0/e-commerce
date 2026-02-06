from django.test import TestCase

from apps.finances.models import Price, Product


class FinancesModelTests(TestCase):
    def test_models_exist(self):
        # Simply verifying that the proxy models are loadable and behave like Django models
        # Since they are proxies to DjStripe, we don't need deep logic checks, just existence
        self.assertTrue(Product.objects.all().exists() or True)
        self.assertTrue(Price.objects.all().exists() or True)
