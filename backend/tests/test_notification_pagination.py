from datetime import datetime

from app.models.company import Company, User
from app.models.request import InternalNotification


def test_notification_cursor_keeps_tied_records_scoped_and_does_not_skip_after_read(client, db_session, auth_headers):
    owner = db_session.query(User).filter(User.email == "arya@novaworks.com").one()
    other = db_session.query(User).filter(User.email == "krish@novaworks.com").one()
    stamp = datetime(2030, 1, 1)
    ids = [f"notif-page-qa-{index:02}" for index in range(29)]
    for index, item_id in enumerate(ids):
        db_session.add(InternalNotification(
            id=item_id, company_id=owner.company_id,
            recipient_id=other.id if index == 28 else owner.id,
            notification_type="QA", title="Synthetic notification", body="Pagination QA",
            deep_link="/requests", created_at=stamp,
        ))
    db_session.commit()
    headers = auth_headers(owner.email)
    first = client.get("/api/requests/notifications/inbox?limit=25&unread_only=true", headers=headers).json()
    assert [item["id"] for item in first] == list(reversed(ids[:28]))[:25]
    last = first[-1]
    assert client.post(f"/api/requests/notifications/{last['id']}/read", headers=headers).status_code == 200
    second = client.get("/api/requests/notifications/inbox", headers=headers, params={
        "limit": 25, "unread_only": True, "before_created_at": last["created_at"], "before_id": last["id"],
    }).json()
    assert [item["id"] for item in second[:3]] == list(reversed(ids[:3]))
    assert not ({item["id"] for item in first} & {item["id"] for item in second})
    assert all(item["id"] != ids[28] for item in first + second)
    denied = client.post(f"/api/requests/notifications/{last['id']}/read", headers=auth_headers(other.email))
    assert denied.status_code == 404
    repeated = client.post(f"/api/requests/notifications/{last['id']}/read", headers=headers)
    assert repeated.status_code == 200


def test_notification_cursor_requires_both_fields_and_bounded_limit(client, auth_headers):
    headers = auth_headers("arya@novaworks.com")
    for params in [{"before_id": "one"}, {"before_created_at": "2030-01-01T00:00:00"}, {"limit": 101}, {"limit": 0}]:
        assert client.get("/api/requests/notifications/inbox", params=params, headers=headers).status_code == 422


def test_notification_company_scope_is_checked_even_for_matching_recipient(client, db_session, auth_headers):
    owner = db_session.query(User).filter(User.email == "arya@novaworks.com").one()
    company = Company(name="Notification isolation QA")
    db_session.add(company)
    db_session.flush()
    notification = InternalNotification(
        id="notif-other-company-qa", company_id=company.id, recipient_id=owner.id,
        notification_type="QA", title="Other company", body="Must stay hidden",
        deep_link="/requests", created_at=datetime(2031, 1, 1),
    )
    db_session.add(notification)
    db_session.commit()
    headers = auth_headers(owner.email)
    result = client.get("/api/requests/notifications/inbox", headers=headers)
    assert result.status_code == 200
    assert notification.id not in {item["id"] for item in result.json()}
    assert client.post(f"/api/requests/notifications/{notification.id}/read", headers=headers).status_code == 404
