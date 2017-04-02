import sys
import time
import json
import machine
import network
import ubinascii
from umqtt.simple import MQTTClient

import micropython
micropython.alloc_emergency_exception_buf(100)

from device import Device

import gc
gc.collect()

MACHINE_ID = ubinascii.hexlify(network.WLAN().config('mac')).decode()


def sleep(sleep_type, sleep_time=60000):
    if sleep_type == "deepsleep":
        print("Putting device into {0} for {1} seconds".format(sleep_type, sleep_time / 1000))
        if sleep_time:
            rtc = machine.RTC()
            rtc.irq(trigger=rtc.ALARM0, wake=getattr(machine, sleep_type.upper()))
            rtc.alarm(rtc.ALARM0, sleep_time)

        machine.deepsleep()
    if sleep_type == "idle":
        machine.idle()
    if sleep_type == "sleep":
        machine.sleep()
    if sleep_type == "wait":
        time.sleep(sleep_time / 1000)


class Config(object):
    # Default configuration
    CONFIG = {}

    def __init__(self, config_file=None):
        self.config_file = config_file if config_file else "{0}.json".format(MACHINE_ID)
        self.config = self.parse_config()

    def dictmerge(self, a, b, path=None):
        if path is None:
            path = []
        for key in b:
            if key in a:
                if isinstance(a[key], dict) and isinstance(b[key], dict):
                    self.dictmerge(a[key], b[key], path + [str(key)])
                elif a[key] == b[key]:
                    pass
                else:
                    a[key] = b[key]
            else:
                a[key] = b[key]
        return a

    def parse_config(self):
        with open(self.config_file, 'r') as fh:
            data = json.load(fh)

        # return self.dictmerge(self.CONFIG, data)
        return data


def main():
    conf = Config()
    client_id = "{0}".format(MACHINE_ID)
    mqtt = MQTTClient(bytes(client_id, 'ascii'), bytes(conf.config['publish']['server'], 'ascii'))
    devices = {}
    while True:
        try:
            if not mqtt.connect(clean_session=False):
                print("Connected to {0} as client {1}".format(conf.config['publish']['server'], client_id))

            # Initialize devices objects if not initialized yet
            if not devices:
                for name, args in conf.config.get('device', {}).items():
                    if name not in devices.keys():
                        args['mqtt'] = mqtt
                        print("Initializing device {0} with args {1}".format(name, args))
                        devices[name] = Device(name, **args)

            # Publish health
            print("Publishing health status into topic {0}".format("{0}/health".format(
                conf.config['publish'].get('topic_base', "esp/{0}".format(MACHINE_ID))
            )))
            mqtt.publish("{0}/health".format(conf.config['publish'].get('topic_base', "esp/{0}".format(MACHINE_ID))),
                bytes(json.dumps({
                    'name': conf.config.get('friendly_name', MACHINE_ID),
                    'id': MACHINE_ID,
                    'uptime': time.ticks_ms(),
                    'mem_free': gc.mem_free(),
                    'mem_alloc': gc.mem_alloc(),
                }), 'ascii'))

            gc.collect()
            sleep(conf.config.get('sleep_type', 'wait'), conf.config.get('sleep_time', 60000))
        except Exception as e:
            if type(e) != 'KeyboardInterrupt':
                if conf.config.get('exception_raise', False):
                    raise e
                else:
                    sys.print_exception(e)
                    print("Sleeping for {0}".format(conf.config.get('exception_wait', 10)))
                    time.sleep(conf.config.get('exception_wait', 10))
                    if conf.config.get('exception_reset', False):
                        machine.reset()
                    if conf.config.get('exception_exit', False):
                        sys.exit()
