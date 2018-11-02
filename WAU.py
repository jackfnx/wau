# coding: utf-8
import yaml
import pickle
import os
import sys
import requests
import zipfile
import random
import time
from bs4 import BeautifulSoup
from contextlib import closing

SCRIPT_NAME = 'WoW Addons Updater'
SAVED_FILE = 'saved.pickle'
CONFIG_FILE = 'config.yaml'
TEMP_FOLDER = 'temp_download'

class Addon:

    @staticmethod
    def extract_host(url):
        if url.startswith('https://wow.curseforge.com/projects'):
            return 'https://wow.curseforge.com'
        elif url.startswith('https://www.curseforge.com/wow/addons'):
            return 'https://www.curseforge.com'
        elif url.startswith('https://www.wowace.com/projects'):
            return 'https://www.wowace.com'
        else:
            raise 'Unknown host'

    def __init__(self, url):
        self.url = url
        self.host = self.extract_host(url)
        self.href = None
        self.timestamp = 0
        self.id = 0
        self.name = None
        self.need_update = True
    
    def __repr__(self):
        return '<Addon: %s, [%s], need_update: %s>' % (self.name, self.url, self.need_update)


def load_config():
    with open(CONFIG_FILE) as f:
        return yaml.load(f)
    
def save_status(addons):
    with open(SAVED_FILE, 'wb') as f:
        pickle.dump(addons, f)

def load_status():
    if os.path.exists(SAVED_FILE):
        with open(SAVED_FILE, 'rb') as f:
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



def jump_url(jump_page):

    response = requests.get(jump_page)
    html = response.text

    soup = BeautifulSoup(html, 'html5lib')
    url = soup.select('.download__link')[0]['href']
    return url


def get_page(url):
    obj = Addon(url)
    
    response = requests.get(url)
    html = response.text
    
    soup = BeautifulSoup(html, 'html5lib')
    if obj.host == 'https://www.curseforge.com':
        jump_page = soup.select('.button--download')[0]['href']
        obj.href = jump_url(obj.host + jump_page)
        obj.id = int(random.random() * 10000)
        obj.name = soup.select('[itemprop="title"]')[3].text
        obj.timestamp = soup.select('.tip.standard-date.standard-datetime')[0]['data-epoch']
    else:
        obj.href = soup.select('.fa-icon-download')[0]['href']
        obj.id = soup.select('.info-data')[0].text
        obj.name = soup.select('.overflow-tip')[0].text
        obj.timestamp = soup.select('.tip.standard-date.standard-datetime')[1]['data-epoch']
    obj.need_update = True
    return obj


def download(addon, temp_path):
    url = addon.host + addon.href
    print("【%s】%s" % (addon.name, url))
    with closing(requests.get(url, stream=True)) as response:
        chunk_size = 1024 # 单次请求最大值
        content_size = int(response.headers['content-length']) # 内容体总大小
        progress = ProgressBar(addon.name, total=content_size,
                                         unit="KB", chunk_size=chunk_size, run_status="正在下载", fin_status="下载完成")
        with open(temp_path, "wb") as f:
            for data in response.iter_content(chunk_size=chunk_size):
                f.write(data)
                progress.refresh(count=len(data))



def main():
    config = load_config()
    addons = load_status()

    new_addons = []
    for url in config['addons']:
        old_addons = [x for x in addons if x.url == url]
        if len(old_addons) > 0:
            old_addon = old_addons[0]
        else:
            old_addon = None

        try:
            new_addon = get_page(url)
            if old_addon and old_addon.timestamp == new_addon.timestamp and not old_addon.need_update:
                new_addon.need_update = False
                print('【%s】，无更新' % new_addon.name)
            else:
                print('【%s】，有更新' % new_addon.name)
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
        temp_path = os.path.join('temp_download', '%s.zip' % addon.id)
        dest_path = os.path.join(config['wow_path'], 'Interface', 'addons')
        if addon.need_update:
            try:
                download(addon, temp_path)
                with zipfile.ZipFile(temp_path, 'r') as zip_ref:
                    zip_ref.extractall(dest_path)
                print('【%s】更新完成' % addon.name)
                addon.need_update = False
                save_status(new_addons)
            except requests.exceptions.RequestException as e:
                sys.stderr.write('Error: %s\n' % str(e))

    save_status(new_addons)
    print('插件更新完成.')


if __name__=='__main__':
    print('【%s】脚本启动' % SCRIPT_NAME)
    main()
