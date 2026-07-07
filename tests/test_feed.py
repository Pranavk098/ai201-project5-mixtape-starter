"""
tests/test_feed.py — Mixtape

Tests for the "Friends Listening Now" feed logic.
"""

import pytest
from datetime import datetime, timedelta, timezone
from app import create_app, db
from models import User, Song, ListeningEvent, friendships
from services.feed_service import get_friends_listening_now


@pytest.fixture
def app():
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"})
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture
def friends(app):
    """A user with two friends: one who listened 20 hours ago, one 10 minutes ago."""
    with app.app_context():
        me = User(username="me", email="me@example.com")
        stale_friend = User(username="stale_friend", email="stale@example.com")
        recent_friend = User(username="recent_friend", email="recent@example.com")
        db.session.add_all([me, stale_friend, recent_friend])
        db.session.flush()

        for f in (stale_friend, recent_friend):
            db.session.execute(friendships.insert().values(user_id=me.id, friend_id=f.id))
            db.session.execute(friendships.insert().values(user_id=f.id, friend_id=me.id))

        stale_song = Song(title="Yesterday Song", artist="X", shared_by=me.id)
        recent_song = Song(title="Right Now Song", artist="Y", shared_by=me.id)
        db.session.add_all([stale_song, recent_song])
        db.session.flush()

        now = datetime.now(timezone.utc)
        db.session.add(ListeningEvent(
            user_id=stale_friend.id, song_id=stale_song.id,
            listened_at=now - timedelta(hours=20),
        ))
        db.session.add(ListeningEvent(
            user_id=recent_friend.id, song_id=recent_song.id,
            listened_at=now - timedelta(minutes=10),
        ))
        db.session.commit()

        yield {"me": me, "stale_friend": stale_friend, "recent_friend": recent_friend}


def test_listening_now_excludes_friend_from_yesterday(app, friends):
    """A friend who listened 20 hours ago should not appear as 'listening now'."""
    with app.app_context():
        result = get_friends_listening_now(friends["me"].id)
        usernames = [r["friend"]["username"] for r in result]
        assert "stale_friend" not in usernames


def test_listening_now_includes_truly_recent_friend(app, friends):
    """A friend who listened 10 minutes ago should appear as 'listening now'."""
    with app.app_context():
        result = get_friends_listening_now(friends["me"].id)
        usernames = [r["friend"]["username"] for r in result]
        assert usernames == ["recent_friend"]
