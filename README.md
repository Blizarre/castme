# CastMe

CastMe is a simple Python REPL that allows you to cast music from a Subsonic server to a Chromecast device, or to the local device.

**NOTE: The subsonic server must expose a URL over HTTPS. And since the chromecast will be the one connecting to the server, the certificate need to be trusted. This project is tested against [Navidrome](https://www.navidrome.org/) only.**

### Installation (pip / pipx / ...)

`castme` is available directly in [pypi](https://pypi.org/project/castme/):
```
pip install castme
```

Just create the configuration file using `--init` and edit the content:

```
> castme --init
Configuration initialized in /home/blizarre/.config/castme.toml, please edit it before starting castme again
```

Castme will automatically look for the `castme.toml` file in `/etc` or in the current directory as well. use `--config` in conjunction with `--init` to set the location of the configuration file.

### Usage

Run the script, and enter the commands in the REPL. For instance:
- List the available Albums
```bash
$ castme
Currently playing on chromecast
[chromecast] >> list
Saint-Saëns: Le carnaval des animaux                Le onde
Brandenburg Concertos 5 and 6 - Violin Concerto     Harold en Italie
```
- Play an album based on fuzzy search
```bash
[chromecast] >> queue Harld enI
Queueing Harold en Italie
```
- Display the queue
```bash
[chromecast] >> queue
 1 Harold in the mountains (Adagio - Allegro) / Harold en Italie by Hector Berlioz
 2 The Pilgrim's Procession (Allegretto) / Harold en Italie by Hector Berlioz
 3 Serenade of an Abruzzian highlander (Allegro assai) / Harold en Italie by Hector Berlioz
 4 The Robbers' orgies (Allegro frenetico) / Harold en Italie by Hector Berlioz
 ```
- Set the volume to 50%, then increase by 20%
```bash
[chromecast] >> volume 50
[chromecast] >> volume +20
```
- Pause and resume
```bash
[chromecast] >> playpause
[chromecast] >> playpause
```
- List the backends and switch to the local backend to play the music on the computer
```bash
[chromecast] >> switch
Available targets: chromecast, local
[chromecast] >> switch local
```
- Skip the current song and display the new queue
```bash
[local] >> next
[local] >> q
 1 The Pilgrim's Procession (Allegretto) / Harold en Italie by Hector Berlioz
 2 Serenade of an Abruzzian highlander (Allegro assai) / Harold en Italie by Hector Berlioz
 3 The Robbers' orgies (Allegro frenetico) / Harold en Italie by Hector Berlioz
```
- Exit the app
```bash
>> quit
```

commands: `help,  list (l),  next (n), rewind (r),  play (p),  playpause (pp),  queue (q),  quit (x),  volume (v),  clear (c)`.

Aliases are defined for the most common commands (in parenthesis).


### Installation (dev)
- Clone the repository
- Install the required dependencies using Poetry or the `install` makefile target:

```bash
make install
```
- Copy the config file template "castme/assets/castme.toml.template" to one of the supported directory and update the values inside
  - "castme.toml"
  - "~/.config/castme.toml"
  - "/etc/castme.toml"

During development, `make dev` will run the formatters and linters for the project.

There is a debug mode that print additional information at runtime. Use the `--debug` flag.