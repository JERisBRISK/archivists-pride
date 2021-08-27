from threading import Event, Thread

def SetInterval(interval, func, *args):
    stopped = Event()
    # call it right away
    func(*args)

    def loop():
        # then call it after the first interval has elapsed
        while not stopped.wait(interval):
            func(*args)
    Thread(target=loop, daemon=True).start()
    return stopped.set
