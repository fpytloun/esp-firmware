import machine
import network

if machine.reset_cause() == machine.DEEPSLEEP_RESET:
    print('Woke from a deep sleep')
else:
    print('Power on or hard reset')


def connect_wifi(essid, password):
    sta_if = network.WLAN(network.STA_IF)
    if not sta_if.isconnected():
        print('connecting to network...')
        sta_if.active(True)
        sta_if.connect(essid, password)
        while not sta_if.isconnected():
            pass
    print('network config:', sta_if.ifconfig())


def disable_ap():
    ap_if = network.WLAN(network.AP_IF)
    ap_if.active(False)


def read_wifi_config():
    with open('.wireless') as fh:
        lines = fh.readlines()
    return (lines[0].strip(), lines[1].strip())

disable_ap()

cfg = read_wifi_config()
print("Connecting to wireless network {0}".format(cfg[0]))
connect_wifi(cfg[0], cfg[1])

#import webrepl
#webrepl.start()

import gc
gc.collect()
