from functools import lru_cache
from unittest.mock import PropertyMock, patch

import boto3
import pytest
from django.conf import settings
from moto import mock_s3
from rest_framework.test import APIClient, APIRequestFactory
from storages.backends.s3boto3 import S3Boto3Storage

pytest_plugins = [
    "celery.contrib.pytest",
    "tests.aws_fixtures",
    "common.tests.fixtures",
    "apps.users.tests.fixtures",
    "apps.finances.tests.fixtures",
    "apps.content.tests.fixtures",
    "apps.notifications.tests.fixtures",
    "apps.integrations.tests.fixtures",
    "apps.multitenancy.tests.fixtures",
]


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def api_client_admin():
    client = APIClient()
    client.defaults.setdefault("SERVER_NAME", "admin.example.org")
    return client


@pytest.fixture
def api_request_factory():
    """Factory for creating API requests for testing"""
    return APIRequestFactory()


@pytest.fixture(autouse=True)
def storage(mocker):
    bucket_name = "test-bucket"
    with mock_s3():
        storage = S3Boto3Storage()
        session = boto3.session.Session()
        with patch(
            "storages.backends.s3boto3.S3Boto3Storage.connection",
            new_callable=PropertyMock,
        ) as mock_connection_property, patch(
            "storages.backends.s3boto3.S3Boto3Storage.bucket",
            new_callable=PropertyMock,
        ) as mock_bucket_property:

            @lru_cache(None)
            def get_connection():
                return session.resource("s3")

            @lru_cache(None)
            def get_bucket():
                connection = get_connection()
                connection.create_bucket(
                    Bucket=bucket_name,
                    CreateBucketConfiguration={"LocationConstraint": "eu-ewst-1"},
                )
                bucket = connection.Bucket(bucket_name)
                return bucket

            mock_connection_property.side_effect = get_connection
            mock_bucket_property.side_effect = get_bucket
            yield storage


@pytest.fixture
def s3_exports_bucket():
    with mock_s3():
        s3 = boto3.client("s3", region_name="us-east-1", endpoint_url=settings.AWS_S3_ENDPOINT_URL)
        s3.create_bucket(Bucket=settings.AWS_EXPORTS_STORAGE_BUCKET_NAME)
        yield
