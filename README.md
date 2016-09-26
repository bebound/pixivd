# Pixiv Downloader
---

A simple tool to download all illustrations from specific illustrator.

Download illustrations by **uers\_id**, **daily ranking** or **history ranking**.

---

## Features
- [x] Keep login sessions
  - [x] Local storage
  - [x] Secure storage (not memory safe)
- [x] Update downloaded artists
- [x] Refresh downloaded artists
- [x] Mutil-Language
- [x] Command-line interface


## Usage

```
Usage:
    pixiv.py
    pixiv.py <id>...
    pixiv.py -r [-d | --date=<date>]
    pixiv.py -u

Arguments:
    <id>                                       user_ids

Options:
    -r                                         Download by ranking
    -d <date> --date <date>                    Target date
    -u                                         Update exist folder
    -h --help                                  Show this screen
    -v --version                               Show version

Examples:
    pixiv.py 7210261 1980643
    pixiv.py -r -d 2016-09-24
```


## Screenshot


![img](https://raw.github.com/bebound/Pixiv/master/ScreenShot/4.png)


## Credits
- [Pixiv-API](https://github.com/twopon/Pixiv-API)
- [PixivPy](https://github.com/upbit/pixivpy)
- [pixiv api](https://danbooru.donmai.us/wiki_pages/58938)
