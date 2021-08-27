from config import BaseConfig
import dearpygui.dearpygui as dpg
import webbrowser

class AppWindow:
    CardWindow = dpg.generate_uuid()
    CardWindowImage = dpg.generate_uuid()
    CardWindowImageTexture = dpg.generate_uuid()
    ProgressBar = dpg.generate_uuid()
    StatusBarText = dpg.generate_uuid()
    ViewMenu = dpg.generate_uuid()

    def __init__(self, label:str, height:int, width:int, baseConfig:BaseConfig):
        self.window = dpg.generate_uuid()
        self.baseConfig = baseConfig

        with dpg.window(label=label, width=width, height=height, id=self.window):
            with dpg.menu_bar():
                with dpg.menu(id=AppWindow.ViewMenu, label="View"):
                    dpg.add_menu_item(label="Card Viewer", callback=lambda: dpg.configure_item(AppWindow.CardWindow, show=True))
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
                    dpg.add_button(label="Send ETH or NFTs", callback=lambda: webbrowser.open(f"https://etherscan.io/address/{self.baseConfig.Get('DonationAddress')}"))
                    dpg.add_same_line(spacing=20)
                    dpg.add_button(label="Send $ via PayPal", callback=lambda: webbrowser.open(f"https://paypal.me/jeremya"))
                    dpg.add_same_line(spacing=20)
                    dpg.add_button(label="Sponsor me on GitHub!", callback=lambda: webbrowser.open("https://github.com/sponsors/JERisBRISK"))
                    dpg.add_text()
                dpg.add_progress_bar(id=AppWindow.ProgressBar, label="ProgressBar", overlay="status", default_value = 0.0, width=200)
                dpg.add_text("", id=AppWindow.StatusBarText)

            with dpg.window(label="Card Viewer", width=600, height=900, id=AppWindow.CardWindow, show=False):
                def CardWindowResize(sender, app_data, user_data):
                    # ensure the Image Exists before trying to resize it.
                    try:
                        dpg.get_item_info(AppWindow.CardWindowImage)
                    except:
                        return

                    w,h = app_data
                    imgW = dpg.get_item_width(AppWindow.CardWindowImage)
                    imgH = dpg.get_item_height(AppWindow.CardWindowImage)
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

                    dpg.configure_item(AppWindow.CardWindowImage, width=newW, height=newH)
                dpg.add_resize_handler(AppWindow.CardWindow, callback=CardWindowResize)