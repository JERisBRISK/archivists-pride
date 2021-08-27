from singleton import Singleton
from config import BaseConfig

# for card data
class Cards(BaseConfig, metaclass=Singleton):
    def __init__(self, logInfoCallback, logErrorCallback, dataFile='cards.json'):
        super().__init__(logInfoCallback=logInfoCallback, logErrorCallback=logErrorCallback, dataFile=dataFile)
