from time import sleep
from alert import alert
from appwindow import AppWindow
from cache import Cache
from cachemanager import CacheManager
from cards import Cards
from config import BaseConfig, LocalConfig
from datetime import datetime
from downloader import Downloader
from enum import Enum
from ethereum import Ethereum
from opensea import OpenSea
from os import stat
from pushcontainer import push_container
from singleton import Singleton
from singleton import Singleton
from sortdirection import SortDirection
from threading import Lock, Thread, Event
import dearpygui.dearpygui as dpg
import webbrowser

class DataColumns(Enum):
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
    
class Wallet(metaclass=Singleton):
    MenuBar = dpg.generate_uuid()
    ProgressBar = dpg.generate_uuid()
    TableData = []
    TableDataLock = Lock()
    AssetsTableLock = Lock()
    TableSortPreference = (DataColumns.ETH.name, SortDirection.Descending())

    def __init__(self, width, height, mainWindow:AppWindow, baseConfig:BaseConfig, localConfig:LocalConfig, logInfoCallback, logErrorCallback):
        # options
        self.mainWindow = mainWindow
        self.baseConfig = baseConfig
        self.localConfig = localConfig
        self.logInfoCallback = logInfoCallback
        self.logErrorCallback = logErrorCallback

        # data
        self.lastUpdateTime = 0
        self.dataUpdated = Event()
        self.imageLock = Lock()

        # UI elements
        self.addressText = dpg.generate_uuid()
        self.ethPriceText = dpg.generate_uuid()
        self.lastUpdateText = dpg.generate_uuid()
        self.table = dpg.generate_uuid()
        self.totalETHText = dpg.generate_uuid()
        self.totalUSDText = dpg.generate_uuid()
        self.window = dpg.generate_uuid()

        # dependencies
        self.cache = CacheManager(baseConfig, localConfig)

        self.cards = Cards(
            logInfoCallback=logInfoCallback,
            logErrorCallback=logErrorCallback)

        self.downloader = Downloader(
            baseConfig=baseConfig,
            localConfig=localConfig,
            logInfoCallback=logInfoCallback,
            logErrorCallback=logErrorCallback)

        with dpg.window(
            id=self.window,
            label="Wallet",
            width=width,
            height=height,
            show=True):

            dpg.add_menu_bar(id=Wallet.MenuBar, parent=self.window)
            dpg.add_progress_bar(parent=Wallet.MenuBar, id=Wallet.ProgressBar, label="ProgressBar", overlay="status", default_value = 0.0)

            dpg.add_input_text(
                id=self.addressText,
                label="Wallet Address",
                default_value=localConfig.Get('WalletAddress'),
                width=400)

            watt = dpg.add_tooltip(parent=self.addressText)
            dpg.add_text(default_value="Put the address of a wallet you want to view here and click 'Refresh'", parent=watt)
            dpg.add_same_line(spacing=2)
            dpg.add_button(label="Refresh", callback=self.Update)
            dpg.add_text("Asset Value (ETH):")
            dpg.add_same_line(spacing=4)
            dpg.add_text(id=self.totalETHText)
            dpg.add_same_line(spacing=10)
            dpg.add_text("Ethereum Value (USD/ETH):")
            dpg.add_same_line(spacing=4)
            dpg.add_text(id=self.ethPriceText)
            dpg.add_same_line(spacing=10)
            dpg.add_text("Asset Value (USD):")
            dpg.add_same_line(spacing=4)
            dpg.add_text(id=self.totalUSDText)
            dpg.add_same_line(spacing=10)
            dpg.add_text("Last Refresh:")
            dpg.add_same_line(spacing=4)
            dpg.add_text(id=self.lastUpdateText)
            self.InitTable()

        # kick things off with a refresh
        #self.cancelUpdate = SetInterval(60*10, self.Update)

    def InitTable(self):
        t = dpg.add_table(
            id=self.table,
            parent=self.window,
            header_row=True,
            sortable=True,
            reorderable=True,
            resizable=True,
            no_host_extendX=True,
            policy=dpg.mvTable_SizingStretchProp,
            callback=self.SortHandler
            )

        with push_container(t) as table:
            dpg.add_table_column(label=DataColumns.Quantity.name, default_sort=True, prefer_sort_descending=True)
            dpg.add_table_column(label=DataColumns.TotalSupply.name, default_sort=True, prefer_sort_descending=True)
            dpg.add_table_column(label=DataColumns.WithheldSupply.name, default_sort=True, prefer_sort_descending=True)
            dpg.add_table_column(label=DataColumns.UnreleasedPercentage.name, default_sort=True, prefer_sort_descending=True)
            dpg.add_table_column(label=DataColumns.ETH.name, default_sort=True, prefer_sort_descending=True)
            dpg.add_table_column(label=DataColumns.USD.name, default_sort=True, prefer_sort_descending=True)
            dpg.add_table_column(label=DataColumns.Name.name, default_sort=True, prefer_sort_ascending=True)
            dpg.add_table_column(label=DataColumns.Properties.name, no_sort=True)
        return table

    def Update(self):
        try:
            # read the wallet address provided by the user
            walletAddress = Ethereum.w3.toChecksumAddress(dpg.get_value(self.addressText))
            self.localConfig.Set('WalletAddress', walletAddress)
            self.localConfig.Save()
            contractAddress = Ethereum.w3.toChecksumAddress(self.baseConfig.Get('ContractAddress'))
        except ValueError:
            alert("Wallet Address Error", f"The address you provided wasn't in the right format.\n\nIt should look like:\n\n{self.baseConfig.Get('DonationAddress')}")
            return
        except Exception as e:
            alert("Wallet Address Error", f"Something went wrong: {str(e)}")
            return

        self.dataUpdated.clear()
        Thread(target=self.UpdateTableData, args=(walletAddress, contractAddress), daemon=True).start()
        Thread(target=self.UpdateAssetsTable, daemon=True).start()

    def Show(self):
        dpg.configure_item(self.window, show=True)

    def HoverHandler(self, sender, app_data, user_data):
        fileName = user_data['FileName']
        print(f"0 HoverHandler for {fileName}")

        if self.imageLock.locked():
            print("  0.1 Image window is locked, so return.")
            return
        
        with self.imageLock:
            # the CardWindowImage control is registered with dpg
            if dpg.does_item_exist(self.mainWindow.CardWindowImage):
                # the current CardWindowImage is the same as the image we're trying to display
                if dpg.get_item_user_data(self.mainWindow.CardWindowImage) == fileName:
                    return

            # the texture is already loaded, so just switch to it
            if self.cache.IsCached(Cache.Textures, fileName):
                dpg.set_item_user_data(self.mainWindow.CardWindowImage, fileName)
                w, h, data = self.cache.textures[fileName]
                dpg.set_value(self.mainWindow.CardWindowImageTexture, data)
                return

            # the texture isn't in the file cache, download it
            if not self.cache.IsCached(Cache.Images, fileName):
                self.downloader.Enqueue(url=user_data['URL'], fileName=fileName)
                return

            # the texture is in the file cache, so load it
            if self.cache.IsCached(Cache.Images, fileName):
                # load the texture
                fullName = self.cache.GetCachePath(Cache.Images, fileName)
                self.logInfoCallback(f"Loading {fileName}")
                loadedImage = dpg.load_image(fullName)

                if loadedImage:
                    self.logInfoCallback(f"Loaded {fileName}. Installing texture...")
                    w, h, _, data = loadedImage
                    # cache it
                    self.cache.textures[fileName] = (w, h, data)
                    # set it
                    with dpg.texture_registry():
                        if dpg.does_item_exist(self.mainWindow.CardWindowImageTexture):
                            dpg.set_value(self.mainWindow.CardWindowImageTexture, data)
                        else:
                            dpg.add_dynamic_texture(
                                id=self.mainWindow.CardWindowImageTexture,
                                width=w,
                                height=h,
                                default_value=data)

                        if dpg.does_item_exist(self.mainWindow.CardWindowImage):
                            dpg.set_value(self.mainWindow.CardWindowImage, fileName)
                        else:
                            dpg.add_image(
                                texture_id=self.mainWindow.CardWindowImageTexture,
                                id=self.mainWindow.CardWindowImage,
                                parent=self.mainWindow.CardWindow,
                                user_data=fileName,
                                width=w / 2 + 20,
                                height=h / 2 + 50)
                else:
                    self.logErrorCallback(f"Couldn't load {fileName}.")
                    if stat(fileName).st_size == 0:
                        self.logErrorCallback(f"{fileName} is 0 bytes long. Consider deleting it.")

    def Show(self):
        dpg.configure_item(self.window, show=True)

    def SortHandler(self, sender, app_data, user_data):
        column, direction = app_data[0]
        columnName = dpg.get_item_configuration(column)['label']
        self.dataUpdated.clear()
        self.SortTableData(columnName, direction != 1)
        self.UpdateAssetsTable()

    def UpdateAssetsTable(self):
        # wait for the update signal
        self.dataUpdated.wait()

        with Wallet.AssetsTableLock:
            walletAddress = self.localConfig.Get('WalletAddress')
            contractAddress = self.baseConfig.Get('ContractAddress')

            if not Wallet.TableData:
                self.UpdateTableData(walletAddress, contractAddress)

            with Wallet.TableDataLock:
                if dpg.does_item_exist(self.table):
                    dpg.delete_item(self.table)

                self.InitTable()

                for row in Wallet.TableData:
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
                        txt = dpg.add_text(default_value=t, parent=self.table)
                        hoverData['EventSource'] = txt
                        dpg.add_hover_handler(parent=txt, callback=self.HoverHandler, user_data=hoverData)
                        dpg.add_table_next_column(parent=self.table)

                    btn = dpg.add_button(
                        label=row[DataColumns.Name.name],
                        parent=self.table,
                        user_data=row[DataColumns.Link.name],
                        callback=lambda _,__,url=row[DataColumns.Link.name]: webbrowser.open(url)
                        )
                    tt = dpg.add_tooltip(parent=btn)
                    dpg.add_text(f"TokenID: {tokenId}", parent=tt)
                    dpg.add_text("\n".join(row[DataColumns.Properties.name].values()), parent=tt)

                    hoverData['EventSource'] = btn
                    dpg.add_hover_handler(parent=btn, callback=self.HoverHandler, user_data=hoverData)
                    dpg.add_table_next_column(parent=self.table)

                    dpg.add_text(", ".join(row[DataColumns.Properties.name].values()), parent=self.table)
                    dpg.add_table_next_column(parent=self.table)

    def SortTableData(self, column, descending):
        with Wallet.TableDataLock:
            self.dataUpdated.clear()
            Wallet.TableSortPreference = (column, descending)
            Wallet.TableData = sorted(Wallet.TableData, key=lambda r: r[column], reverse=descending)
            self.dataUpdated.set()

    def UpdateTableData(self, walletAddress, contractAddress):
        ethPrice = Ethereum.GetEthInFiat(1.0)
        netWorthInEth = 0.0
        netWorthInFiat = 0.0
        i = 0.0

        with Wallet.TableDataLock:
            self.dataUpdated.clear()
            Wallet.TableData.clear()

            assets = OpenSea.GetAssets(
                walletAddress,
                contractAddress,
                logInfoCallback=self.logInfoCallback,
                logErrorCallback=self.logErrorCallback)

            numAssets = float(len(assets))

            for asset in assets:
                i += 1.0
                name = asset['name']
                link = asset['permalink']
                tokenId = int(asset['token_id'])
                imageUrl = asset['image_original_url']
                thumbUrl = asset['image_thumbnail_url']
                properties = {t['trait_type']:t['value'] for t in asset['traits']}

                supply = OpenSea.GetTotalTokenSupply(
                    baseConfig=self.baseConfig,
                    cards=self.cards,
                    tokenId=tokenId,
                    logInfoCallback=self.logInfoCallback,
                    logErrorCallback=self.logErrorCallback)

                ownedQuantity = Ethereum.GetTokenQuantity(walletAddress, contractAddress, tokenId)
                price = OpenSea.GetLastSalePrice(asset)

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

                Wallet.TableData.append(row)

                try:
                    percentage = i / numAssets
                    dpg.set_value(Wallet.ProgressBar, percentage)
                    dpg.configure_item(Wallet.ProgressBar, overlay="Loaded {0:,} assets.".format(int(i), int(numAssets)))
                except Exception as e:
                    self.logErrorCallback(str(e))

            dpg.set_value(self.ethPriceText, "${0:,.2f}".format(ethPrice))
            dpg.set_value(self.totalETHText, "{0:,.4f}".format(netWorthInEth))
            dpg.set_value(self.totalUSDText, "${0:,.2f}".format(netWorthInFiat))
            dpg.set_value(self.lastUpdateText, datetime.now().strftime("%c"))

        column, descending = Wallet.TableSortPreference

        # we don't need to set the self.dataCompleted event because SortTableData does it
        self.SortTableData(column, descending)

    