from alert import *
from cards import Cards
from config import BaseConfig, LocalConfig
from dearpygui.logger import mvLogger
from openlistings import OpenListings
from os import mkdir
from os.path import abspath, isdir, expandvars
from sets import Sets
from wallet import Wallet
from appwindow import AppWindow
import dearpygui.dearpygui as dpg
import dumper

# Init logging
dumper.max_depth = 10
logger = mvLogger()
AppVersion = "1.0 alpha"
AppName = "Archivist's Pride"

# Load configuration data
baseConfig = BaseConfig(logInfoCallback=logger.log, logErrorCallback=logger.log_error)
localConfig = LocalConfig(logInfoCallback=logger.log, logErrorCallback=logger.log_error)
cards = Cards(logInfoCallback=logger.log, logErrorCallback=logger.log_error)

AppDataRoot = expandvars(localConfig.Get('AppDataRoot', abspath(".\_Data")))
CacheRoot = localConfig.Set('CacheRoot', f"{AppDataRoot}\Cache")
ImageCacheRoot = localConfig.Set('ImageCacheRoot', f"{localConfig.Get('CacheRoot')}\Images")

# Ensure the roots exist
if not isdir(AppDataRoot):
    mkdir(AppDataRoot)

if not isdir(CacheRoot):
    mkdir(CacheRoot)

if not isdir(ImageCacheRoot):
    mkdir(ImageCacheRoot)

# Init UI
MainWindow = AppWindow(
    width=1280,
    height=1024,
    baseConfig=baseConfig,
    label=AppName)

dpg.set_primary_window(MainWindow.window, True)

OpenListingsWindow = OpenListings(
    width=600,
    height=300,
    baseConfig=baseConfig,
    localConfig=localConfig,
    logInfoCallback=logger.log,
    logErrorCallback=logger.log_error)

WalletWindow = Wallet(
    width=1280,
    height=1024,
    mainWindow = MainWindow,
    baseConfig=baseConfig,
    localConfig=localConfig,
    logInfoCallback=logger.log,
    logErrorCallback=logger.log_error)

SetsWindow = Sets(
    width=800,
    height=400,
    cards=cards,
    walletAddress=localConfig.Get('WalletAddress'),
    contractAddress=baseConfig.Get('ContractAddress'),
    logInfoCallback=logger.log,
    logErrorCallback=logger.log_error)

dpg.add_menu_item(parent=MainWindow.ViewMenu, label="Listings", callback=lambda: OpenListingsWindow.Show())
dpg.add_menu_item(parent=MainWindow.ViewMenu, label="Sets", callback=lambda: SetsWindow.Show())
dpg.add_menu_item(parent=MainWindow.ViewMenu, label="Wallet", callback=lambda: WalletWindow.Show())
dpg.add_menu_item(parent=MainWindow.ViewMenu, label="Log", callback=lambda: dpg.configure_item(logger.window_id, show=True))

# hide the logger by default
dpg.configure_item(logger.window_id, show=False)

dpg.setup_registries()

# https://github.com/hoffstadt/DearPyGui/wiki/Viewport#manual-viewport
vp = dpg.create_viewport(title=f"Archivist\'s Pride {AppVersion} by JERisBRISK")

# must be called before showing viewport
dpg.set_viewport_small_icon('parallel.ico')
dpg.set_viewport_large_icon('parallel.ico')
dpg.setup_dearpygui(viewport=vp)

dpg.show_viewport(vp)
dpg.maximize_viewport()

dpg.start_dearpygui()
