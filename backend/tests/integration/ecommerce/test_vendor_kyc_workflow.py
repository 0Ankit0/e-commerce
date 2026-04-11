from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.integration.ecommerce.test_marketplace_flow import _create_tenant_for_owner, _create_user_headers


@pytest.mark.asyncio
async def test_vendor_kyc_packet_decision_flow_and_auditability(client: AsyncClient, db_session: AsyncSession):
    admin, admin_headers = await _create_user_headers(db_session, username='kyc_admin', email='kyc_admin@example.com', is_superuser=True)
    reviewer, reviewer_headers = await _create_user_headers(db_session, username='kyc_reviewer', email='kyc_reviewer@example.com', is_superuser=True)
    vendor_user, vendor_headers = await _create_user_headers(db_session, username='kyc_vendor', email='kyc_vendor@example.com')
    tenant = await _create_tenant_for_owner(db_session, vendor_user, 'kyc-tenant')

    create_vendor = await client.post(
        '/api/v1/vendor/profile',
        headers=vendor_headers,
        json={
            'tenant_id': __import__('src.apps.iam.utils.hashid', fromlist=['encode_id']).encode_id(tenant.id),
            'business_name': 'KYC Vendor Pvt Ltd',
            'display_name': 'KYC Vendor',
            'slug': 'kyc-vendor',
            'description': 'KYC workflow vendor',
        },
    )
    assert create_vendor.status_code == 201, create_vendor.text
    vendor_id = create_vendor.json()['vendor']['id']

    incomplete_under_review = await client.post(f'/api/v1/admin/vendors/{vendor_id}/mark-under-review', headers=admin_headers)
    assert incomplete_under_review.status_code == 409

    packet_submit = await client.put(
        '/api/v1/vendor/kyc/packet',
        headers=vendor_headers,
        json={
            'gst_doc_number': 'GST-12345',
            'gst_file_url': 'https://example.com/gst.pdf',
            'pan_doc_number': 'PAN-5555',
            'pan_file_url': 'https://example.com/pan.pdf',
            'bank_account_name': 'KYC Vendor Pvt Ltd',
            'bank_account_number': '000123456789',
            'bank_ifsc_code': 'NMBL0001',
            'bank_name': 'NMB Bank',
        },
    )
    assert packet_submit.status_code == 200, packet_submit.text

    queue_resp = await client.get('/api/v1/admin/vendors/kyc/queue', headers=admin_headers, params={'filter': 'new'})
    assert queue_resp.status_code == 200
    assert any(row['vendor']['id'] == vendor_id for row in queue_resp.json()['items'])

    assign_reviewer = await client.post(
        f'/api/v1/admin/vendors/{vendor_id}/kyc/assign-reviewer',
        headers=admin_headers,
        json={'reviewer_user_id': __import__('src.apps.iam.utils.hashid', fromlist=['encode_id']).encode_id(reviewer.id)},
    )
    assert assign_reviewer.status_code == 200, assign_reviewer.text

    start_review = await client.post(f'/api/v1/admin/vendors/{vendor_id}/mark-under-review', headers=admin_headers)
    assert start_review.status_code == 200, start_review.text

    reject_as_vendor = await client.post(
        f'/api/v1/admin/vendors/{vendor_id}/kyc/decision/reject',
        headers=vendor_headers,
        json={'reason_code': 'missing_information', 'reason': 'Need clearer docs'},
    )
    assert reject_as_vendor.status_code in {401, 403}

    resubmit_decision = await client.post(
        f'/api/v1/admin/vendors/{vendor_id}/kyc/decision/request-resubmission',
        headers=admin_headers,
        json={'reason_code': 'document_unreadable', 'reason': 'PAN is not readable'},
    )
    assert resubmit_decision.status_code == 200, resubmit_decision.text

    invalid_reason = await client.post(
        f'/api/v1/admin/vendors/{vendor_id}/kyc/decision/reject',
        headers=admin_headers,
        json={'reason_code': 'bad_code', 'reason': 'nope'},
    )
    assert invalid_reason.status_code == 422

    packet_resubmit = await client.put(
        '/api/v1/vendor/kyc/packet',
        headers=vendor_headers,
        json={
            'gst_doc_number': 'GST-12345',
            'gst_file_url': 'https://example.com/gst-v2.pdf',
            'pan_doc_number': 'PAN-5555',
            'pan_file_url': 'https://example.com/pan-v2.pdf',
            'bank_account_name': 'KYC Vendor Pvt Ltd',
            'bank_account_number': '000123456789',
            'bank_ifsc_code': 'NMBL0001',
            'bank_name': 'NMB Bank',
        },
    )
    assert packet_resubmit.status_code == 200, packet_resubmit.text

    restart_review = await client.post(f'/api/v1/admin/vendors/{vendor_id}/mark-under-review', headers=admin_headers)
    assert restart_review.status_code == 200, restart_review.text

    profile = await client.get('/api/v1/vendor/profile', headers=vendor_headers)
    assert profile.status_code == 200
    docs = [doc for doc in profile.json()['documents'] if doc['is_current'] and doc['doc_type'] in {'gst', 'pan'}]
    for doc in docs:
        mark_under_review = await client.post(
            f"/api/v1/admin/vendor-documents/{doc['id']}/mark-under-review",
            headers=admin_headers,
            json={'remarks': 'reviewing', 'expected_uploaded_at': doc['uploaded_at'], 'expected_version': doc['version']},
        )
        assert mark_under_review.status_code == 200, mark_under_review.text
        verify_doc = await client.post(
            f"/api/v1/admin/vendor-documents/{doc['id']}/verify",
            headers=admin_headers,
            json={'remarks': 'ok', 'expected_uploaded_at': doc['uploaded_at'], 'expected_version': doc['version']},
        )
        assert verify_doc.status_code == 200, verify_doc.text

    bank_id = profile.json()['bank_accounts'][0]['id']
    verify_bank = await client.post(f'/api/v1/admin/vendor-bank-accounts/{bank_id}/verify', headers=admin_headers)
    assert verify_bank.status_code == 200, verify_bank.text

    approve_decision = await client.post(
        f'/api/v1/admin/vendors/{vendor_id}/kyc/decision/approve',
        headers=admin_headers,
        json={'reason_code': 'approved', 'reason': 'All checks complete'},
    )
    assert approve_decision.status_code == 200, approve_decision.text

    history = await client.get('/api/v1/vendor/kyc/history', headers=vendor_headers)
    assert history.status_code == 200
    event_types = {event['event_type'] for event in history.json()['items']}
    assert 'vendor.kyc_packet_submitted' in event_types
    assert 'vendor.kyc_reviewer_assigned' in event_types
