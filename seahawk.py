from json.decoder import JSONDecodeError
import enum
import random
from os import environ
from os.path import exists
import shutil
import time
import requests
import json
from requests.api import delete
from web3 import Web3, contract
import dearpygui.dearpygui as dpg
import dearpygui.logger as dpg_logger
import webbrowser
from queue import Empty, Queue
from threading import Lock, Event, Thread
import dumper
from datetime import datetime
from globals_ import *
import math
#from openlistings import OpenListings

def SetInterval(interval, func, *args):
    stopped = Event()
    func(*args)
    def loop():
        while not stopped.wait(interval): # the first call is in `interval` secs
            func(*args)
    Thread(target=loop, daemon=True).start()
    return stopped.set

# Image cache root
AppDataRoot = f"{environ['appdata']}\Seahawk"
CacheRoot = f"{AppDataRoot}\Cache"
ImageCacheRoot = f"{CacheRoot}\Images"

# Cache mechanisms
TextureCache = {}
ThumbnailCache = {}
TokenSupplyCache = {}
TooltipCache = {}

TokenSupplyJsonFile = f"{CacheRoot}\TokenData.json"

def GetCardData():
    ParaCardsJsonFile = "paracards.json"
    data = {}
    if exists(ParaCardsJsonFile):
        with open(ParaCardsJsonFile, "r") as f:
            try:
                logger.log(f"{ParaCardsJsonFile} loaded.")
                data = json.load(f)
            except JSONDecodeError as e:
                logger.log(f"{ParaCardsJsonFile} load failed because: {str(e)}")
    return data

def SaveCardData(data):
    ParaCardsJsonFile = "paracards.json"
    with open(ParaCardsJsonFile, "w") as f:
        json.dump(data, f, indent=2, separators=(',',': '))
        logger.log(f"{ParaCardsJsonFile} saved.")

def LoadTokenSupplyCache():
    global TokenSupplyCache
    if exists(TokenSupplyJsonFile):
        with open(TokenSupplyJsonFile, "r") as f:
            try:
                TokenSupplyCache = json.load(f)
                logger.log(f"{TokenSupplyJsonFile} loaded.")
                #[logger.log(f"  {k}:{v}") for k,v in TokenSupplyCache.items()]
            except JSONDecodeError as e:
                logger.log(f"{TokenSupplyJsonFile} load failed because: {str(e)}")
    else:
        TokenSupplyCache = {}

def SaveTokenSupplyCache():
    global TokenSupplyCache
    with open(TokenSupplyJsonFile, "w") as f:
        json.dump(TokenSupplyCache, f)
        logger.log(f"{TokenSupplyJsonFile} saved.")

class Cache(enum.Enum):
    Images = 1
    Textures = 2
    Thumbnails = 3
    TokenSupply = 4

def IsCached(cache, item):
    switch = {
        Cache.Images: lambda: exists(f"{ImageCacheRoot}\{item}"),
        Cache.Textures: lambda: item in TextureCache,
        Cache.Thumbnails: lambda: item in ThumbnailCache,
        Cache.TokenSupply: lambda: item in TokenSupplyCache,
    }

    if cache in switch:
        return switch[cache]()
    return False

def GetCachePath(cache, item):
    switch = {
        Cache.Images: f"{ImageCacheRoot}\{item}"
    }

    if cache in switch:
        return switch[cache]
    return None

def GetCacheKey(contractAddress, tokenId):
    return f"{contractAddress}.{tokenId}".lower()

# from dearpygui.demo import *
# show_demo()
# dpg.start_dearpygui()
# exit()

# Init the log
logger = dpg_logger.mvLogger()

# Ethereum Wallet address
#ownerId = "0xc1eacdc144a41628c6ff985acead70c2194bdb75"
#ownerId = "0xEB95ff72EAb9e8D8fdb545FE15587AcCF410b42E"

# Console globals
firstCol = 7
fiat = "USD"

# Init Ethereum Mainnet connection
w3 = Web3(Web3.HTTPProvider('https://mainnet.infura.io/v3/58c9fc5b6b7b493089f4d174a610beeb'))


NullAddress = "0x0000000000000000000000000000000000000000"

# Parallel contract
#assetContractAddress = "0x76be3b62873462d2142405439777e971754e8e77"
#contractAddress = w3.toChecksumAddress(assetContractAddress)
# based on https://eips.ethereum.org/EIPS/eip-1155
ABI = json.loads('[{"constant":true,"inputs":[{"name":"_owner","type":"address"},{"name":"_id","type":"uint256"}],"name":"balanceOf","outputs":[{"name":"","type":"uint256"}],"payable":false,"stateMutability":"view","type":"function"}]')
#contract = w3.eth.contract(contractAddress, abi=ABI)

def GetEthInFiat(ethQty : float):
    response = requests.get('https://api.coinbase.com/v2/exchange-rates?currency=ETH')
    data = json.loads(response.text)
    rate = float(data['data']['rates'][fiat])
    return rate * ethQty

def GetTokenQuantity(walletAddress, contractAddress, tokenId):
    global ABI
    contract = w3.eth.contract(w3.toChecksumAddress(contractAddress), abi=ABI)
    return int(contract.functions.balanceOf(walletAddress, tokenId).call())

def GetAssetNameAndLink(order):
    assetName = order['asset']['name']
    link = order['asset']['permalink']
    return assetName, link

def GetBestPrice(tokenId, contractAddress):
    lastOffer = GetOffers(tokenId, contractAddress)['orders'][0]
    lastListing = GetListings(tokenId, contractAddress)['orders'][0]
    _, lastOfferPrice, __ = GetPrices(lastOffer)
    _, lastListingPrice, __ = GetPrices(lastListing)
    return max(lastOfferPrice, lastListingPrice)

def GetCurrentListingPrice(tokenId, contractAddress):
    #lastOffer = GetOffers(tokenId, contractAddress)['orders'][0]
    lastListing = GetListings(tokenId, contractAddress)['orders'][0]
    #_, lastOfferPrice, __ = GetPrices(lastOffer)
    _, lastListingPrice, __ = GetPrices(lastListing)
    return lastListingPrice
    
def GetLastSalePrice(asset):
    if asset['last_sale']:
        qty = int(asset['last_sale']['quantity'])
        decimals = int(asset['last_sale']['payment_token']['decimals'])
        price = float(asset['last_sale']['total_price']) / qty / (10**decimals)
        currency = asset['last_sale']['payment_token']['symbol']

        # DAI is usually locked to $1, just like USDC
        if "USDC" == currency or "DAI" == currency:
            price = price / GetEthInFiat(1.0)
    else:
        price = 0

    return price

def GetPrices(order):
    ethInFiat = GetEthInFiat(1.0)
    qty = int(order['metadata']['asset']['quantity'])
    decimals = int(order['payment_token_contract']['decimals'])
    price = float(order['current_price']) / qty / (10**decimals)
    currency = order['payment_token_contract']['symbol']
    usdPrice = float(0.0)

    # DAI is usually locked to $1, just like USDC
    if "USDC" == currency or "DAI" == currency:
        usdPrice = price
        price = price / ethInFiat
    else:
        usdPrice = price * ethInFiat

    return currency, price, usdPrice

def GetUserNameAndAddress(order):
    user = order['maker']['user']
    userName = "Unknown"
    if user and 'username' in user:
        userName = user['username']
    userAddress = "http://opensea.io/{0}".format(order['maker']['address'])
    return userName, userAddress

def GetTokens(walletAddress, contractAddress):
    assets = GetAssets(walletAddress, contractAddress)
    return [str(row['token_id']) for row in assets]

def GetTotalTokenSupply(contractAddress, tokenId, retries=5):
    if retries < 0:
        return -1

    global TokenSupplyCache
    if not TokenSupplyCache:
        LoadTokenSupplyCache()

    cacheKey = GetCacheKey(contractAddress, tokenId)
    # value is cached, return it
    if cacheKey in TokenSupplyCache:
        #logger.log(f"Cache hit: {cacheKey}")
        return TokenSupplyCache[cacheKey]

    #logger.log(f"Cache miss: {cacheKey}")

    url = "https://api.opensea.io/api/v1/events"
    headers = {"Accept": "application/json"}

    query = {
        # by using the null address, we scope into the initial mint of tokens
        "account_address":NullAddress,
        "asset_contract_address":contractAddress,
        "token_id":f"{tokenId}",
        "event_type":"transfer",
        "only_opensea":"false",
        "offset":"0",
        "limit":"1",
    }

    response = requests.request("GET", url, headers=headers, params=query)

    if response.status_code == 200:
        r = json.loads(response.text)
        # the result was ok, but empty. try again
        if not len(r['asset_events']):
            quantity = GetTotalTokenSupply(contractAddress=contractAddress, tokenId=tokenId, retries=retries - 1)
        else:
            quantity = int(r['asset_events'][0]['quantity'])
    else:
        time.sleep(random.randint(10,30))
        quantity = GetTotalTokenSupply(contractAddress=contractAddress, tokenId=tokenId, retries=retries - 1)

    # cache the answer if it's valid
    record = {}
    if quantity > 0:
        mintingAddress = w3.toChecksumAddress(dpg.get_value(MintingAddressText))
        record = {
            "Minted" : quantity,
            "Withheld" : GetTokenQuantity(mintingAddress, contractAddress, tokenId)
        }

        TokenSupplyCache[cacheKey] = record
        
        # save the cache
        SaveTokenSupplyCache()

    return record

def GetAssets(walletAddress, contractAddress, tokens:list[int] = [], limit:int = 50):
    global StatusBarText
    # API will not return more than 50 items
    # and we should always request at least 1
    limit = max(1, min(limit, 50))

    url = "https://api.opensea.io/api/v1/assets"
    headers = {"Accept": "application/json"}

    query = {
        "asset_contract_address":contractAddress,
        "order_direction":"desc",
        "offset":0,
        "limit":limit
    }

    if walletAddress:
        query['owner'] = walletAddress

    assets = []

    # divide the request into chunks, capped at limit
    # but always get at least 1 chunk
    chunks = max(1, int(math.ceil(len(tokens) / limit)))

    for s in range(0, chunks):
        logger.log("GetAssets: Requesting chunk {s}/{chunks}")
        requestedAssetCount = 0

        if len(tokens) > 0:
            lowerBound = s * limit
            upperBound = (s + 1) * limit
            query['token_ids'] = tokens[lowerBound : upperBound]
            requestedAssetCount = len(query['token_ids'])
            logger.log(f"Issuing {dumper.dumps(query)}")
            dpg.set_value(StatusBarText, f"Requesting {requestedAssetCount} assets from OpenSea.")

        thereMayBeMore = True
        offset = 0

        while thereMayBeMore:
            response = requests.request("GET", url, headers=headers, params=query)
            if response:
                if response.status_code == 200:
                    data = json.loads(response.text)
                    if 'assets' in data:
                        responseAssets = data['assets']
                        count = len(responseAssets)

                        if count == limit and not count == requestedAssetCount:
                            offset += count
                            query['offset'] = offset
                            time.sleep(random.random() * 11)
                        else:
                            thereMayBeMore = False

                        assets.extend(responseAssets)
                        dpg.set_value(StatusBarText, f"Received {len(assets)} assets from OpenSea.")
                elif response.status_code == 429:
                    msg = f"OpenSea: [{response.status_code}] {response.text}"
                    logger.log_error(msg)
                    time.sleep(random.random() * 11)
                    thereMayBeMore = True
            else:
                thereMayBeMore = False
                dpg.set_value(StatusBarText, f"OpenSea: [{response.status_code}] {response.text}")

    return assets

def GetListings(tokenId, contractAddress):
    time.sleep(0.2)
    url = "https://api.opensea.io/wyvern/v1/orders"
    headers = {"Accept": "application/json"}
    listingQuery = {
        "asset_contract_address":contractAddress,
        "taker":NullAddress,
        "bundled":"false",
        "include_bundled":"false",
        "include_invalid":"false",
        "token_id":tokenId,
        "side":"1",
        "sale_kind":"0",
        "limit":"1",
        "offset":"0",
        "order_by":"eth_price",
        "order_direction":"asc"
    }

    response = requests.request("GET", url, headers=headers, params=listingQuery)
    return json.loads(response.text)

def GetOffers(tokenId, contractAddress):
    time.sleep(0.2)
    url = "https://api.opensea.io/wyvern/v1/orders"
    headers = {"Accept": "application/json"}

    offersQuery = {
        "asset_contract_address":contractAddress,
        "taker":NullAddress,
        "bundled":"false",
        "include_bundled":"false",
        "include_invalid":"false",
        "token_id":tokenId,
        "side":"0",
        "sale_kind":"0",
        "limit":"1",
        "offset":"0",
        "order_by":"eth_price",
        "order_direction":"desc"
    }

    response = requests.request("GET", url, headers=headers, params=offersQuery)
    return json.loads(response.text)
    
def DownloadImage(url, destination):
    # inspired by https://stackoverflow.com/questions/13137817/how-to-download-image-using-requests
    logger.log(f"Downloading {url}")
    dpg.set_value(StatusBarText, f"Downloading {url}")
    try:
        response = requests.get(url, stream=True)
        if response and response.status_code == 200:
            with open(GetCachePath(Cache.Images, destination), 'wb') as out_file:
                response.raw.decode_content = True
                shutil.copyfileobj(response.raw, out_file)
            del response
            logger.log(f"{destination} downloaded.")
        else:
            logger.log_error(f"response: {response}")
    except Exception as e:
        logger.log_error(str(e))

DownloadQueue = Queue()
DownloadCache = set()

def DownloadQueueWorker():
    global DownloadCache
    logger.log("DownloadQueueWorker starting up.")
    while True:
        item = DownloadQueue.get()
        # we already downloaded this one; skip it
        if item in DownloadCache:
            logger.log(f"{item} is in DownloadCachce")
            logger.logs(dumper.dumps(item))
            DownloadQueue.task_done()
            continue
        else:
            logger.log(f"{item} is NOT in DownloadCachce")
            logger.log(dumper.dumps(item))
            DownloadCache.add(item)
            #item()
            DownloadQueue.task_done()
        time.sleep(1)

Thread(target=DownloadQueueWorker, daemon=True).start()

class DataColumns(enum.Enum):
    TokenId = 1
    Quantity = 2
    ETH = 3
    USD = 4
    Name = 5
    Link = 6
    ImageUrl = 7
    ThumbnailUrl = 8
    Properties = 9
    TotalSupply = 10
    WithheldSupply = 11
    UnreleasedPercentage = 12

def SortTableData(column, descending):
    global TableDataLock
    global TableData
    global TableSortPreference
    TableDataLock.acquire()
    TableData = sorted(TableData, key=lambda r: r[column], reverse=descending)
    TableSortPreference = (column, descending)
    TableDataLock.release()

TableData = []
TableDataLock = Lock()

def UpdateTableData(walletAddress, contractAddress):
    global TableData
    global TableDataLock
    global TableSortPreference

    ethPrice = GetEthInFiat(1.0)

    # prevent re-entrancy    
    if TableDataLock.locked():
        return
    else:
        TableDataLock.acquire()

    netWorthInEth = 0.0
    netWorthInFiat = 0.0
    i = 0.0

    TableData.clear()

    assets = GetAssets(walletAddress, contractAddress)
    numAssets = float(len(assets))

    for asset in assets:
        i += 1.0

        name = asset['name']
        link = asset['permalink']
        tokenId = int(asset['token_id'])
        imageUrl = asset['image_original_url']
        thumbUrl = asset['image_thumbnail_url']
        properties = {t['trait_type']:t['value'] for t in asset['traits']}
        supply = GetTotalTokenSupply(contractAddress=contractAddress, tokenId=tokenId)
        ownedQuantity = GetTokenQuantity(walletAddress, contractAddress, tokenId)
        price = GetLastSalePrice(asset)

        netWorthInEth += price * ownedQuantity
        netWorthInFiat += price * ownedQuantity * ethPrice
        usdPrice = price * ethPrice

        row = {
            DataColumns.TokenId.name : tokenId,
            DataColumns.Quantity.name : ownedQuantity,
            DataColumns.ETH.name :price,
            DataColumns.USD.name : usdPrice,
            DataColumns.Name.name : name,
            DataColumns.Link.name : link,
            DataColumns.ImageUrl.name : imageUrl,
            DataColumns.ThumbnailUrl.name : thumbUrl,
            DataColumns.Properties.name : properties,
            DataColumns.TotalSupply.name : supply['Minted'],
            DataColumns.WithheldSupply.name : supply['Withheld'],
            DataColumns.UnreleasedPercentage.name : supply['Withheld'] / supply['Minted'] * 100
        }

        TableData.append(row)

        try:
            percentage = i / numAssets
            dpg.set_value(ProgressBar, percentage)
            dpg.configure_item(ProgressBar, overlay="Loaded {0:,} assets.".format(int(i), int(numAssets)))
        except Exception as e:
            logger.log_error(str(e))

    # todo: find a better place to update these
    dpg.set_value(EthPriceText, "${0:,.2f}".format(ethPrice))
    dpg.set_value(AssetValueInEth, "{0:,.4f}".format(netWorthInEth))
    dpg.set_value(AssetValueInFiat, "${0:,.2f}".format(netWorthInFiat))
    dpg.set_value(LastUpdateText, datetime.now().strftime("%c"))

    TableDataLock.release()
    column, descending = TableSortPreference
    SortTableData(column, descending)

assetsTableLock = Lock()
def UpdateAssetsTable(parent, walletAddress, contractAddress, table):
    # prevent re-entrancy    
    if assetsTableLock.locked():
        return
    else:
        assetsTableLock.acquire()

    global TableData
    global TableDataLock

    if not TableData:
        UpdateTableData(walletAddress, contractAddress)

    TableDataLock.acquire()
    
    try:
        dpg.delete_item(table)
    except:
        pass

    def SortHandler(sender, app_data, user_data):
        column, direction = app_data[0]
        columnName = dpg.get_item_configuration(column)['label']
        SortTableData(columnName, direction != 1)
        UpdateAssetsTable(parent, walletAddress, contractAddress, table)

    def HoverHandler(sender, app_data, user_data):
        global CardWindow
        global CardWindowImage
        global CardWindowImageTexture
        global TextureCache
        global TooltipCache

        fileName = user_data['FileName']

        # the current image displayed is the same as the image we're trying to display
        if dpg.does_item_exist(CardWindowImage):
            if dpg.get_item_user_data(CardWindowImage) == fileName:
                return

        # the texture is already loaded, so just switch to it
        if IsCached(Cache.Textures, fileName):
            dpg.set_item_user_data(CardWindowImage, fileName)
            w, h, data = TextureCache[fileName]
            dpg.set_value(CardWindowImageTexture, data)
            return

        # the texture isn't in the file cache
        if not IsCached(Cache.Images, fileName):
            dpg.set_value(StatusBarText, f"Adding {fileName} to download queue.")
            DownloadQueue.put(lambda u=user_data['URL'],f=fileName: DownloadImage(u, f))

        # the texture is in the file cache, so load it
        if IsCached(Cache.Images, fileName):
            # load the texture
            fullName = GetCachePath(Cache.Images, fileName)
            success = False
            while not success:
                try:
                    f = open(fullName)
                    f.close()
                    success = True
                except IOError:
                    logger.log("Could not open file, trying again...")

            w, h, _, data = dpg.load_image(GetCachePath(Cache.Images, fileName))
            # cache it
            TextureCache[fileName] = (w, h, data)
            # set it
            with dpg.texture_registry():
                if dpg.does_item_exist(CardWindowImageTexture):
                    dpg.set_value(CardWindowImageTexture, data)
                    dpg.set_value(CardWindowImage, fileName)
                else:
                    dpg.add_dynamic_texture(id=CardWindowImageTexture, width=w, height=h, default_value=data)
                    dpg.add_image(texture_id=CardWindowImageTexture, id=CardWindowImage, parent=CardWindow, user_data=fileName, width=w / 2 + 20, height=h / 2 + 50)

    with dpg.table(
        id=table,
        parent=parent,
        header_row=True,
        sortable=True,
        reorderable=True,
        resizable=True,
        no_host_extendX=True,
        policy=dpg.mvTable_SizingStretchProp,
        callback=SortHandler
        ):

        dpg.add_table_column(label=DataColumns.Quantity.name, default_sort=True, prefer_sort_descending=True)
        dpg.add_table_column(label=DataColumns.TotalSupply.name, default_sort=True, prefer_sort_descending=True)
        dpg.add_table_column(label=DataColumns.WithheldSupply.name, default_sort=True, prefer_sort_descending=True)
        dpg.add_table_column(label=DataColumns.UnreleasedPercentage.name, default_sort=True, prefer_sort_descending=True)
        dpg.add_table_column(label=DataColumns.ETH.name, default_sort=True, prefer_sort_descending=True)
        dpg.add_table_column(label=DataColumns.USD.name, default_sort=True, prefer_sort_descending=True)
        dpg.add_table_column(label=DataColumns.Name.name, default_sort=True, prefer_sort_ascending=True)
        dpg.add_table_column(label=DataColumns.Properties.name, no_sort=True)

    for row in TableData:
        tokenId = row[DataColumns.TokenId.name]
        imageFileName = f"{contractAddress}.{tokenId}.f.png"
        thumbFileName = f"{contractAddress}.{tokenId}.t.png"

        record = [
            row[DataColumns.Quantity.name],
            row[DataColumns.TotalSupply.name],
            row[DataColumns.WithheldSupply.name],
            "{0:.2f}%".format(row[DataColumns.UnreleasedPercentage.name]),
            "ETH {0:,.4f}".format(row[DataColumns.ETH.name]),
            "${0:,.2f}".format(row[DataColumns.USD.name]),
            ]

        hoverData = {
            "URL": row[DataColumns.ImageUrl.name],
            "FileName": imageFileName,
            "ThumbName": thumbFileName,
            "Name": row[DataColumns.Name.name],
            "TokenId": row[DataColumns.TokenId.name]
            }

        for t in record:
            txt = dpg.add_text(default_value=t, parent=table)
            hoverData['EventSource'] = txt
            dpg.add_hover_handler(parent=txt, callback=HoverHandler, user_data=hoverData)
            dpg.add_table_next_column(parent=table)

        btn = dpg.add_button(
            label=row[DataColumns.Name.name],
            parent=table,
            user_data=row[DataColumns.Link.name],
            callback=lambda _,__,url=row[DataColumns.Link.name]: webbrowser.open(url)
            )
        tt = dpg.add_tooltip(parent=btn)
        dpg.add_text(f"TokenID: {tokenId}", parent=tt)
        dpg.add_text("\n".join(row[DataColumns.Properties.name].values()), parent=tt)

        hoverData['EventSource'] = btn
        dpg.add_hover_handler(parent=btn, callback=HoverHandler, user_data=hoverData)
        dpg.add_table_next_column(parent=table)

        dpg.add_text(", ".join(row[DataColumns.Properties.name].values()), parent=table)
        dpg.add_table_next_column(parent=table)

    TableDataLock.release()
    assetsTableLock.release()

class SortDirection():
    @staticmethod
    def Descending(): return True
    @staticmethod
    def Ascending(): return False


AssetsTable = dpg.generate_uuid()
AssetValueInEth = dpg.generate_uuid()
AssetValueInFiat = dpg.generate_uuid()
CardWindow = dpg.generate_uuid()
CardWindowImage = dpg.generate_uuid()
CardWindowImageTexture = dpg.generate_uuid()
ContractAddressText = dpg.generate_uuid()
EthPriceText = dpg.generate_uuid()
LastUpdateText = dpg.generate_uuid()
MainWindow = dpg.generate_uuid()
MintingAddressText = dpg.generate_uuid()
ProgressBar = dpg.generate_uuid()
SetsWindow = dpg.generate_uuid()
StatusBarText = dpg.generate_uuid()
TableSortPreference = (DataColumns.ETH.name, SortDirection.Descending())
ThumbnailImage = dpg.generate_uuid()
ThumbnailTexture = dpg.generate_uuid()
ThumbnailTooltip = dpg.generate_uuid()
WalletAddressText = dpg.generate_uuid()

