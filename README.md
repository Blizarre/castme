# CastMe

CastMe is a simple Python REPL that allows you to cast music from a Subsonic server to a Chromecast device.

**NOTE: The subsonic server must expose a URL over HTTPS. And since the chromecast will be the one connecting to the server, the certificate need to be trusted. This project is tested against [Navidrome](https://www.navidrome.org/) only.**

It's pretty bare-bone for now, but as I am using it more and more I will add the features that I need.

### Installation
- Clone the repository
- Install the required dependencies using Poetry or the install target:

```bash
make install
```
- Copy the config file template "castme.toml.template" to one of the supported directory and update the values inside
  - "castme.toml"
  - "~/.config/castme.toml"
  - "/etc/castme.toml"


### Usage
- Run the script, a REPL will appear:

```bash
> poetry run castme
Loading config from /home/blizarre/.config/castme.toml
Finding chromecast
Waiting for cast to be ready
Chromecast ready
CastMe

>> play Harold enItal
Playing song Harold in the mountains (Adagio - Allegro) / Harold en Italie by Hector Berlioz
>> queue
 0 The Pilgrim's Procession (Allegretto) / Harold en Italie by Hector Berlioz
 1 Serenade of an Abruzzian highlander (Allegro assai) / Harold en Italie by Hector Berlioz
 2 The Robbers' orgies (Allegro frenetico) / Harold en Italie by Hector Berlioz
>> playpause
>> playpause
>> quit
```

commands: `help  list  next  play  playpause  queue  quit  volume`