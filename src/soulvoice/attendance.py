from pathlib import Path
import json
import requests
import lxml.html
from urllib.parse import urljoin
import ddddocr

cookies_file = 'cookies.json'
account_file = 'account.txt'
attendance_url = 'https://pt.soulvoice.club/attendance.php'
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36 Edg/114.0.1823.82'
}

# https://scrapfly.io/blog/save-and-load-cookies-in-requests-python/
# to retrieve cookies:
session = requests.Session()
session.headers = headers
try:
    cookies = json.loads(Path(cookies_file).read_text())  # save them to file as JSON
    cookies = requests.utils.cookiejar_from_dict(cookies)  # turn dict to cookiejar
    session.cookies.update(cookies)  # load cookiejar to current session
except Exception:
    print('No session could be restored')


def solve_captch(html):
    # <img src='image.php?action=regimage&amp;imagehash=41df35630571a24397eecfc807a029ef&amp;secret=' border='0' alt='CAPTCHA' />
    tree = lxml.html.fromstring(html)
    captcha_img = tree.xpath('//img[@alt="CAPTCHA"]')[0]
    captcha_img_url = urljoin(attendance_url, captcha_img.get('src'))
    captcha_img_hash = captcha_img_url.split('imagehash=')[1].split('&')[0]

    response_captcha_img = requests.get(captcha_img_url)
    if response_captcha_img.status_code == 200:
        with open('captcha.jpg', 'wb') as f:
            f.write(response_captcha_img.content)

    ocr = ddddocr.DdddOcr(old=True)
    with open('captcha.jpg', 'rb') as f:
        image = f.read()

    captcha_text = ocr.classification(image)

    return captcha_text, captcha_img_hash


# auto follow redirection if no previous session restored
response = session.get(attendance_url)

if 200 != response.status_code:
    raise Exception(f'Abnormal status code: {response.status_code}')

if 'login.php' in response.url:
    print('Login required before proceeding')
    account = Path(account_file).read_text().split()
    imagestring, imagehash = solve_captch(response.text)
    login_url = 'https://pt.soulvoice.club/takelogin.php'
    data = {
        'secret': '',
        'username': account[0],
        'password': account[1],
        'two_step_code': '',
        'imagestring': imagestring,
        'imagehash': imagehash,
        'returnto': 'attendance.php',
    }
    response = session.post(login_url, data=data)

if '签到成功' in response.text:
    tree = lxml.html.fromstring(response.text)
    r = tree.xpath('//a[contains(@href, "userdetails")]')[0]
    level = r.get('class').split('_')[0]
    username = r.text_content()
    points = tree.xpath(
        '//a[contains(@href, "mybonus.php")]/following-sibling::text()[following::a[contains(@href, "attendance.php")]]'
    )[0].split()[1]
    result = tree.xpath("//td/table//table//p")[0].text_content()

    print('站点: soulvoice.club')
    print('用户名: ', username)
    print('等级: ', level)
    print('魔力: ', points)
    print('结果: ', result)

# to save cookies:
cookies = requests.utils.dict_from_cookiejar(
    session.cookies
)  # turn cookiejar into dict
Path(cookies_file).write_text(json.dumps(cookies))  # save them to file as JSON
