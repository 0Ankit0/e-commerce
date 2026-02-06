import logging

from apps.notifications import sender
from common import emails

from . import constants, email_serializers, models

logger = logging.getLogger(__name__)


class TenantInvitationEmail(emails.Email):
    name = "TENANT_INVITATION"
    serializer_class = email_serializers.TenantInvitationEmailSerializer


def send_tenant_invitation_notification(tenant_membership: models.TenantMembership, membership_id: str, token: str):
    if tenant_membership.user:
        sender.send_notification(
            user=str(tenant_membership.user.id),
            type=constants.Notification.TENANT_INVITATION_CREATED.value,
            data={
                "id": membership_id,
                "token": token,
                "tenant_name": tenant_membership.tenant.name,
            },
            issuer=str(tenant_membership.creator.id) if tenant_membership.creator else "",
        )


def send_accepted_tenant_invitation_notification(tenant_membership: models.TenantMembership, membership_id: str):
    if tenant_membership.creator and tenant_membership.user:
        sender.send_notification(
            user=str(tenant_membership.creator.id),
            type=constants.Notification.TENANT_INVITATION_ACCEPTED.value,
            data={
                "id": membership_id,
                "name": str(tenant_membership.user.profile) or str(tenant_membership.user),
                "tenant_name": str(tenant_membership.tenant),
            },
            issuer=str(tenant_membership.user.id),
        )


def send_declined_tenant_invitation_notification(tenant_membership: models.TenantMembership, membership_id: str):
    if tenant_membership.creator and tenant_membership.user:
        sender.send_notification(
            user=str(tenant_membership.creator.id),
            type=constants.Notification.TENANT_INVITATION_DECLINED.value,
            data={
                "id": membership_id,
                "name": str(tenant_membership.user.profile) or str(tenant_membership.user),
                "tenant_name": str(tenant_membership.tenant),
            },
            issuer=str(tenant_membership.user.id),
        )
