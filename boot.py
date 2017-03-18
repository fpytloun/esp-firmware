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

disable_ap()
connect_wifi('domecek', 'akm2853cx7')

# import webrepl
# webrepl.start()
import gc
gc.collect()
