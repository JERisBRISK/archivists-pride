from logging import error
import dearpygui.dearpygui as dpg
import dumper
from threading import Thread
from globals_ import *
from openlistings import *
from seahawk import *
from sets import *
from alert import *

dumper.max_depth = 10

# Init UI
DonationAddress = "0x4042e6DDA6A74cb3A9462B4a34e0618Fd60844d2"
DefaultAddress = "0xcb58f6eab75e27bc9c5119d4e635a16bd68da301"
AppVersion = "1.0 alpha"
OpenListingsWindow = OpenListings(width=600, height=300)
SetsWindow = Sets(width=800, height=400)

def GetData():
    global CurrentEthPrice
    # save the current ETH to fiat price
    CurrentEthPrice = GetEthInFiat(1.0)

    try:
        walletAddress = w3.toChecksumAddress(dpg.get_value(WalletAddressText))
        contractAddress = w3.toChecksumAddress(dpg.get_value(ContractAddressText))
    except ValueError as ve:
        alert("Wallet Address Error", f"The address you provided wasn't in the right format.\n\nIt should look like:\n\n{DefaultAddress}")
        return

    Thread(target=OpenListingsWindow.Update, args=(walletAddress, contractAddress), daemon=True).start()
    Thread(target=SetsWindow.Update, args=(walletAddress, contractAddress), daemon=True).start()
    Thread(target=UpdateTableData, args=(walletAddress, contractAddress), daemon=False).start()
    Thread(target=UpdateAssetsTable, args=(MainWindow, walletAddress, contractAddress, AssetsTable), daemon=False).start()

with dpg.window(label="Wallet", width=1280, height=720, id=MainWindow):
    with dpg.menu_bar():
        with dpg.menu(label="View"):
            dpg.add_menu_item(label="Card Viewer", callback=lambda: dpg.configure_item(CardWindow, show=True))
            dpg.add_menu_item(label="Listings", callback=lambda: OpenListingsWindow.Show())
            dpg.add_menu_item(label="Sets", callback=lambda: SetsWindow.Show())
            dpg.add_menu_item(label="Log", callback=lambda: dpg.configure_item(logger.window_id, show=True))
        donate = dpg.add_button(label="Donate")
        with dpg.popup(parent=donate, mousebutton=dpg.mvMouseButton_Left, modal=True):
            dpg.add_text("Writing this has been a labor of blood, sweat, and tears. It's my joy to bring it to you.")
            dpg.add_text("    Thanks in advance for your generous donations -- they help keep the dream alive!")
            dpg.add_text("                            -Jeremy Anderson aka JERisBRISK")
            dpg.add_text()
            dpg.add_text("                                    Ways to give:")
            dpg.add_text()
            dpg.add_text()
            dpg.add_same_line(spacing=120)
            dpg.add_button(label="Send ETH or NFTs", callback=lambda: webbrowser.open(f"https://etherscan.io/address/{DonationAddress}"))
            dpg.add_same_line(spacing=20)
            dpg.add_button(label="Send $ via PayPal", callback=lambda: webbrowser.open(f"https://paypal.me/jeremya"))
            dpg.add_same_line(spacing=20)
            dpg.add_button(label="Sponsor me on GitHub*", callback=lambda: webbrowser.open("https://github.com/sponsors/JERisBRISK"))
            dpg.add_text()
            dpg.add_text("* I've applied for GitHub Sponsorship, but it hasn't been approved yet.")
            dpg.add_text("  If it's not obvious how to sponsor me, please choose another route!")
        dpg.add_progress_bar(id=ProgressBar, label="ProgressBar", overlay="status", default_value = 0.0, width=200)
        dpg.add_text("", id=StatusBarText)

    dpg.add_input_text(id=ContractAddressText, label="Contract Address", default_value="0x76be3b62873462d2142405439777e971754e8e77", show=False)
    dpg.add_input_text(id=MintingAddressText, label="Minting Address", default_value="0x74db0bbfde94aa80a135c5f8b60c0ca3d17332f2", show=False)
    dpg.add_input_text(id=WalletAddressText, label="Wallet Address", default_value=DefaultAddress, width=400)
    watt = dpg.add_tooltip(parent=WalletAddressText)
    dpg.add_text(default_value="Put the address of a wallet you want to view here and click 'Refresh'", parent=watt)

    dpg.add_same_line(spacing=2)
    dpg.add_button(label="Refresh", callback=GetData)

    dpg.add_text("Asset Value (ETH):")
    dpg.add_same_line(spacing=4)
    dpg.add_text(id=AssetValueInEth)

    dpg.add_same_line(spacing=10)

    dpg.add_text("Ethereum Value (USD/ETH):")
    dpg.add_same_line(spacing=4)
    dpg.add_text(id=EthPriceText)

    dpg.add_same_line(spacing=10)

    dpg.add_text("Asset Value (USD):")
    dpg.add_same_line(spacing=4)
    dpg.add_text(id=AssetValueInFiat)

    dpg.add_same_line(spacing=10)
    dpg.add_text("Last Refresh:")
    dpg.add_same_line(spacing=4)
    dpg.add_text(id=LastUpdateText)


    with dpg.window(label="Viewer", width=600, height=900, id=CardWindow, show=False):
        def CardWindowResize(sender, app_data, user_data):
            # ensure the Image Exists before trying to resize it.
            try:
                dpg.get_item_info(CardWindowImage)
            except:
                return

            w,h = app_data
            imgW = dpg.get_item_width(CardWindowImage)
            imgH = dpg.get_item_height(CardWindowImage)
            imgRatio = imgW / imgH

            padding = 20
            w = w - padding
            h = h - padding - 30

            # requested width is greater than height
            # set the new width and height to honor the height and the ratio
            if w > h:
                newW = h * imgRatio
                newH = h
            else:
                newW = w 
                newH = w / imgRatio

            dpg.configure_item(CardWindowImage, width=newW, height=newH)

        dpg.add_resize_handler(CardWindow, callback=CardWindowResize)

    # add a plot
    #with dpg.plot(label="Scatter Plot", height=dpg.get_viewport_height() - 20, width=dpg.get_viewport_width() - 20)

dpg.set_primary_window(MainWindow, True)

# hide the logger by default
dpg.configure_item(logger.window_id, show=False)

# https://github.com/hoffstadt/DearPyGui/wiki/Viewport#manual-viewport
vp = dpg.create_viewport(title=f"Archivist\'s Pride {AppVersion} by JERisBRISK", width=1280, height=1024) # create viewport takes in config options too!
# must be called before showing viewport
dpg.set_viewport_small_icon('parallel.ico')
dpg.set_viewport_large_icon('parallel.ico')
dpg.setup_dearpygui(viewport=vp)
dpg.setup_registries()
dpg.show_viewport(vp)

# kick things off with a refresh
cancelUpdate = SetInterval(60, GetData)

dpg.start_dearpygui()

