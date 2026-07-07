"""
tests/test_notifications.py — Mixtape

Tests for notification creation logic.
"""

import pytest
from app import create_app, db
from models import User, Song
from services.notification_service import rate_song, add_to_playlist, get_notifications


@pytest.fixture
def app():
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"})
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture
def sharer_and_friend(app):
    with app.app_context():
        sharer = User(username="sharer", email="sharer@example.com")
        friend = User(username="friend", email="friend@example.com")
        db.session.add_all([sharer, friend])
        db.session.flush()

        song = Song(title="Test Song", artist="Test Artist", shared_by=sharer.id)
        db.session.add(song)
        db.session.commit()

        yield {"sharer": sharer, "friend": friend, "song": song}


def test_rating_a_song_notifies_the_sharer(app, sharer_and_friend):
    """Rating a friend's shared song should notify the original sharer."""
    with app.app_context():
        sharer = sharer_and_friend["sharer"]
        friend = sharer_and_friend["friend"]
        song = sharer_and_friend["song"]

        rate_song(friend.id, song.id, 5)

        notifs = get_notifications(sharer.id)
        assert len(notifs) == 1
        assert notifs[0]["type"] == "song_rated"


def test_rating_your_own_song_does_not_notify_yourself(app, sharer_and_friend):
    """Rating your own shared song should not create a notification."""
    with app.app_context():
        sharer = sharer_and_friend["sharer"]
        song = sharer_and_friend["song"]

        rate_song(sharer.id, song.id, 4)

        notifs = get_notifications(sharer.id)
        assert notifs == []
