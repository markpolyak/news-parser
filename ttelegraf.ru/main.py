import requests
from bs4 import BeautifulSoup
import fake_useragent
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry


HOST = 'https://www.ttelegraf.ru'
FILE = 'news.tsv'


def requests_retry_session(retries=3, backoff_factor=0.5):
    session = requests.Session()
    retry = Retry(
        total=retries,
        read=retries,
        connect=retries,
        backoff_factor=backoff_factor)
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session


def get_html(url):
    user = fake_useragent.UserAgent().random
    headers = {
        'user-agent': user,
        'accept': '*/*'}
    r = requests_retry_session().get(url, headers=headers)
    return r


def get_pages_count(html):
    soup = BeautifulSoup(html, 'html.parser')
    pagination = soup.find_all('a', class_='page-numbers')
    return int(pagination[-2].get_text())


def get_years(html):
    soup = BeautifulSoup(html, 'html.parser')
    years_tags = soup.find('div', class_='col-row').find_all('p')

    years = []
    for year in years_tags:
        years.append(int(year.get('id')))
    return years


def get_year_links(html, year_num):
    soup = BeautifulSoup(html, 'html.parser')
    year_tag = soup.find('div', class_='col-row').find('p', id=f'{year_num}')
    year_tag_links = year_tag.find_all('a')

    links = []
    for link in year_tag_links:
        links.append(link.get('href'))
    return links


def get_news_info(html):
    soup = BeautifulSoup(html, 'html.parser')
    items = soup.find_all('article', class_='post post-tp-24')

    news = []
    for item in items:
        news.append({
            'title': item.find('div', class_='title-13-2').get_text(strip=True).replace('\u200b', ''),
            'date': item.find('div', class_='tag-shower-2').get_text(strip=True)
            [:item.find('div', class_='tag-shower-2').get_text(strip=True).find(':') + 3],
            'link': item.find('a').get('href'),
            'text': ''
        })
    return news


def get_news_text(html):
    soup = BeautifulSoup(html, 'html.parser')
    paragraphs = soup.find('div', class_='post-content').find_all('p')

    text = ""
    for paragraph in paragraphs:
        if paragraph != paragraphs[-1]:
            text = text + paragraph.get_text(strip=True) + ' '
        else:
            text = text + paragraph.get_text(strip=True)

    return text


def save_file(items, path):
    with open(path, 'a') as file:
        for item in items:
            file.write("%s\t%s\t%s\t%s\n" % (item['title'], item['date'],
                                             item['link'], item['text']))


def parse_month(url):
    month_items = []

    html = get_html(url)
    if html.status_code == 200:

        pages_count = get_pages_count(html.text)

        for page in range(1, pages_count + 1):
            html = get_html(url + f'/page/{page}/')
            if html.status_code == 200:
                month_items.extend(get_news_info(html.text))
            else:
                print('Ошибка открытия страницы с новостями')

        for item in month_items:
            html = get_html(item['link'])
            if html.status_code == 200:
                item['text'] = get_news_text(html.text)
            else:
                print('Ошибка открытия страницы новости')
    else:
        print('Ошибка открытия страницы месяца')

    return month_items


def parse_archive(url):
    month_names = ['январь', 'февраль', 'март', 'апрель', 'май', 'июнь',
                   'июль', 'август', 'сентябрь', 'октябрь', 'ноябрь', 'декабрь']

    html = get_html(url)
    if html.status_code == 200:
        years = get_years(html.text)

        print('Находим ссылки для каждого месяца...\n')
        links = []
        for year in years:
            links.extend(get_year_links(html.text, year))

        for link in links:
            items = []
            month_value = int(link[6:8]) - 1
            year_value = link[1:5]
            print(f'Парсим новости за {month_names[month_value]} {year_value} года...')
            items.extend(parse_month(HOST + link))
            save_file(items, FILE)
    else:
        print('Ошибка открытия страницы архива')

    print(f'\nПарсинг завершён успешно!')


parse_archive(HOST + '/archive')
