# coding: utf-8
import os
import shutil
import sys
import time
import yaml
import pickle
import requests
import zipfile
from bs4 import BeautifulSoup
from contextlib import closing
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.remote.remote_connection import LOGGER
import logging


SCRIPT_NAME = 'WoW Addons Updater'
TEMP_FOLDER = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'temp_download')

proxy = {
    "http": "http://127.0.0.1:8080",
    "https": "https://127.0.0.1:8080"
}
# proxy = None
headers = {
    'user-agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/76.0.3809.132 Safari/537.36',
    # 'referer': 'https://www.curseforge.com/wow/addons'
}

class Addon:
    def __init__(self, url):
        self.url = url
        if url.startswith('https://www.curseforge.com'):
            self.host = 'https://www.curseforge.com'
        elif url.startswith('https://www.wowace.com'):
            self.host = 'https://www.wowace.com'
        self.version = ''
        self.href = None
        self.timestamp = 0
        self.id = 0
        self.name = None
        self.need_update = True
    
    def __repr__(self):
        return '<Addon: %s, [%s], need_update: %s>' % (self.name, self.url, self.need_update)

def load_config(config_file):
    with open(config_file) as f:
        return yaml.load(f)

def save_status(addons, saved_file):
    with open(saved_file, 'wb') as f:
        pickle.dump(addons, f)

def load_status(saved_file):
    if os.path.exists(saved_file):
        with open(saved_file, 'rb') as f:
            addons = pickle.load(f)
    else:
        addons = []
    return addons


class ProgressBar(object):

    def __init__(self, title,
                 count=0.0,
                 run_status=None,
                 fin_status=None,
                 total=100.0,
                 unit='', sep='/',
                 chunk_size=1.0):
        super(ProgressBar, self).__init__()
        self.info = "【%s】%s %.2f %s %s %.2f %s"
        self.title = title
        self.total = total
        self.count = count
        self.chunk_size = chunk_size
        self.status = run_status or ""
        self.fin_status = fin_status or " " * len(self.status)
        self.unit = unit
        self.seq = sep

    def __get_info(self):
        # 【名称】状态 进度 单位 分割线 总数 单位
        _info = self.info % (self.title, self.status,
                             self.count/self.chunk_size, self.unit, self.seq, self.total/self.chunk_size, self.unit)
        return _info

    def refresh(self, count=1, status=None):
        self.count += count
        # if status is not None:
        self.status = status or self.status
        end_str = "\r"
        if self.count >= self.total:
            end_str = '\n'
            self.status = status or self.fin_status
        print(self.__get_info(), end=end_str)


class ChromeDriver:

    def __init__(self):

        LOGGER.setLevel(logging.CRITICAL)

        chrome_options = Options()
        # chrome_options.add_argument("--headless")
        # chrome_options.set_headless()
        chrome_options.add_argument("--proxy-server=http://127.0.0.1:8080")

        self.browser_driver = webdriver.Chrome(executable_path=('C:/Program Files (x86)/Google/Chrome/Application/chromedriver.exe'), chrome_options=chrome_options)

        chrome_options2 = Options()
        # chrome_options2.add_argument("--headless")
        chrome_options2.add_argument("--proxy-server=http://127.0.0.1:8080")
        chrome_options2.add_experimental_option("prefs", {
            "download.default_directory": TEMP_FOLDER,
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True
        })
        self.download_driver = webdriver.Chrome(executable_path=('C:/Program Files (x86)/Google/Chrome/Application/chromedriver.exe'), chrome_options=chrome_options2)

        for f in os.listdir(TEMP_FOLDER):
            if f.endswith('.crdownload'):
                last_cr = os.path.join(TEMP_FOLDER, f)
                print('clear: %s' % last_cr)
                os.unlink(last_cr)


    def browser_to(self, url):
        self.browser_driver.get(url)
        html = self.browser_driver.find_element_by_xpath("//*").get_attribute("outerHTML")
        # self.browser_driver.close()
        return html

    def download(self, addon, temp_path):
        def wait_for_downloads_done():
            while True:
                if len([f for f in os.listdir(TEMP_FOLDER) if f.endswith(".crdownload") or f.endswith(".tmp")]) == 0:
                    break
                time.sleep(0.5)

        url = addon.host + addon.href
        print("【%s】%s" % (addon.name, url))
        self.download_driver.get(url)
        wait_for_downloads_done()
        time.sleep(5)
        filepath = max([os.path.join(TEMP_FOLDER, f) for f in os.listdir(TEMP_FOLDER)], key=os.path.getctime)
        # print(filepath)
        # print(os.listdir(TEMP_FOLDER))
        # shutil.move(filepath, temp_path)
        return filepath

    def close(self):
        self.browser_driver.close()
        self.download_driver.close()


chromeDriver = ChromeDriver()


def get_page(url, wow_version):
    obj = Addon(url)
    
    # r = requests.get(url)#, proxies=proxy, headers=headers)
    html = chromeDriver.browser_to(url)

    if obj.host == "https://www.wowace.com":
        soup = BeautifulSoup(html, 'html5lib')
        obj.version = soup.select('.project-file-name-container')[0].text.strip()
        obj.href = soup.select('.fa-icon-download')[0]['href']
        obj.timestamp = soup.select('.tip.standard-date.standard-datetime')[1]['data-epoch']
        obj.id = soup.select('.info-data')[0].text
        obj.name = soup.select('.overflow-tip')[0].text
        obj.need_update = True
    elif obj.host == "https://www.curseforge.com":
        soup = BeautifulSoup(html, 'html5lib')

        if wow_version == 'wow':
            raw_url = soup.select('.button.button--icon-only.button--sidebar')[0]['href']
            timestamp = soup.select('.tip.standard-date.standard-datetime')[2]['data-epoch']
            ver_obj = soup.select('.overflow-tip.truncate')[0]
        elif wow_version == 'wowclassic':
            wowversioncount = len(soup.select('.e-sidebar-subheader.overflow-tip.mb-1'))
            if wowversioncount == 2: #include classic
                raw_url = soup.select('.button.button--icon-only.button--sidebar')[1]['href']
                timestamp = soup.select('.tip.standard-date.standard-datetime')[3]['data-epoch']
                ver_obj = soup.select('.overflow-tip.truncate')[1]
            elif wowversioncount==1: #only classic
                wowversionstring = soup.select('.e-sidebar-subheader.overflow-tip.mb-1')[0].text.strip()
                if wowversionstring == 'WoW Classic':
                    raw_url = soup.select('.button.button--icon-only.button--sidebar')[0]['href']
                    timestamp = soup.select('.tip.standard-date.standard-datetime')[2]['data-epoch']
                    ver_obj = soup.select('.overflow-tip.truncate')[0]
                else:
                    return None
            else:
                return None
        else:
            return None

        obj.version = ver_obj.text
        obj.href = raw_url + '/file'
        obj.timestamp = int(timestamp)
        obj.id = ver_obj['data-id']
        obj.name = soup.select('h2.font-bold.text-lg.break-all')[0].text
        obj.need_update = True
    return obj


def download(addon, temp_path):
    url = addon.host + addon.href
    print("【%s】%s" % (addon.name, url))
    with closing(requests.Session().get(url, stream=True, proxies=proxy)) as response:
        chunk_size = 1024 # 单次请求最大值
        content_size = int(response.headers['content-length']) # 内容体总大小
        progress = ProgressBar(addon.name, total=content_size,
                                         unit="KB", chunk_size=chunk_size, run_status="正在下载", fin_status="下载完成")
        with open(temp_path, "wb") as f:
            for data in response.iter_content(chunk_size=chunk_size):
                f.write(data)
                progress.refresh(count=len(data))


def main(config_file):
    config = load_config(config_file)
    addons = load_status(config['saved_file'])

    new_addons = []
    for url in config['addons']:
        old_addons = [x for x in addons if x.url == url]
        if len(old_addons) > 0:
            old_addon = old_addons[0]
        else:
            old_addon = None

        try:
            new_addon = get_page(url, config['wow_version'])
            if not new_addon:
                print('【%s】，找不到插件' % url)
                continue
            elif old_addon:
                if old_addon.timestamp == new_addon.timestamp and not old_addon.need_update:
                    new_addon.need_update = False
                    print('【%s】，无更新' % (new_addon.name))
                else:
                    print('【%s】，有更新 (%s -> %s)' % (new_addon.name, old_addon.version, new_addon.version))
            else:
                print('【%s】，有更新 (<None> -> %s)' % (new_addon.name, new_addon.version))
        except requests.exceptions.RequestException as e:
            if old_addon:
                new_addon = old_addon
            print('【%s】更新出错' % new_addon.name)
            sys.stderr.write('Error: %s\n' % str(e))
        new_addons.append(new_addon)

    print('插件列表确认完成，开始下载更新.')

    if not os.path.isdir(TEMP_FOLDER):
        os.makedirs(TEMP_FOLDER)

    for addon in new_addons:
        temp_path = os.path.join(TEMP_FOLDER, '%s.zip' % addon.id)
        dest_path = os.path.join(config['wow_path'], 'Interface', 'addons')
        if addon.need_update:
            try:
                temp_path = chromeDriver.download(addon, temp_path)
                # download(addon, temp_path)
                with zipfile.ZipFile(temp_path, 'r') as zip_ref:
                    zip_ref.extractall(dest_path)
                print('【%s】更新完成' % addon.name)
                addon.need_update = False
                save_status(new_addons, config['saved_file'])
            except requests.exceptions.RequestException as e:
                sys.stderr.write('Error: %s\n' % str(e))

    save_status(new_addons, config['saved_file'])
    print('插件更新完成.')

    chromeDriver.close()

if __name__=='__main__':
    print('【%s】脚本启动' % SCRIPT_NAME)
    config_file = sys.argv[1] if len(sys.argv) > 1 else 'wow.yaml'
    main(config_file)
