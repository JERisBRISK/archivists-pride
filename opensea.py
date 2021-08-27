from cards import Cards
from config import BaseConfig
from dumper import dumps
from ethereum import Ethereum
from json import loads
from math import ceil
from random import random
from requests import request
from threading import Lock
from time import sleep

class OpenSea:
    NullAddress = "0x0000000000000000000000000000000000000000"
    ApiLock = Lock()

    @staticmethod
    def RandomSleep(minimum:float=0.1, maximum:float=10.0):
        sleep(max(minimum, random() * maximum))

    @staticmethod
    def GetResponse(url, headers, query, logInfoCallback, logErrorCallback, retries = 5):
        retVal = {}

        # retries exhausted and no good response was had
        if retries < 0:
            return retVal

        try:
            OpenSea.ApiLock.acquire()
            logInfoCallback(f"Requesting from {url}\n{dumps(query)}")
            response = request("GET", url, headers=headers, params=query)
            if response:
                # response is OK
                if response.status_code == 200:
                    json = loads(response.text)
                    return json
                # header is probably too large
                elif response.status_code == 400:
                    logErrorCallback(f"OpenSea returned [{response.status_code}] {response.text}")
                    return loads(response.text)
                # things need to slow down
                elif response.status_code == 429:
                    logErrorCallback(f"OpenSea returned [{response.status_code}] {response.text}")
                    OpenSea.RandomSleep()
                    # try again
                    return OpenSea.GetResponse(url, headers, query, logInfoCallback, logErrorCallback, retries - 1)
        except Exception as e:
            logErrorCallback(str(e))
        finally:
            OpenSea.ApiLock.release()

    @staticmethod
    def GetAssets(walletAddress, contractAddress, logInfoCallback, logErrorCallback, tokens:list[int] = [], limit:int = 50):
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
        chunks = max(1, int(ceil(len(tokens) / limit)))

        for s in range(0, chunks):
            logInfoCallback(f"GetAssets: Requesting chunk {s}/{chunks}")
            requestedAssetCount = 0

            if len(tokens) > 0:
                lowerBound = s * limit
                upperBound = (s + 1) * limit
                query['token_ids'] = tokens[lowerBound : upperBound]
                requestedAssetCount = len(query['token_ids'])
                logInfoCallback(f"Requesting {requestedAssetCount} assets from OpenSea.")

            thereMayBeMore = True
            offset = 0

            while thereMayBeMore:
                data = OpenSea.GetResponse(url=url, headers=headers, query=query, logInfoCallback=logInfoCallback, logErrorCallback=logErrorCallback)
                if data and 'assets' in data:
                    responseAssets = data['assets']
                    count = len(responseAssets)

                    if count == limit and not count == requestedAssetCount:
                        thereMayBeMore = True
                        offset += count
                        query['offset'] = offset
                    else:
                        thereMayBeMore = False
                        assets.extend(responseAssets)
                        logInfoCallback(f"Received {len(assets)}/{requestedAssetCount} assets from OpenSea.")
                else:
                    thereMayBeMore = False

        return assets

    @staticmethod
    def GetTokens(walletAddress, contractAddress, logInfoCallback, logErrorCallback):
        assets = OpenSea.GetAssets(walletAddress, contractAddress, logInfoCallback, logErrorCallback)
        return [str(row['token_id']) for row in assets]

    @staticmethod
    def GetLastSalePrice(asset):
        if asset['last_sale']:
            qty = int(asset['last_sale']['quantity'])
            decimals = int(asset['last_sale']['payment_token']['decimals'])
            price = float(asset['last_sale']['total_price']) / qty / (10**decimals)
            currency = asset['last_sale']['payment_token']['symbol']

            # DAI is usually locked to $1, just like USDC
            if "USDC" == currency or "DAI" == currency:
                price = price / Ethereum.GetEthInFiat(1.0)
        else:
            price = 0

        return price

    @staticmethod
    def GetListings(walletAddress, contractAddress, logInfoCallback, logErrorCallback, retries=5):
            if retries < 0:
                return []

            url = "https://api.opensea.io/wyvern/v1/orders"
            headers = {"Accept": "application/json"}
            listings = []
            tokens = []
            ethPrice = Ethereum.GetEthInFiat(1.0)

            tokens = OpenSea.GetTokens(walletAddress, contractAddress, logInfoCallback, logErrorCallback)
            # wallet has no tokens, therefore has nothing to offer
            if not tokens:
                logInfoCallback(f"Wallet {walletAddress} does not appear to hold any tokens.")
                return

            query = {
                "asset_contract_address":contractAddress,
                "maker":walletAddress,
                "taker":OpenSea.NullAddress,
                "include_bundled":"true",
                "include_invalid":"false",
                "side":"1",
                "sale_kind":"0",
                "offset":"0",
                "limit":"50",
                "order_by":"eth_price",
                "order_direction":"asc",
                "token_ids":tokens,
            }

            orders = OpenSea.GetResponse(url=url, headers=headers, query=query, logInfoCallback=logInfoCallback, logErrorCallback=logErrorCallback)

            if 'orders' in orders:
                for order in orders['orders']:
                    tokenId = int(order['metadata']['asset']['id'])
                    qty = int(order['metadata']['asset']['quantity'])
                    decimals = int(order['payment_token_contract']['decimals'])
                    currency = order['payment_token_contract']['symbol']
                    price = float(order['current_price']) / qty / (10**decimals)

                    # DAI is usually locked to $1, just like USDC
                    if "USDC" == currency or "DAI" == currency:
                        price = price / ethPrice
                        
                    listing = {
                        "TokenId" : tokenId,
                        "Quantity" : qty,
                        "ETH" : price,
                        "USD" : price * ethPrice,
                        "TotalETH" : price * qty,
                        "TotalUSD" : price * qty * ethPrice,
                        "Name" : order['asset']['name'],
                        "Link" : order['asset']['permalink'],
                    }

                    listings.append(listing)
            else:
                listings = OpenSea.GetMyListings(
                    contractAddress=contractAddress,
                    logInfoCallback=logInfoCallback,
                    logErrorCallback=logErrorCallback,
                    walletAddress=walletAddress,
                    retries=retries - 1)

            return listings

    @staticmethod
    def GetPrices(order):
        ethInFiat = Ethereum.GetEthInFiat(1.0)
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

    @staticmethod
    def GetTotalTokenSupply(baseConfig:BaseConfig, cards:Cards, tokenId, logInfoCallback, logErrorCallback, retries=5):
        if retries < 0:
            return -1

        root = "cards"
        token = str(tokenId)
        supplyKey = "supply"

        # value is cached, return it
        if cards.Has(token):
            if supplyKey in cards.Get(token):
                return cards.Get(token)[supplyKey]

        url = "https://api.opensea.io/api/v1/events"
        headers = {"Accept": "application/json"}

        query = {
            # by using the null address, we scope into the initial mint of tokens
            "account_address":OpenSea.NullAddress,
            "asset_contract_address":baseConfig.Get('ContractAddress'),
            "token_id":f"{tokenId}",
            "event_type":"transfer",
            "only_opensea":"false",
            "offset":"0",
            "limit":"1",
        }

        response = OpenSea.GetResponse(
            url=url,
            headers=headers,
            query=query,
            logInfoCallback=logInfoCallback,
            logErrorCallback=logErrorCallback)

        supply = {}
        if response and 'asset_events' in response:
            # response was empty
            if not len(response['asset_events']):
                supply = OpenSea.GetTotalTokenSupply(
                    baseConfig=baseConfig,
                    tokenId=tokenId,
                    logInfoCallback=logInfoCallback,
                    logErrorCallback=logErrorCallback,
                    retries=retries - 1)
            else:
                supply = {
                    "Minted" : int(response['asset_events'][0]['quantity']),
                }
        else:
            logErrorCallback(f"GetTotalTokenSupply retry {retries} returned {response.status_code} for query:")
            logErrorCallback(dumps(query))

            sleep(random.random() * 30)
            supply = OpenSea.GetTotalTokenSupply(baseConfig=baseConfig, tokenId=tokenId, retries=retries - 1)

        # cache the answer if it's valid
        if 'Minted' in supply and supply['Minted'] > 0:
            mintingAddress = Ethereum.w3.toChecksumAddress(baseConfig.Get('MintingAddress'))
            record = {
                "Minted" : supply['Minted'],
                "Withheld" : Ethereum.GetTokenQuantity(mintingAddress, baseConfig.Get('ContractAddress'), tokenId)
            }

            cards.Get(token)[supplyKey] = record
            
            # save the cache
            cards.Save()

        return record