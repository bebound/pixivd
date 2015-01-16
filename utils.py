class PivivUtils():
    @staticmethod
    def get_original_links(illust):
        """
        get original_links from illust.pages and illust.illust480

        Args:
            illust: a PixivIllustModel instance

        Return:
            a list contains the original illust urls
        """
        original_urls = []
        illust.pages = 1 if illust.pages == '' else int(illust.pages)
        for page in range(illust.pages):
            if 'mobile' in illust.illust480:
                """
                old style:
                change http://i2.pixiv.net/img38/img/luciahreat/mobile/37766477_480mw.jpg
                to http://i2.pixiv.net/img38/img/luciahreat/37766477.jpg
                """
                base_url = illust.illust480[:illust.illust480.find(r'mobile/')]
                if page == 0:
                    file_name = illust.illust_id + '.' + illust.illust_ext
                else:
                    file_name = illust.illust_id + '_p' + str(page) + '.' + illust.illust_ext
                original_urls.append(base_url + file_name)
            else:
                if '_480mw' in illust.illust480:
                    """
                    new style:
                    change http://i2.pixiv.net/c/480x960/img-master/img/2014/10/18/02/31/58/46605041_480mw.jpg
                    to http://i2.pixiv.net/img-original/img/2014/10/18/02/31/58/46605041_p0.jpg
                    """
                    base_url = illust.illust480[:illust.illust480.find(r'_480mw') - len(illust.illust_id)]
                    base_url = base_url.replace('c/480x960/img-master/', 'img-original/')
                    if page == 0:
                        file_name = illust.illust_id + '_p0.' + illust.illust_ext
                    else:
                        file_name = illust.illust_id + '_p' + str(page) + '.' + illust.illust_ext
                    original_urls.append(base_url + file_name)
                elif '_master1200.jpg' in illust.illust480:
                    """
                    ugoira file
                    change http://i4.pixiv.net/c/480x960/img-master/img/2015/01/14/12/37/32/48169827_master1200.jpg
                    to http://i4.pixiv.net/img-zip-ugoira/img/2015/01/14/12/37/32/48169827_ugoira600x600.zip
                    """
                    ugoira_url = illust.illust480.replace('c/480x960/img-master/img/', 'img-zip-ugoira/img/')
                    ugoira_url = ugoira_url.replace('_master1200.jpg', '_ugoira600x600.zip')
                    original_urls.append(ugoira_url)
                    break

        return original_urls