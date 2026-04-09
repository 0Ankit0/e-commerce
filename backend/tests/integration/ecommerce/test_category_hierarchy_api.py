from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.apps.core.security import TokenType, create_access_token, get_password_hash, verify_token
from src.apps.iam.models.token_tracking import TokenTracking
from src.apps.iam.models.user import User, UserProfile


async def _create_admin_headers(db_session: AsyncSession) -> dict[str, str]:
    user = User(
        username='catalog_admin',
        email='catalog-admin@example.com',
        hashed_password=get_password_hash('TestPass123!'),
        is_active=True,
        is_superuser=True,
        is_confirmed=True,
    )
    db_session.add(user)
    await db_session.flush()
    db_session.add(UserProfile(user_id=user.id, first_name='Catalog'))

    token = create_access_token(user.id, expires_delta=timedelta(hours=1))
    payload = verify_token(token, token_type=TokenType.ACCESS)
    exp = payload['exp']
    expires_at = datetime.fromtimestamp(exp, tz=timezone.utc) if isinstance(exp, (int, float)) else datetime.now(timezone.utc)
    db_session.add(
        TokenTracking(
            user_id=user.id,
            token_jti=payload['jti'],
            token_type=TokenType.ACCESS,
            ip_address='127.0.0.1',
            user_agent='pytest',
            is_active=True,
            expires_at=expires_at,
        )
    )
    await db_session.commit()
    return {'Authorization': f'Bearer {token}'}


@pytest.mark.asyncio
async def test_category_hierarchy_constraints_and_concurrency(client: AsyncClient, db_session: AsyncSession):
    headers = await _create_admin_headers(db_session)

    root = await client.post('/api/v1/admin/categories', headers=headers, json={'name': 'Root', 'slug': 'root', 'level': 1})
    assert root.status_code == 201, root.text
    root_category = root.json()['category']

    child = await client.post(
        '/api/v1/admin/categories',
        headers=headers,
        json={'name': 'Child', 'slug': 'child', 'parent_id': root_category['id'], 'level': 2},
    )
    assert child.status_code == 201, child.text
    child_category = child.json()['category']

    grandchild = await client.post(
        '/api/v1/admin/categories',
        headers=headers,
        json={'name': 'Grandchild', 'slug': 'grandchild', 'parent_id': child_category['id'], 'level': 3},
    )
    assert grandchild.status_code == 201, grandchild.text

    too_deep = await client.post(
        '/api/v1/admin/categories',
        headers=headers,
        json={'name': 'Too Deep', 'slug': 'too-deep', 'parent_id': grandchild.json()['category']['id'], 'level': 4},
    )
    assert too_deep.status_code == 422

    stale_update = await client.patch(
        f"/api/v1/admin/categories/{child_category['id']}",
        headers=headers,
        json={
            'name': 'Child v2',
            'slug': 'child-v2',
            'parent_id': root_category['id'],
            'level': 2,
            'description': '',
            'attributes': [],
            'sort_order': 0,
            'expected_updated_at': '2020-01-01T00:00:00+00:00',
        },
    )
    assert stale_update.status_code == 409

    categories = await client.get('/api/v1/categories', headers=headers)
    assert categories.status_code == 200
    cycle_attempt = await client.patch(
        f"/api/v1/admin/categories/{root_category['id']}",
        headers=headers,
        json={
            'name': 'Root',
            'slug': 'root',
            'parent_id': child_category['id'],
            'level': 2,
            'description': '',
            'attributes': [],
            'sort_order': 0,
            'expected_updated_at': next(item for item in categories.json()['items'] if item['id'] == root_category['id'])['updated_at'],
        },
    )
    assert cycle_attempt.status_code == 400

    slug_collision = await client.post('/api/v1/admin/categories', headers=headers, json={'name': 'Root Copy', 'slug': 'root', 'level': 1})
    assert slug_collision.status_code == 409
    slug_collision_on_update = await client.patch(
        f"/api/v1/admin/categories/{child_category['id']}",
        headers=headers,
        json={
            'name': 'Child',
            'slug': 'root',
            'parent_id': root_category['id'],
            'level': 2,
            'description': '',
            'attributes': [],
            'sort_order': 0,
        },
    )
    assert slug_collision_on_update.status_code == 409

    delete_without_migration = await client.delete(f"/api/v1/admin/categories/{root_category['id']}", headers=headers)
    assert delete_without_migration.status_code == 400

    merge_target = await client.post('/api/v1/admin/categories', headers=headers, json={'name': 'Merged', 'slug': 'merged', 'level': 1})
    assert merge_target.status_code == 201

    delete_with_migration = await client.request(
        'DELETE',
        f"/api/v1/admin/categories/{child_category['id']}",
        headers=headers,
        json={'migrate_to_category_id': merge_target.json()['category']['id']},
    )
    assert delete_with_migration.status_code == 200, delete_with_migration.text

    updated_categories = await client.get('/api/v1/categories', headers=headers)
    assert updated_categories.status_code == 200
    ids = {item['id'] for item in updated_categories.json()['items']}
    assert child_category['id'] not in ids

    reorder_payload = {
        'items': [
            {
                'id': item['id'],
                'parent_id': item.get('parent_id'),
                'sort_order': index,
            }
            for index, item in enumerate(updated_categories.json()['items'])
        ]
    }
    reorder = await client.post('/api/v1/admin/categories/reorder', headers=headers, json=reorder_payload)
    assert reorder.status_code == 200, reorder.text

    invalid_parent_reorder = await client.post(
        '/api/v1/admin/categories/reorder',
        headers=headers,
        json={
            'items': [
                {
                    **item,
                    'parent_id': 'OQ',  # arbitrary encoded id that does not exist
                }
                if item['id'] == merge_target.json()['category']['id']
                else item
                for item in reorder_payload['items']
            ]
        },
    )
    assert invalid_parent_reorder.status_code == 400


@pytest.mark.asyncio
async def test_category_attribute_schema_crud(client: AsyncClient, db_session: AsyncSession):
    headers = await _create_admin_headers(db_session)

    category_resp = await client.post(
        '/api/v1/admin/categories',
        headers=headers,
        json={'name': 'Wearables', 'slug': 'wearables', 'level': 1, 'attributes': [{'name': 'size'}]},
    )
    assert category_resp.status_code == 201, category_resp.text
    category_id = category_resp.json()['category']['id']

    initial_attrs = await client.get(f'/api/v1/admin/categories/{category_id}/attributes', headers=headers)
    assert initial_attrs.status_code == 200, initial_attrs.text
    assert [item['name'] for item in initial_attrs.json()['attributes']] == ['size']

    add_attr = await client.post(
        f'/api/v1/admin/categories/{category_id}/attributes',
        headers=headers,
        json={'name': 'color', 'type': 'select', 'required': True, 'options': ['red', 'blue']},
    )
    assert add_attr.status_code == 201, add_attr.text
    assert [item['name'] for item in add_attr.json()['attributes']] == ['size', 'color']

    duplicate_attr = await client.post(
        f'/api/v1/admin/categories/{category_id}/attributes',
        headers=headers,
        json={'name': 'Color'},
    )
    assert duplicate_attr.status_code == 400

    patch_attr = await client.patch(
        f'/api/v1/admin/categories/{category_id}/attributes/color',
        headers=headers,
        json={'name': 'finish', 'options': ['matte', 'glossy']},
    )
    assert patch_attr.status_code == 200, patch_attr.text
    assert sorted(item['name'] for item in patch_attr.json()['attributes']) == ['finish', 'size']

    replace_attrs = await client.put(
        f'/api/v1/admin/categories/{category_id}/attributes',
        headers=headers,
        json={'attributes': [{'name': 'material', 'type': 'text'}, {'name': 'origin', 'type': 'text'}]},
    )
    assert replace_attrs.status_code == 200, replace_attrs.text
    assert sorted(item['name'] for item in replace_attrs.json()['attributes']) == ['material', 'origin']

    delete_attr = await client.delete(f'/api/v1/admin/categories/{category_id}/attributes/material', headers=headers)
    assert delete_attr.status_code == 200, delete_attr.text
    assert [item['name'] for item in delete_attr.json()['attributes']] == ['origin']
