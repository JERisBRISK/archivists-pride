from re import S
import dearpygui.dearpygui as dpg
import json
from seahawk import *
from pushcontainer import push_container
import webbrowser

import dearpygui.logger as dpg_logger

class Sets:
    NullAddress = "0x0000000000000000000000000000000000000000"

    def __init__(self, width, height, dataFile='parasets.json'):
        self.window = dpg.generate_uuid()
        self.totalETHText = dpg.generate_uuid()
        self.totalUSDText = dpg.generate_uuid()
        self.table = dpg.generate_uuid()
        self.dataFile = dataFile
        self.data = {}
        self.setNames = []
        self.columnsIdsByName = {}
        self.LoadSetData()

        with dpg.window(id=self.window, label="ParaSets", width=width, height=height, show=False):
            self.InitTable()

    def LoadSetData(self):
        if exists(self.dataFile):
            with open(self.dataFile, "r") as f:
                try:
                    self.data = json.load(f)['parasets']
                    logger.log(f"{self.dataFile} loaded.")
                except JSONDecodeError as e:
                    logger.log(f"{self.dataFile} load failed because: {str(e)}")
        else:
            logger.log(f"{self.dataFile} is missing.")
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
    
    def Hide(self):
        dpg.configure_item(self.window, show=False)

    def Update(self, walletAddress, contractAddress):
        if dpg.does_item_exist(self.table):
            dpg.delete_item(self.table)
        
        self.table = self.InitTable()

        ethInFiat = GetEthInFiat(1.0)
        ownedAssets = GetAssets(walletAddress, contractAddress)
        cardData = GetCardData()['cards']
        ownedTokens = set([int(a['token_id']) for a in ownedAssets])
        missingPriceBySet = {}
        setPriceBySet = {}
        priceByToken = {}

        with push_container(self.table):
            for setName in sorted(self.data):
                tokensInSet = set(self.data[setName])
                setAssets = GetAssets(walletAddress=None, contractAddress=contractAddress, tokens=list(tokensInSet))
                unavailableTokens = []
                
                missingTokens = tokensInSet - ownedTokens
                missingPriceEth = 0.0
                setPriceEth = 0.0

                for asset in setAssets:
                    id = int(asset['token_id'])
                    sell_orders = asset['sell_orders']
                    tokenIsMissing = id in missingTokens

                    if sell_orders:
                        lCurrency, lPrice, lUsdPrice = GetPrices(sell_orders[0])

                        if (tokenIsMissing):
                            missingPriceEth += lPrice

                        # whether owned or not, add it to the set price
                        priceByToken[id] = lPrice
                        setPriceEth += lPrice
                    else:
                        priceByToken[id] = 0
                        unavailableTokens.append(id)
                        logger.log_warning(f"Sets: no listing found for [{id}] {asset['name']} {asset['permalink']}")

                missingPriceBySet[setName] = missingPriceEth
                setPriceBySet[setName] = setPriceEth

                for token in tokensInSet:
                    # default is medium grey
                    color = (150,150,150)

                    if token in ownedTokens:
                        # white
                        color = (255,255,255)
                        if token in unavailableTokens:
                            # purple if you owned and unlisted!
                            color = (255,255,0)
                    if token in unavailableTokens:
                        # red
                        color = (255,0,0)

                    # get the name of the card
                    k = str(token)
                    if k in cardData:
                        text = cardData[k]['name']
                    else:
                        text = token

                    dpg.add_button(label="o", user_data=cardData[k]['link'], callback=lambda _,__,url: webbrowser.open_new_tab(url))
                    dpg.add_same_line()
                    txt = dpg.add_text(default_value=text, color=color)
                    tt = dpg.add_tooltip(parent=txt)
                    dpg.add_text(default_value=f"[{token}] {cardData[k]['name']}", parent=tt, color=(212,175,55))
                    dpg.add_text(default_value=f"Properties:", parent=tt, color=(0,255,255))
                    for trait in cardData[k]['traits']:
                        dpg.add_text(default_value=f"  {cardData[k]['traits'][trait]}", parent=tt)
                    if token in priceByToken:
                        missingTokenPrice = priceByToken[token]
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
                            for token in unavailableTokens:
                                dpg.add_text(default_value=f"  {cardData[str(token)]['name']}", parent=tt, color=(255,0,0))

                dpg.add_table_next_column()
