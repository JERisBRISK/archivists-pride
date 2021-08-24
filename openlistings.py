import dearpygui.dearpygui as dpg
import requests
from seahawk import *
from pushcontainer import push_container

# import dearpygui.logger as dpg_logger

class OpenListings:
    NullAddress = "0x0000000000000000000000000000000000000000"

    def __init__(self, width, height):
        self.window = dpg.generate_uuid()
        self.totalETHText = dpg.generate_uuid()
        self.totalUSDText = dpg.generate_uuid()
        self.table = dpg.generate_uuid()

        with dpg.window(
            id=self.window,
            label="Open Listings",
            width=width,
            height=height,
            show=False):

            dpg.add_same_line(spacing=4)
            dpg.add_text(default_value="Total ETH:")
            dpg.add_same_line(spacing=4)
            dpg.add_text(id=self.totalETHText)
            dpg.add_same_line(spacing=4)
            dpg.add_text(default_value="Total USD:")
            dpg.add_same_line(spacing=4)
            dpg.add_text(id=self.totalUSDText)
            self.InitTable()

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
            dpg.add_table_column(label="Quantity", no_sort=True, default_sort=True, prefer_sort_descending=True)
            dpg.add_table_column(label="ETH", no_sort=True, default_sort=True, prefer_sort_descending=True)
            dpg.add_table_column(label="Total ETH", no_sort=True, default_sort=True, prefer_sort_descending=True)
            dpg.add_table_column(label="USD", no_sort=True, default_sort=True, prefer_sort_descending=True)
            dpg.add_table_column(label="Total USD", no_sort=True, default_sort=True, prefer_sort_descending=True)
            dpg.add_table_column(label="Name", no_sort=True, default_sort=True, prefer_sort_ascending=True)
        return table

    def Show(self):
        dpg.configure_item(self.window, show=True)
    
    def Hide(self):
        dpg.configure_item(self.window, show=False)

    def GetMyListings(walletAddress, contractAddress, retries=5):
        if retries < 0:
            return []

        url = "https://api.opensea.io/wyvern/v1/orders"
        headers = {"Accept": "application/json"}
        listings = []
        tokens = []
        ethPrice = GetEthInFiat(1.0)

        tokens = GetTokens(walletAddress, contractAddress)
        # wallet has no tokens, therefore has nothing to offer
        if not tokens:
            logger.log(f"Wallet {walletAddress} does not appear to hold any tokens.")
            return

        query = {
            "asset_contract_address":contractAddress,
            "maker":walletAddress,
            "taker":OpenListings.NullAddress,
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

        response = requests.request("GET", url, headers=headers, params=query)

        if response.status_code == 200:
            orders = json.loads(response.text)['orders']

            for order in orders:
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
            logger.log_error(f"Query returned status {response.status_code}")
            time.sleep(random.randint(1,10))
            listings = OpenListings.GetMyListings(contractAddress=contractAddress, walletAddress=walletAddress, retries=retries - 1)

        return listings

    def Update(self, walletAddress, contractAddress):
        totalETH = 0.0
        totalUSD = 0.0

        if dpg.does_item_exist(self.table):
            dpg.delete_item(self.table)

        self.table = self.InitTable()
        listings = OpenListings.GetMyListings(walletAddress, contractAddress)
        for listing in listings:
            totalETH += listing['TotalETH']
            totalUSD += listing['TotalUSD']

            with push_container(self.table):
                dpg.add_text(str(listing['Quantity']))
                dpg.add_table_next_column()
                dpg.add_text("{0:,.4f}".format(listing['ETH']))
                dpg.add_table_next_column()
                dpg.add_text("{0:,.4f}".format(listing['TotalETH']))
                dpg.add_table_next_column()
                dpg.add_text("${0:,.2f}".format(listing['USD']))
                dpg.add_table_next_column()
                dpg.add_text("${0:,.2f}".format(listing['TotalUSD']))
                dpg.add_table_next_column()
                dpg.add_button(label=listing['Name'], user_data=listing['Link'], callback=lambda _,__,url: webbrowser.open_new_tab(url))
                dpg.add_table_next_column()

        dpg.set_value(self.totalETHText, "{0:,.4f}".format(totalETH))
        dpg.set_value(self.totalUSDText, "${0:,.2f}".format(totalUSD))