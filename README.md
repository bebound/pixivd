# PixivD

[![PyPI version](https://badge.fury.io/py/pixivd.svg)](https://badge.fury.io/py/pixivd)

A simple tool to download illustrations from Pixiv.

Download illustrations by **uers\_id**, **daily ranking** or **history ranking**.

## Features

- [x] Keep login sessions
    - [x] Local storage
    - [x] Secure storage (not memory safe)
- [x] Update downloaded artists
- [x] Refresh downloaded artists
- [x] Mutil-Language
- [x] Command-line interface
- [x] Docker image

## Installation

`pip install pixivd`

Or you can use it with `uv`'s `uvx pixivd`

### Docker

`docker run -v ~/.config/pixivd:/root/.config/pixivd --rm -it ghcr.io/bebound/pixivd`

## Usage

```
usage: pixivd [-h] [-r] [-d DATE] [-u] [--version] [userid ...]

Pixiv downloader

positional arguments:
  userid           Pixiv user id

options:
  -h, --help       show this help message and exit
  -r               Download by ranking
  -d, --date DATE  Target date (use with -r), e.g. 2016-09-24
  -u               Update exist folder
  --version        Show version

Examples:
    pixivd 7210261 1980643
    pixivd -r -d 2016-09-24
```

The illusts will be downloaded to `illustrations` folder in current directory.

## Screenshot

![img](https://raw.github.com/bebound/Pixiv/master/ScreenShot/3.0.png)

## Credits

- [Pixiv-API](https://github.com/twopon/Pixiv-API)
- [PixivPy](https://github.com/upbit/pixivpy)
- [pixiv api](https://danbooru.donmai.us/wiki_pages/58938)
- [Pixiv OAuth Flow](https://gist.github.com/ZipFile/c9ebedb224406f4f11845ab700124362)

