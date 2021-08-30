from os import rename
import queue
from cache import Cache
from cachemanager import CacheManager
from config import BaseConfig, LocalConfig
from dumper import dumps
from opensea import OpenSea
from queue import Queue
from random import randint
from requests import get
from shutil import copyfile, copyfileobj
from singleton import Singleton
from threading import Lock, Thread, get_ident
from time import sleep

class Downloader(metaclass=Singleton):
    def __init__(self, baseConfig:BaseConfig, localConfig:LocalConfig, logInfoCallback, logErrorCallback):
        self.baseConfig = baseConfig
        self.localConfig = localConfig
        self.logInfoCallback = logInfoCallback
        self.logErrorCallback = logErrorCallback

        self.lockPool = [Lock(), Lock(), Lock()]
        self.lockPoolLock = Lock()
        self.queue = Queue()
        self.cache = set()

        self.cacheManager = CacheManager(baseConfig, localConfig)
        Thread(target=self.DownloadQueueWorker, daemon=True).start()

    def Enqueue(self, url:str, fileName:str):
        self.queue.put(item={
                'file' : fileName,
                'url' : url
            })

    def GetLock(self) -> Lock:
        with self.lockPoolLock:
            # find the first available lock
            for i, lock in enumerate(self.lockPool):
                if not lock.locked():
                    lock.acquire()
                    return lock
            
            # a lock was not available, wait on one at random
            i = randint(0,2)
            lock = self.lockPool[i]
            lock.acquire()
            return lock

    # inspired by https://stackoverflow.com/questions/13137817/how-to-download-image-using-requests
    def DownloadImage(self, url:str, destination:str, lock:Lock=None, retries = 5):
        if retries < 0:
            self.logErrorCallback(f"DownloadImage {get_ident()}: Retry count for {url} exceeded.")
            self.cache.remove(destination)
            return

        try:
            self.logInfoCallback(f"DownloadImage {get_ident()}: Requesting {url} ...")
            response = get(url, stream=True)
            if response and response.status_code == 200:
                self.logInfoCallback(f"DownloadImage {get_ident()}: Downloading {url}")
                partFile = destination + ".part"
                with open(self.cacheManager.GetCachePath(Cache.Images, partFile), 'wb') as out_file:
                    response.raw.decode_content = True
                    copyfileobj(response.raw, out_file)
                del response

                self.logInfoCallback(f"DownloadImage {get_ident()}: Renaming {partFile} to {destination}")
                rename(
                    self.cacheManager.GetCachePath(Cache.Images, partFile),
                    self.cacheManager.GetCachePath(Cache.Images, destination))
                
                self.cache.remove(destination)
            elif response and response.status_code == 429:
                self.logErrorCallback(f"DownloadImage {get_ident()}: response: {response}")
                OpenSea.RandomSleep(0.1, 3)
                self.DownloadImage(url, destination, lock, retries=retries - 1)
        except Exception as e:
            self.logErrorCallback(str(e))

    def DownloadQueueWorker(self):
        self.logInfoCallback("DownloadQueueWorker starting up.")
        while True:
            item = self.queue.get()
            # we already downloaded this one; skip it
            if item['file'] in self.cache:
                self.queue.task_done()
                continue
            else:
                with self.GetLock():
                    self.cache.add(item['file'])
                    Thread(target=self.DownloadImage, args=(item['url'], item['file']), daemon=True)
                    self.queue.task_done()
            sleep(0.1)