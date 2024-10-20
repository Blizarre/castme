import difflib
import random
import string
from hashlib import md5
from typing import Any, Dict, List, Tuple
from urllib.parse import urlencode

import requests

from castme.messages import debug as msg_debug
from castme.song import Song


def debug(msg):
    msg_debug("sonic", msg)


class AlbumNotFoundException(Exception):
    def __init__(self, keyword: str):
        self.keyword = keyword

    def __str__(self):
        return f"Album not found with keyword: {self.keyword}"


class SubsonicApiError(Exception):
    def __init__(self, message: str, code: int):
        self.message = message
        self.code = code

    def __str__(self):
        return f"Error {self.code} when calling the Subsonic Server: {self.message}"


SUBSONIC_SUPPORTED_VERSION = "1.16.1"


class SubSonic:
    """API client implementation based on the official documentation:
    https://www.subsonic.org/pages/api.jsp
    """

    def __init__(
        self, app_id: str, user: str, password: str, server_prefix: str
    ) -> None:
        self.app_id = app_id
        self.user = user
        self.password = password
        self.server_prefix = server_prefix

    def make_sonic_url(
        self, verb: str, **kwargs: str | int
    ) -> Tuple[str, Dict[str, Any]]:
        salt = "".join(random.choices(string.ascii_letters + string.digits, k=10))
        token = md5((self.password + salt).encode()).hexdigest()
        parameters = kwargs | {
            "u": self.user,
            "t": token,
            "v": SUBSONIC_SUPPORTED_VERSION,
            "c": self.app_id,
            "f": "json",
            "s": salt,
        }

        return f"{self.server_prefix}/rest/{verb}", parameters

    def call_sonic(self, verb: str, **kwargs: str | int):
        url, parameters = self.make_sonic_url(verb, **kwargs)
        req = requests.get(url, params=parameters, timeout=20)
        req.raise_for_status()
        response = req.json()["subsonic-response"]
        if response["status"] == "failed":
            error_data = response["error"]
            raise SubsonicApiError(error_data["message"], error_data["code"])
        return req.json()

    def get_all_albums(self) -> List[str]:
        albums = self.call_sonic("getAlbumList", type="alphabeticalByName", size=500)[
            "subsonic-response"
        ]["albumList"]["album"]
        return [a["title"] for a in albums]

    def get_songs_for_album(self, album_name: str) -> Tuple[str, List[Song]]:
        output = self.call_sonic("getAlbumList", type="alphabeticalByName", size=500)[
            "subsonic-response"
        ]
        albums = output["albumList"]["album"]
        debug(f"Found {len(albums)}")
        songs = []
        closest = difflib.get_close_matches(
            album_name,
            # This truncation is a hack, but get_close_matches doesn't handle very
            # dissimilar string length well. We essentially assume that the user
            # was lazy and just typed the beginning of the album name, which works
            # actually really well. It is a good enough heuristic for now.
            [a["title"][: len(album_name) + 3] for a in albums],
            1,
        )
        if not closest:
            raise AlbumNotFoundException(album_name)

        debug(f"Closest match {closest}")

        for album in albums:
            debug(f'Looking at {album["title"]}')
            if album["title"][: len(album_name) + 3] == closest[0]:
                cover_url, cover_params = self.make_sonic_url(
                    "getCoverArt", id=album["coverArt"]
                )
                theid = album["id"]
                data = self.call_sonic("getAlbum", id=theid)["subsonic-response"][
                    "album"
                ]["song"]
                for s in data:
                    strurl, params = self.make_sonic_url("stream", id=s["id"])
                    songs.append(
                        Song(
                            s["title"],
                            s["album"],
                            s["artist"],
                            strurl + "?" + urlencode(params),
                            s["contentType"],
                            cover_url + "?" + urlencode(cover_params),
                        )
                    )
                return album["title"], songs

        raise AlbumNotFoundException(album_name)
