from uuid import uuid4

import pytest

from app.models import ItemPhoto
from test_claims import add_item, claims_api  # noqa: F401


JPEG = b'\xff\xd8\xffphoto'
PNG = b'\x89PNG\r\n\x1a\nphoto'
WEBP = b'RIFF\x04\x00\x00\x00WEBPphoto'
MAX_SIZE = 5 * 1024 * 1024


@pytest.mark.parametrize('content_type,data', [
    ('image/jpeg', JPEG), ('image/png', PNG), ('image/webp', WEBP),
])
def test_creator_upload_and_public_get(claims_api, content_type, data):
    client, db, creator, _owner, headers, _team, _team_headers = claims_api
    item = add_item(db, creator)
    path = f'/api/v1/items/{item.id}/photo'
    old_updated_at = item.updated_at

    response = client.put(path, headers={**headers, 'Content-Type': content_type}, content=data)

    assert response.status_code == 200
    assert response.headers['cache-control'] == 'no-store'
    db.refresh(item)
    url = f'{path}?v={int(item.photo_updated_at.timestamp() * 1000)}'
    assert response.json()['photo_url'] == url
    assert item.updated_at == item.photo_updated_at
    assert item.updated_at > old_updated_at
    saved = db.get(ItemPhoto, item.id)
    assert saved.data == data
    assert saved.updated_at == item.photo_updated_at
    photo = client.get(url)
    assert photo.status_code == 200
    assert photo.content == data
    assert photo.headers['content-type'] == content_type
    assert photo.headers['cache-control'] == 'public, max-age=31536000, immutable'
    assert photo.headers['x-content-type-options'] == 'nosniff'
    assert client.get('/api/v1/items').json()['data'][0]['photo_url'] == url
    assert client.get(f'/api/v1/items/{item.id}', headers=headers).json()['photo_url'] == url

    replacement = client.put(path, headers={**headers, 'Content-Type': 'image/png'}, content=PNG)
    assert replacement.status_code == 200
    assert client.get(replacement.json()['photo_url']).content == PNG
    assert db.get(ItemPhoto, item.id).content_type == 'image/png'


def test_non_creator_and_unauthenticated_upload_rejected(claims_api):
    client, db, _creator, owner, headers, _team, team_headers = claims_api
    item = add_item(db, owner)
    path = f'/api/v1/items/{item.id}/photo'
    for auth in [headers, team_headers]:
        response = client.put(path, headers={**auth, 'Content-Type': 'image/jpeg'}, content=JPEG)
        assert response.status_code == 403
        assert response.json()['error']['code'] == 'FORBIDDEN'
    assert client.put(path, headers={'Content-Type': 'image/jpeg'}, content=JPEG).status_code == 401
    assert db.get(ItemPhoto, item.id) is None


@pytest.mark.parametrize('content_type,data,extra,status,code', [
    ('text/plain', JPEG, {}, 415, 'UNSUPPORTED_MEDIA_TYPE'),
    ('image/jpeg', PNG, {}, 422, 'VALIDATION_ERROR'),
    ('image/png', JPEG, {}, 422, 'VALIDATION_ERROR'),
    ('image/webp', b'RIFFxxxxFAIL', {}, 422, 'VALIDATION_ERROR'),
    ('image/jpeg', b'', {}, 422, 'VALIDATION_ERROR'),
    ('image/jpeg', JPEG + b'x' * MAX_SIZE, {'Content-Length': '1'}, 413, 'PAYLOAD_TOO_LARGE'),
    ('image/jpeg', JPEG, {'Content-Length': str(MAX_SIZE + 1)}, 413, 'PAYLOAD_TOO_LARGE'),
], ids=['unsupported-type', 'jpeg-mismatch', 'png-mismatch', 'webp-mismatch', 'empty', 'actual-oversized', 'declared-oversized'])
def test_invalid_photo_rejected(claims_api, content_type, data, extra, status, code):
    client, db, creator, _owner, headers, _team, _team_headers = claims_api
    item = add_item(db, creator)
    response = client.put(f'/api/v1/items/{item.id}/photo',
                          headers={**headers, 'Content-Type': content_type, **extra}, content=data)
    assert response.status_code == status
    assert response.json()['error']['code'] == code
    assert isinstance(response.json()['error']['details'], list)
    assert db.get(ItemPhoto, item.id) is None
    db.refresh(item)
    assert item.photo_updated_at is None


def test_absent_photo_and_missing_item(claims_api):
    client, db, creator, _owner, headers, _team, _team_headers = claims_api
    item = add_item(db, creator)
    response = client.get(f'/api/v1/items/{item.id}/photo')
    assert response.status_code == 404
    assert response.json()['error']['code'] == 'PHOTO_NOT_FOUND'
    path = f'/api/v1/items/{uuid4()}/photo'
    for response in [client.get(path), client.put(path, headers={**headers, 'Content-Type': 'image/jpeg'}, content=JPEG)]:
        assert response.status_code == 404
        assert response.json()['error']['code'] == 'ITEM_NOT_FOUND'
    assert client.get('/api/v1/items').json()['data'][0]['photo_url'] is None
    assert client.get(f'/api/v1/items/{item.id}', headers=headers).json()['photo_url'] is None
    created = client.post('/api/v1/items', headers=headers, json={
        'type': 'lost', 'name': 'Keys', 'description': 'Two keys', 'category': 'Other',
        'date': '2026-11-14', 'location': 'Library',
    })
    assert created.status_code == 201
    assert created.json()['photo_url'] is None


def test_maximum_size_and_status_response(claims_api):
    client, db, creator, _owner, headers, _team, team_headers = claims_api
    item = add_item(db, creator, type='lost')
    data = JPEG + b'x' * (MAX_SIZE - len(JPEG))
    uploaded = client.put(f'/api/v1/items/{item.id}/photo',
                          headers={**headers, 'Content-Type': 'image/jpeg'}, content=data)
    assert uploaded.status_code == 200
    assert client.get(uploaded.json()['photo_url']).content == data
    updated = client.patch(f'/api/v1/items/{item.id}/status', headers=team_headers,
                           json={'status': 'returned'})
    assert updated.status_code == 200
    assert updated.json()['photo_url'] == uploaded.json()['photo_url']
