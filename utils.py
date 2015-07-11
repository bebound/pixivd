class Pixiv_Get_Error(Exception):
    def __init__(self, url):
        self.url = url

    def __str__(self):
        return 'Failed to get data: ' + self.url


def get_image_url_per_illust(data):
    """
    get image_urls from one data
    """
    image_urls = []
    # extract work if the raw data is from ranking
    if 'work' in data:
        data = data['work']

    # not manga
    if not data['is_manga']:
        image_urls.append(data['image_urls']['large'])
    # manga
    else:
        for i in range(data['page_count']):
            per_page_link = data['image_urls']['large'][:-5] + str(i) + data['image_urls']['large'][-4:]
            image_urls.append(per_page_link)
    return image_urls
