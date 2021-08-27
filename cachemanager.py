from os.path import exists
from config import BaseConfig, LocalConfig
from singleton import Singleton
from cache import Cache

class CacheManager(metaclass=Singleton):
    def __init__(self, baseConfig:BaseConfig, localConfig:LocalConfig):
        self.baseConfig = baseConfig
        self.localConfig = localConfig
        self.textures = {}
        self.thumbnails = {}
        self.tooltips = {}

    def IsCached(self, cache, item):
        switch = {
            Cache.Images: lambda: exists(f"{self.localConfig.Get('ImageCacheRoot')}\{item}"),
            Cache.Textures: lambda: item in self.textures,
            Cache.Thumbnails: lambda: item in self.thumbnails,
        }

        if cache in switch:
            return switch[cache]()
        return False

    def GetCachePath(self, cache, item):
        switch = {
            Cache.Images: f"{self.localConfig.Get('ImageCacheRoot')}\{item}"
        }

        if cache in switch:
            return switch[cache]
        return None

    def GetCacheKey(self, tokenId):
        return f"{self.baseConfig.Get('ContractAddress')}.{tokenId}".lower()
