class Pixiv_Get_Error(Exception):
    def __init__(self, url):
        self.url = url

    def __str__(self):
        return 'Failed to get data: ' + self.url
