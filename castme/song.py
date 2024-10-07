from dataclasses import dataclass


@dataclass
class Song:
    title: str
    album_name: str
    artist: str
    url: str
    content_type: str
    album_art: str

    def __str__(self) -> str:
        return f"{self.title} / {self.album_name} by {self.artist}"
