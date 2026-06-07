# PixivD

[![PyPI version](https://img.shields.io/pypi/v/pixivd?logo=pypi)](https://pypi.org/project/pixivd/)
[![GHCR](https://img.shields.io/badge/docker-ghcr.io-blue?logo=docker)](https://github.com/bebound/pixiv/pkgs/container/pixivd)
[![Python](https://img.shields.io/badge/python-3.10+-blue?logo=python)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Docker Build](https://img.shields.io/github/actions/workflow/status/bebound/pixiv/publish-docker.yml?branch=release&logo=github&label=docker)](https://github.com/bebound/pixiv/actions/workflows/publish-docker.yml)
[![PyPI Publish](https://img.shields.io/github/actions/workflow/status/bebound/pixiv/publish-pypi.yml?branch=release&logo=github&label=pypi)](https://github.com/bebound/pixiv/actions/workflows/publish-pypi.yml)

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

