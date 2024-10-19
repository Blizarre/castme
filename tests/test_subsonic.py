import json
import socketserver
from hashlib import md5
from http.server import BaseHTTPRequestHandler
from threading import Thread
from urllib.parse import parse_qs, urlparse

import pytest
from pytest import fixture

from castme.messages import enable_debug_mode
from castme.subsonic import AlbumNotFoundException, SubSonic

PORT = 4040
VERSION = "1.16.1"
CLIENT_NAME = "tests"


@fixture(scope="module", autouse=True)
def enable_debug():
    enable_debug_mode()


def create_response(status, **data):
    response = {"subsonic-response": {"status": status, "version": VERSION, **data}}
    return json.dumps(response).encode("utf-8")


class MockSubsonicServer(socketserver.TCPServer):
    allow_reuse_port = True


class MockSubsonicHandler(BaseHTTPRequestHandler):
    def okResponse(self, data: bytes):
        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        parsed_path = urlparse(self.path)
        params = parse_qs(parsed_path.query)

        if parsed_path.path == "/rest/ping":
            self.okResponse(create_response("ok"))

        elif parsed_path.path == "/rest/getAlbumList":
            with open("tests/AlbumList.json", "rb") as fd:
                albums = json.load(fd)
            self.okResponse(create_response("ok", albumList=albums))

        elif parsed_path.path == "/rest/getAlbum":
            with open("tests/HighVoltage.json", "rb") as fd:
                album = json.load(fd)
            if params["id"][0] != album["id"]:
                self.send_error(404, "Not Found")
                return
            self.okResponse(create_response("ok", album=album))

        elif parsed_path.path == "/rest/echo":
            self.okResponse(create_response("ok", params=params))

        else:
            self.send_error(404, "Not Found")


@fixture(scope="session")
def mock_server():
    with MockSubsonicServer(("", PORT), MockSubsonicHandler, True) as httpd:
        server_thread = Thread(target=httpd.serve_forever)
        server_thread.start()
        yield PORT
        httpd.shutdown()
        server_thread.join()


@fixture
def subsonic(mock_server):
    return SubSonic(CLIENT_NAME, "castme", "pwd", f"http://localhost:{mock_server}")


def test_call_sonic_no_args(subsonic: SubSonic):
    result = subsonic.call_sonic("ping")
    assert result["subsonic-response"]["status"] == "ok"


def test_check_sonic_auth(subsonic: SubSonic):
    """Checking that the call_sonic method os providing the right parameters.
    The echo endpoint on the subsonic mock server will return all the parameters that
    were sent."""
    result = subsonic.call_sonic("echo")
    params = result["subsonic-response"]["params"]

    assert params["u"] == [subsonic.user]
    assert params["v"] == [VERSION]
    assert params["c"] == [CLIENT_NAME]
    seed1 = params["s"]
    assert params["t"] == [
        md5((subsonic.password + params["s"][0]).encode("utf-8")).hexdigest()
    ]

    # The seed is generated dynamically. We check that it is different each time
    result = subsonic.call_sonic("echo")
    params = result["subsonic-response"]["params"]
    assert seed1 != params["s"]


def test_get_all_albums(subsonic: SubSonic):
    assert subsonic.get_all_albums() == ["Arrival", "High Voltage"]


@pytest.mark.parametrize(
    "raw_title", ["High", "High Vol", "Hoghvoltge", "High Voltage"]
)
def test_get_songs_for_album_fuzzy(subsonic: SubSonic, raw_title):
    title, songs = subsonic.get_songs_for_album(raw_title)
    assert title == "High Voltage"
    assert len(songs) == 2  # noqa: PLR2004
    assert songs[0].title == "The Jack"
    assert songs[0].album_name == title
    assert songs[0].artist == "AC/DC"
    assert songs[0].content_type == "audio/mpeg"
    parsed_path = urlparse(songs[0].url)
    params = parse_qs(parsed_path.query)
    assert params["id"] == ["71463"]
    assert params["u"] == [subsonic.user]
    assert parsed_path.hostname == "localhost"
    assert parsed_path.path == "/rest/stream"

    assert songs[1].title == "Tnt"
    assert songs[1].album_name == title
    assert songs[1].artist == "AC/DC"
    assert songs[1].content_type == "audio/mpeg"
    parsed_path = urlparse(songs[1].album_art)
    params = parse_qs(parsed_path.query)
    # That's coming from the Album from AlbumList
    assert params["id"] == ["23"]
    assert parsed_path.path == "/rest/getCoverArt"


@pytest.mark.parametrize("raw_title", ["XXXX", "XXXXXXXXXXXXXXXXXXXXXx"])
def test_get_songs_for_album_unknown(subsonic: SubSonic, raw_title):
    with pytest.raises(AlbumNotFoundException):
        subsonic.get_songs_for_album(raw_title)
