from unittest.mock import Mock

import pytest

from ..middleware import get_current_tenant, get_current_user_role

pytestmark = pytest.mark.django_db


# TenantUserRoleMiddleware tests removed as it was replaced by TenantMiddleware


class TestTenantUserRoleMiddlewareGetCurrentTenant:
    def test_get_current_tenant_with_tenant_id(self, tenant_factory):
        tenant_factory.create_batch(10)
        tenant = tenant_factory(name="Test Tenant")
        result = get_current_tenant(tenant.id)
        assert result == tenant

    def test_get_current_tenant_nonexistent_tenant(self, tenant_factory):
        tenant_factory.create_batch(10)
        tenant_factory(name="Test Tenant")
        result = get_current_tenant("9999")
        assert result is None

    def test_get_current_tenant_missing_tenant_id(self, tenant_factory):
        tenant_factory.create_batch(10)
        tenant_factory(name="Test Tenant")
        result = get_current_tenant(None)
        assert result is None


class TestTenantUserRoleMiddlewareGetCurrentUserRole:
    def test_get_current_user_role_authenticated_user(self, graphene_client, tenant, user, tenant_membership_factory):
        tenant_membership = tenant_membership_factory(user=user, tenant=tenant, role="admin")
        info = Mock()
        info.context.user = user
        info.context.tenant = tenant
        info.context.tenant_id = tenant.id
        graphene_client.force_authenticate(user)
        result = get_current_user_role(info.context.tenant, info.context.user)
        assert result == tenant_membership.role

    def test_get_current_user_role_unauthenticated_user(self, tenant, user, tenant_membership_factory):
        tenant_membership_factory(user=user, tenant=tenant, role="admin")
        info = Mock()
        info.context.user = None
        info.context.tenant = tenant
        info.context.tenant_id = tenant.id
        result = get_current_user_role(info.context.tenant, info.context.user)
        assert result is None

    def test_get_current_user_role_membership_does_not_exist(
        self, graphene_client, tenant, user, tenant_membership_factory
    ):
        tenant_membership_factory(user=user, tenant=tenant, role="admin")
        info = Mock()
        info.context.user = user
        info.context.tenant = None
        info.context.tenant_id = None
        graphene_client.force_authenticate(user)
        result = get_current_user_role(info.context.tenant, info.context.user)
        assert result is None
