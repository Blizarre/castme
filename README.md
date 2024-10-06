# CastMe

CastMe is a simple Python script that allows you to cast music from a Subsonic server to a Chromecast device.

It's pretty bare-bone for now, but as I am using it more and more I will add the features that I need.
The first step will be to be add a config file for the secrets, and then I will add more options than just album search.

### Installation
- Clone the repository
- Install the required dependencies using Poetry or the install target:

```bash
make install
```

### Usage
- Run the script with the desired album name as an argument
- The script will find the closest match for the album name on the Subsonic server
- It will then play the songs from the album on the selected Chromecast device

```bash
poetry run castme "Greatest hist... so far"
Closest match for Greatest hist... so far is Greatest Hits… So Far!!!
19 to play
Finding chromecast
Waiting for cast to be ready
Chromecast ready
Playing Song(title='Get the Party Started', album_name='Greatest Hits… So Far!!!', artist='P!nk', url='
...
```

NOTE: `--chromecast-label` can be used to override the default chromecast name