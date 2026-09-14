from app.security import create_queue_status_token, decode_queue_status_token


def test_queue_status_token_round_trip():
    token = create_queue_status_token(123)
    assert decode_queue_status_token(token) == 123


def test_queue_status_token_rejects_access_token():
    from app.security import create_access_token

    token = create_access_token("admin")
    assert decode_queue_status_token(token) is None
