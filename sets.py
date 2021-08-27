from cards import Cards
from ethereum import Ethereum
from json.decoder import JSONDecodeError
from opensea import OpenSea
from os.path import exists
from pushcontainer import push_container
from re import S
from singleton import Singleton
from threading import Thread
from time import time
import dearpygui.dearpygui as dpg
import json
import webbrowser

class Sets(metaclass=Singleton):
    NullAddress = "0x0000000000000000000000000000000000000000"

    def __init__(self, width, height, cards:Cards, walletAddress, contractAddress, logInfoCallback, logErrorCallback, dataFile='sets.json'):
        self.cards = cards
        self.walletAddress = walletAddress
        self.contractAddress = contractAddress

        self.window = dpg.generate_uuid()
        self.totalETHText = dpg.generate_uuid()
        self.totalUSDText = dpg.generate_uuid()
        self.table = dpg.generate_uuid()
        self.dataFile = dataFile
        self.data = {}
        self.setNames = []
        self.columnsIdsByName = {}
        self.lastUpdateTime = 0
        self.logInfoCallback = logInfoCallback
        self.logErrorCallback = logErrorCallback

        self.LoadSetData()

        with dpg.window(id=self.window, label="ParaSets", width=width, height=height, show=False):
            dpg.add_button(label="Refresh", callback=lambda: self.Update())
            self.InitTable()

    def LoadSetData(self):
        if exists(self.dataFile):
            with open(self.dataFile, "r") as f:
                try:
                    self.data = json.load(f)['parasets']
                    self.logInfoCallback(f"{self.dataFile} loaded.")
                except JSONDecodeError as e:
                    self.logErrorCallback(f"{self.dataFile} load failed because: {str(e)}")
        else:
            self.logErrorCallback(f"{self.dataFile} is missing.")
            self.data = {}

    def InitTable(self):
        t = dpg.add_table(
                id=self.table,
                parent=self.window,
                header_row=True,
                sortable=True,
                reorderable=True,
                resizable=True,
                no_host_extendX=True,
                policy=dpg.mvTable_SizingStretchProp)

        with push_container(t) as table:
            self.setNames = sorted(self.data)
            for s in self.setNames:
                self.columnsIdsByName[s] = dpg.add_table_column(label=s, no_sort=True, default_sort=True, prefer_sort_descending=True)
        return table

    def Show(self):
        dpg.configure_item(self.window, show=True)

        if (time() - self.lastUpdateTime >= 60 * 5):
            Thread(target=self.Update, daemon=True).start()

    def Update(self):
        if dpg.does_item_exist(self.table):
            dpg.delete_item(self.table)

        self.table = self.InitTable()

        ethInFiat = Ethereum.GetEthInFiat(1.0)
        ownedAssets = OpenSea.GetAssets(self.walletAddress, self.contractAddress, logInfoCallback=self.logInfoCallback, logErrorCallback=self.logErrorCallback)

        self.lastUpdateTime = time()

        ownedTokens = set([int(a['token_id']) for a in ownedAssets])
        missingPriceBySet = {}
        setPriceBySet = {}
        priceByToken = {}

        with push_container(self.table):
            for setName in sorted(self.data):
                tokensInSet = set(self.data[setName])
                setAssets = OpenSea.GetAssets(
                    walletAddress=None,
                    contractAddress=self.contractAddress,
                    logInfoCallback=self.logInfoCallback,
                    logErrorCallback=self.logErrorCallback,
                    tokens=list(tokensInSet))
                unavailableTokens = []

                missingTokens = tokensInSet - ownedTokens
                missingPriceEth = 0.0
                setPriceEth = 0.0

                for asset in setAssets:
                    id = int(asset['token_id'])
                    sell_orders = asset['sell_orders']
                    tokenIsMissing = id in missingTokens

                    if sell_orders:
                        _, lPrice, __ = OpenSea.GetPrices(sell_orders[0])

                        if (tokenIsMissing):
                            missingPriceEth += lPrice

                        # whether owned or not, add it to the set price
                        priceByToken[id] = lPrice
                        setPriceEth += lPrice
                    else:
                        priceByToken[id] = 0
                        unavailableTokens.append(id)
                        self.logInfoCallback(f"Sets: no listing found for [{id}] {asset['name']} {asset['permalink']}")

                missingPriceBySet[setName] = missingPriceEth
                setPriceBySet[setName] = setPriceEth

                for tokenId in tokensInSet:
                    # default is medium grey
                    color = (150,150,150)

                    if tokenId in ownedTokens:
                        # white
                        color = (255,255,255)
                        if tokenId in unavailableTokens:
                            # purple if you owned and unlisted!
                            color = (255,255,0)
                    if tokenId in unavailableTokens:
                        # red
                        color = (255,0,0)

                    # get the name of the card
                    token = str(tokenId)
                    if self.cards.Has(token):
                        text = self.cards.Get(token)['name']
                    else:
                        text = tokenId

                    card = self.cards.Get(token)
                    dpg.add_button(label="o", user_data=card['link'], callback=lambda _,__,url: webbrowser.open_new_tab(url))
                    dpg.add_same_line()
                    txt = dpg.add_text(default_value=text, color=color)
                    tt = dpg.add_tooltip(parent=txt)
                    dpg.add_text(default_value=f"[{tokenId}] {card['name']}", parent=tt, color=(212,175,55))
                    dpg.add_text(default_value=f"Properties:", parent=tt, color=(0,255,255))
                    for trait in self.cards.Get(token)['traits']:
                        dpg.add_text(default_value=f"  {card['traits'][trait]}", parent=tt)
                    if tokenId in priceByToken:
                        missingTokenPrice = priceByToken[tokenId]
                        dpg.add_text(default_value="Current Token Price:", parent=tt, color=(0,255,255))
                        dpg.add_text(default_value=f"  ETH {missingTokenPrice:0,.4f}", parent=tt)
                        dpg.add_text(default_value=f"  USD ${missingTokenPrice * ethInFiat:0,.2f}", parent=tt)
                        dpg.add_text(default_value="Set Completion Costs:", parent=tt, color=(0,255,255))
                        dpg.add_text(default_value=f"  ETH {missingPriceEth:0,.4f}", parent=tt)
                        dpg.add_text(default_value=f"  USD ${(missingPriceEth * ethInFiat):0,.2f}", parent=tt)
                        dpg.add_text(default_value="Full Set Cost (Lowest Listings):", parent=tt, color=(0,255,255))
                        dpg.add_text(default_value=f"  ETH {setPriceEth:0,.4f}", parent=tt)
                        dpg.add_text(default_value=f"  USD ${(setPriceEth * ethInFiat):0,.2f}", parent=tt)
                        if unavailableTokens:
                            dpg.add_text(default_value="Unavailable Tokens:", parent=tt, color=(255,0,0))
                            for t in unavailableTokens:
                                dpg.add_text(default_value=f"  {self.cards.Get(str(t))['name']}", parent=tt, color=(255,0,0))

                dpg.add_table_next_column()
