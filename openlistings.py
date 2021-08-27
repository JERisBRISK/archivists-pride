from config import BaseConfig, LocalConfig
from datetime import datetime
from opensea import OpenSea
from pushcontainer import push_container
from singleton import Singleton
from threading import Thread
from time import time
from webbrowser import open_new_tab
import dearpygui.dearpygui as dpg

class OpenListings(metaclass=Singleton):
    NullAddress = "0x0000000000000000000000000000000000000000"

    def __init__(self, width, height, baseConfig:BaseConfig, localConfig:LocalConfig, logInfoCallback, logErrorCallback):
        # options
        self.baseConfig = baseConfig
        self.localConfig = localConfig
        self.logInfoCallback = logInfoCallback
        self.logErrorCallback = logErrorCallback

        # data
        self.lastUpdateTime = 0

        # ui elements
        self.lastUpdateText = dpg.generate_uuid()
        self.table = dpg.generate_uuid()
        self.totalETHText = dpg.generate_uuid()
        self.totalUSDText = dpg.generate_uuid()
        self.window = dpg.generate_uuid()

        with dpg.window(
            id=self.window,
            label="Open Listings",
            width=width,
            height=height,
            show=False):

            dpg.add_button(label="Refresh", callback=self.Update)

            dpg.add_text(default_value="Total ETH:")
            dpg.add_same_line(spacing=4)
            dpg.add_text(id=self.totalETHText)
            dpg.add_same_line(spacing=10)
            dpg.add_text(default_value="Total USD:")
            dpg.add_same_line(spacing=4)
            dpg.add_text(id=self.totalUSDText)
            dpg.add_same_line(spacing=10)
            dpg.add_text("Last Refresh:")
            dpg.add_same_line(spacing=4)
            dpg.add_text(id=self.lastUpdateText)

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
        if (time() - self.lastUpdateTime >= 60 * 5):
            Thread(target=self.Update, daemon=True).start()

    def Update(self):
        self.lastUpdateTime = time()
        totalETH = 0.0
        totalUSD = 0.0

        if dpg.does_item_exist(self.table):
            dpg.delete_item(self.table)

        self.table = self.InitTable()
        listings = OpenSea.GetListings(
            walletAddress=self.localConfig.Get('WalletAddress'),
            contractAddress=self.baseConfig.Get('ContractAddress'),
            logInfoCallback=self.logInfoCallback,
            logErrorCallback=self.logErrorCallback)

        if listings:
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
                    dpg.add_button(label=listing['Name'], user_data=listing['Link'], callback=lambda _,__,url: open_new_tab(url))
                    dpg.add_table_next_column()

        dpg.set_value(self.totalETHText, "{0:,.4f}".format(totalETH))
        dpg.set_value(self.totalUSDText, "${0:,.2f}".format(totalUSD))
        dpg.set_value(self.lastUpdateText, datetime.now().strftime("%c"))
