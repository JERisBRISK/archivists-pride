from functools import cache
from os.path import exists
from json import load, dump
from singleton import Singleton
from threading import Thread

# for application-specific data
class BaseConfig(metaclass=Singleton):
    def __init__(self, logInfoCallback, logErrorCallback, dataFile='config_base.json'):
        self.dataFile = dataFile
        self.data = {}
        self.logInfoCallback = logInfoCallback
        self.logErrorCallback = logErrorCallback
        self.Load()

    def Get(self, cacheKey, defaultValue=None):
        if self.Has(cacheKey):
            return self.data[cacheKey]
        else:
            return defaultValue

    def Has(self, cacheKey):
        return cacheKey in self.data

    def Set(self, cacheKey, value):
        self.data[cacheKey] = value
        Thread(target=self.Save, daemon=False)
        return value

    def Load(self):
        if exists(self.dataFile):
            try:
                with open(self.dataFile, "r") as f:
                    self.data = load(f)
                    self.logInfoCallback(f"{self.dataFile} loaded.")
            except Exception as e:
                self.logErrorCallback(f"{self.dataFile} load failed because: {str(e)}")
        else:
            self.logErrorCallback(f"{self.dataFile} is missing.")
            self.data = {}
        return self

    def Save(self):
        try:
            with open(self.dataFile, "w") as f:
                dump(self.data, f, indent=2, separators=(',',': '))
                self.logInfoCallback(f"{self.dataFile} saved.")
        except Exception as e:
            self.logErrorCallback(f"{self.dataFile} could not be saved because: {str(e)}")
        return self

# for user-specific data
class LocalConfig(BaseConfig, metaclass=Singleton):
    def __init__(self, logInfoCallback, logErrorCallback, dataFile='config_local.json'):
        super().__init__(logInfoCallback=logInfoCallback, logErrorCallback=logErrorCallback, dataFile=dataFile)

