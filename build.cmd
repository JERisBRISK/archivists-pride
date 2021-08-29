pyinstaller --onefile --noconsole main.py --icon=parallel.ico --name=ArchivistsPride
copy /y *.json dist
copy /y parallel.ico dist
copy /y LICENSE dist\LICENSE.txt