import base64
import json
import random
import re
import string
import time
import urllib.error
import urllib.parse
import xbmcvfs
import os

from resources.lib.ui import client, control, jsunpack
from resources.lib.ui.pyaes import AESModeOfOperationCBC, Decrypter, Encrypter


_EMBED_EXTRACTORS = {}
_EDGE_UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36 Edg/116.0.1938.62'
_FF_UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/117.0'


def load_video_from_url(in_url):
    found_extractor = None

    for extractor in list(_EMBED_EXTRACTORS.keys()):
        if in_url.startswith(extractor):
            found_extractor = _EMBED_EXTRACTORS[extractor]
            break

    if found_extractor is None:
        control.log("[*E*] No extractor found for %s" % in_url, 'info')
        return None

    try:
        if found_extractor['preloader'] is not None:
            control.log("Modifying Url: %s" % in_url)
            in_url = found_extractor['preloader'](in_url)

        data = found_extractor['data']
        if data is not None:
            return found_extractor['parser'](in_url,
                                             data)

        control.log("Probing source: %s" % in_url)
        print(f"Initial URL: {in_url}")

        headers = None
        if '|' in in_url:
            in_url, headers = in_url.split('|')
            print(f"Split URL: {in_url}")
            print(f"Raw headers: {headers}")

            headers = dict([item.split('=') for item in headers.split('&')])
            print(f"Parsed headers: {headers}")

            for header in headers:
                headers[header] = urllib.parse.unquote_plus(headers[header])
                print(f"Decoded header: {header} = {headers[header]}")

        reqObj = client.request(in_url, headers=headers, output='extended')
        print(f"Request object: {reqObj}")

        return found_extractor['parser'](reqObj[5],
                                         reqObj[0],
                                         reqObj[2].get('Referer'))
    except urllib.error.URLError:
        return None  # Dead link, Skip result
    except:
        raise

    return None


def __get_packed_data(html):
    packed_data = ''
    for match in re.finditer(r'''(eval\s*\(function\(p,a,c,k,e,.*?)</script>''', html, re.DOTALL | re.I):
        r = match.group(1)
        t = re.findall(r'(eval\s*\(function\(p,a,c,k,e,)', r, re.DOTALL | re.IGNORECASE)
        if len(t) == 1:
            if jsunpack.detect(r):
                packed_data += jsunpack.unpack(r)
        else:
            t = r.split('eval')
            t = ['eval' + x for x in t if x]
            for r in t:
                if jsunpack.detect(r):
                    packed_data += jsunpack.unpack(r)
    return packed_data


def __append_headers(headers):
    return '|%s' % '&'.join(['%s=%s' % (key, urllib.parse.quote_plus(headers[key])) for key in headers])


def __check_video_list(refer_url, vidlist, add_referer=False,
                       ignore_cookie=False):
    nlist = []
    headers = {}
    if add_referer:
        headers.update({'Referer': refer_url})
    for item in vidlist:
        try:
            item_url = item[1]
            temp_req = client.request(item_url, limit=0, headers=headers, output='extended')
            if temp_req[1] != '200':
                control.log("[*] Skiping Invalid Url: %s - status = %d" % (item[1], temp_req.status_code))
                continue  # Skip Item.

            out_url = temp_req[5]
            if ignore_cookie:
                out_url = client.strip_cookie_url(out_url)

            nlist.append((item[0], out_url, item[2]))
        except Exception as e:
            # Just don't add source.
            control.log('Error when checking: {0}'.format(e))
            pass

    return nlist


def __check_video(url):
    temp_req = client.request(url, limit=0, output='extended')
    if temp_req[1] not in ['200', '201']:
        url = None

    return url


def __extract_yourupload(url, page_content, referer=None):
    r = re.search(r"jwplayerOptions\s*=\s*{\s*file:\s*'([^']+)", page_content)
    headers = {'User-Agent': _EDGE_UA,
               'Referer': url}
    if r:
        return r.group(1) + __append_headers(headers)
    return


def __extract_mp4upload(url, page_content, referer=None):
    page_content += __get_packed_data(page_content)
    r = re.search(r'src\("([^"]+)', page_content) or re.search(r'src:\s*"([^"]+)', page_content)
    headers = {'User-Agent': _EDGE_UA,
               'Referer': url,
               'verifypeer': 'false'}
    if r:
        return r.group(1) + __append_headers(headers)
    return


def __extract_lulu(url, page_content, referer=None):
    page_content += __get_packed_data(page_content)
    r = re.search(r'''sources:\s*\[{file:\s*["']([^"']+)''', page_content)
    ref = urllib.parse.urljoin(url, '/')
    headers = {'User-Agent': _FF_UA,
               'Referer': ref,
               'Origin': ref[:-1]}
    if r:
        return r.group(1) + __append_headers(headers)
    return


def __extract_kwik(url, page_content, referer=None):
    page_content += __get_packed_data(page_content)
    r = re.search(r"const\s*source\s*=\s*'([^']+)", page_content)
    if r:
        headers = {'User-Agent': _EDGE_UA,
                   'Referer': url}
        return r.group(1) + __append_headers(headers)


def __extract_okru(url, page_content, referer=None):
    pattern = r'(?://|\.)(ok\.ru|odnoklassniki\.ru)/(?:videoembed|video|live)/(\d+)'
    host, media_id = re.findall(pattern, url)[0]
    aurl = "http://www.ok.ru/dk"
    data = {'cmd': 'videoPlayerMetadata', 'mid': media_id}
    data = urllib.parse.urlencode(data)
    html = client.request(aurl, post=data)
    json_data = json.loads(html)
    if 'error' in json_data:
        return
    strurl = json_data.get('hlsManifestUrl')
    return strurl


def __extract_mixdrop(url, page_content, referer=None):
    r = re.search(r'(?:vsr|wurl|surl)[^=]*=\s*"([^"]+)', __get_packed_data(page_content))
    if r:
        surl = r.group(1)
        if surl.startswith('//'):
            surl = 'https:' + surl
        headers = {'User-Agent': _EDGE_UA,
                   'Referer': url}
        return surl + __append_headers(headers)
    return


def __extract_filemoon(url, page_content, referer=None):
    r = re.search(r'sources:\s*\[{\s*file:\s*"([^"]+)', __get_packed_data(page_content))
    if r:
        surl = r.group(1)
        if surl.startswith('//'):
            surl = 'https:' + surl
        headers = {'User-Agent': _EDGE_UA,
                   'Referer': url}
        return surl + __append_headers(headers)
    return


def __extract_embedrise(url, page_content, referer=None):
    r = re.search(r'<source\s*src="([^"]+)', page_content)
    if r:
        surl = r.group(1)
        if surl.startswith('//'):
            surl = 'https:' + surl
        headers = {'User-Agent': _EDGE_UA,
                   'Referer': url}
        return surl + __append_headers(headers)
    return


def __extract_fusevideo(url, page_content, referer=None):
    r = re.findall(r'<script\s*src="([^"]+)', page_content)
    if r:
        jurl = r[-1]
        js = client.request(jurl, referer=url)
        match = re.search(r'n\s*=\s*atob\("([^"]+)', js)
        if match:
            jd = base64.b64decode(match.group(1)).decode('utf-8')
            surl = re.search(r'":"(http[^"]+)', jd)
            if surl:
                headers = {'User-Agent': _EDGE_UA, 'Referer': url, 'Accept-Language': 'en'}
                return surl.group(1).replace('\\/', '/') + __append_headers(headers)
    return


def __extract_dood(url, page_content, referer=None):
    def dood_decode(pdata):
        t = string.ascii_letters + string.digits
        return pdata + ''.join([random.choice(t) for _ in range(10)])

    pattern = r'(?://|\.)((?:do*ds?(?:tream|ter)?|ds2(?:play|video))\.(?:com?|watch|to|s[ho]|cx|l[ai]|w[sf]|pm|re|yt|stream|pro))/(?:d|e)/([0-9a-zA-Z]+)'
    match = re.search(r'''dsplayer\.hotkeys[^']+'([^']+).+?function\s*makePlay.+?return[^?]+([^"]+)''', page_content, re.DOTALL)
    if match:
        host, media_id = re.findall(pattern, url)[0]
        token = match.group(2)
        nurl = 'https://{0}{1}'.format(host, match.group(1))
        html = client.request(nurl, referer=url)
        if html:
            headers = {'User-Agent': _EDGE_UA,
                       'Referer': url}
            return dood_decode(html) + token + str(int(time.time() * 1000)) + __append_headers(headers)
    return


def __extract_streamtape(url, page_content, referer=None):
    src = re.findall(r'''ById\('.+?=\s*(["']//[^;<]+)''', page_content)
    if src:
        src_url = ''
        parts = src[-1].replace("'", '"').split('+')
        for part in parts:
            p1 = re.findall(r'"([^"]*)', part)[0]
            p2 = 0
            if 'substring' in part:
                subs = re.findall(r'substring\((\d+)', part)
                for sub in subs:
                    p2 += int(sub)
            src_url += p1[p2:]
        src_url += '&stream=1'
        headers = {'User-Agent': _EDGE_UA,
                   'Referer': url}
        src_url = 'https:' + src_url if src_url.startswith('//') else src_url
        return src_url + __append_headers(headers)
    return


def __extract_streamwish(url, page_content, referer=None):
    page_content += __get_packed_data(page_content)
    r = re.search(r'''sources:\s*\[{file:\s*["']([^"']+)''', page_content)
    if r:
        return r.group(1)
    return


def __extract_voe(url, page_content, referer=None):
    r = re.search(r"let\s*(?:wc0|[0-9a-f]+)\s*=\s*'([^']+)", page_content)
    if r:
        r = json.loads(base64.b64decode(r.group(1)).decode('utf-8')[::-1])
        stream_url = r.get('file')
        if stream_url:
            headers = {'User-Agent': _EDGE_UA}
            return stream_url + __append_headers(headers)
    r = re.search(r'''mp4["']:\s*["']([^"']+)''', page_content)
    if r:
        headers = {'User-Agent': _EDGE_UA}
        stream_url = r.group(1)
        if not stream_url.startswith('http'):
            stream_url = base64.b64decode(stream_url).decode('utf-8')
        stream_url = stream_url + __append_headers(headers)
        return stream_url
    r = re.search(r'''hls["']:\s*["']([^"']+)''', page_content)
    if r:
        headers = {'User-Agent': _EDGE_UA}
        stream_url = r.group(1)
        if not stream_url.startswith('http'):
            stream_url = base64.b64decode(stream_url).decode('utf-8')
        stream_url = stream_url + __append_headers(headers)
        return stream_url
    return


def __extract_goload(url, page_content, referer=None):
    def _encrypt(msg, key, iv):
        key = control.bin(key)
        encrypter = Encrypter(AESModeOfOperationCBC(key, iv))
        ciphertext = encrypter.feed(msg)
        ciphertext += encrypter.feed()
        ciphertext = base64.b64encode(ciphertext)
        return ciphertext.decode()

    def _decrypt(msg, key, iv):
        ct = base64.b64decode(msg)
        key = control.bin(key)
        decrypter = Decrypter(AESModeOfOperationCBC(key, iv))
        decrypted = decrypter.feed(ct)
        decrypted += decrypter.feed()
        return decrypted.decode()

    pattern = r'(?://|\.)((?:gogo-(?:play|stream)|streamani|go(?:load|one|gohd)|vidstreaming|gembedhd|playgo1|anihdplay|(?:play|emb|go|s3|s3emb)taku1?)\.' \
              r'(?:io|pro|net|com|cc|online))/(?:streaming|embed(?:plus)?|ajax|load)(?:\.php)?\?id=([a-zA-Z0-9-]+)'
    r = re.search(r'crypto-js\.js.+?data-value="([^"]+)', page_content)
    if r:
        host, media_id = re.findall(pattern, url)[0]
        keys = ['37911490979715163134003223491201', '54674138327930866480207815084989']
        iv = control.bin('3134003223491201')
        params = _decrypt(r.group(1), keys[0], iv)
        eurl = 'https://{0}/encrypt-ajax.php?id={1}&alias={2}'.format(
            host, _encrypt(media_id, keys[0], iv), params)
        response = client.request(eurl, XHR=True)
        try:
            response = json.loads(response).get('data')
        except:
            return
        if response:
            result = _decrypt(response, keys[1], iv)
            result = json.loads(result)
            str_url = ''
            if len(result.get('source')) > 0:
                str_url = result.get('source')[0].get('file')
            if not str_url and len(result.get('source_bk')) > 0:
                str_url = result.get('source_bk')[0].get('file')
            if str_url:
                headers = {'User-Agent': _EDGE_UA,
                           'Referer': 'https://{0}/'.format(host),
                           'Origin': 'https://{0}'.format(host)}
                return str_url + __append_headers(headers)
    return


def __register_extractor(urls, function, url_preloader=None, datas=[]):
    if type(urls) is not list:
        urls = [urls]

    if not datas:
        datas = [None] * len(urls)

    for url, data in zip(urls, datas):
        _EMBED_EXTRACTORS[url] = {
            "preloader": url_preloader,
            "parser": function,
            "data": data
        }


def __ignore_extractor(url, content, referer=None):
    return None


def __relative_url(original_url, new_url):
    if new_url.startswith("http://") or new_url.startswith("https://"):
        return new_url

    if new_url.startswith("//"):
        return "http:%s" % new_url
    else:
        return urllib.parse.urljoin(original_url, new_url)


def get_sub(sub_url, sub_lang):
    content = client.request(sub_url)
    subtitle = xbmcvfs.translatePath('special://temp/')
    fname = f'TemporarySubs.{sub_lang}.srt'
    fpath = os.path.join(subtitle, fname)
    if sub_url.endswith('.vtt'):
        fname = fname.replace('.srt', '.vtt')
        fpath = fpath.replace('.srt', '.vtt')
    fpath = fpath.encode(encoding='ascii', errors='ignore').decode(encoding='ascii')
    fname = fname.encode(encoding='ascii', errors='ignore').decode(encoding='ascii')
    with open(fpath, 'w', encoding='utf-8') as f:
        f.write(content)
    return f'special://temp/{fname}'


def del_subs():
    dirs, files = xbmcvfs.listdir('special://temp/')
    for fname in files:
        if fname.startswith('TemporarySubs'):
            xbmcvfs.delete(f'special://temp/{fname}')


__register_extractor(["https://www.mp4upload.com/",
                      "https://mp4upload.com/"],
                     __extract_mp4upload)

__register_extractor(["https://kwik.cx/",
                      "https://kwik.si/"],
                     __extract_kwik)

__register_extractor(["https://www.yourupload.com/"],
                     __extract_yourupload)

__register_extractor(["https://mixdrop.co/",
                      "https://mixdrop.to/",
                      "https://mixdrop.sx/",
                      "https://mixdrop.bz/",
                      "https://mixdrop.ch/",
                      "https://mixdrop.ag/",
                      "https://mixdrop.gl/",
                      "https://mixdrop.club/",
                      "https://mixdrop.vc/",
                      "https://mixdroop.bz/",
                      "https://mixdroop.co/",
                      "https://mixdrp.to/",
                      "https://mixdrp.co/"],
                     __extract_mixdrop)

__register_extractor(["https://ok.ru/",
                      "odnoklassniki.ru"],
                     __extract_okru)

__register_extractor(["https://dood.wf/",
                      "https://dood.pm/",
                      "https://dood.cx/",
                      "https://dood.la/",
                      "https://dood.li/",
                      "https://dood.ws/",
                      "https://dood.so/",
                      "https://dood.to/",
                      "https://dood.sh/",
                      "https://dood.re/",
                      "https://dood.yt/",
                      "https://dood.stream/",
                      "https://dooodster.com",
                      "https://dood.watch/",
                      "https://doods.pro/",
                      "https://dooood.com/",
                      "https://doodstream.com/",
                      "https://ds2play.com/",
                      "https://ds2video.com/"],
                     __extract_dood,
                     lambda x: x.replace('.wf/', '.li/'))

__register_extractor(["https://gogo-stream.com/",
                      "https://gogo-play.net/",
                      "https://streamani.net/",
                      "https://goload.one/"
                      "https://goload.io/",
                      "https://goload.pro/",
                      "https://gogohd.net/",
                      "https://gogohd.pro/",
                      "https://gembedhd.com/",
                      "https://playgo1.cc/",
                      "https://anihdplay.com/",
                      "https://playtaku.net/",
                      "https://playtaku.online/",
                      "https://gotaku1.com/",
                      "https://goone.pro/",
                      "https://embtaku.pro/",
                      "https://s3taku.com/",
                      "https://embtaku.com/",
                      "https://s3embtaku.pro/"],
                     __extract_goload)

__register_extractor(["https://streamtape.com/e/"],
                     __extract_streamtape)

__register_extractor(["https://filemoon.sx/e/",
                      "https://kerapoxy.cc/e/",
                      "https://smdfs40r.skin/e/",
                      "https://1azayf9w.xyz/e/"],
                     __extract_filemoon)

__register_extractor(["https://embedrise.com/v/"],
                     __extract_embedrise)

__register_extractor(["https://streamwish.com",
                      "https://streamwish.to",
                      "https://wishembed.pro",
                      "https://streamwish.site",
                      "https://strmwis.xyz",
                      "https://embedwish.com",
                      "https://awish.pro",
                      "https://dwish.pro",
                      "https://mwish.pro",
                      "https://filelions.com",
                      "https://filelions.to",
                      "https://filelions.xyz",
                      "https://filelions.live",
                      "https://filelions.com",
                      "https://alions.pro",
                      "https://dlions.pro",
                      "https://mlions.pro"],
                     __extract_streamwish)

__register_extractor(["https://fusevideo.net/e/",
                      "https://fusevideo.io/e/"],
                     __extract_fusevideo)

__register_extractor(["https://voe.sx/e/",
                      "https://brookethoughi.com/e/",
                      "https://rebeccaneverbase.com/e/",
                      "https://loriwithinfamily.com/e/",
                      "https://donaldlineelse.com/e/"],
                     __extract_voe,
                     lambda x: x.replace('/voe.sx/', '/donaldlineelse.com/'))

__register_extractor(["https://lulustream.com",
                      "https://luluvdo.com",
                      "https://kinoger.pw"],
                     __extract_lulu)
