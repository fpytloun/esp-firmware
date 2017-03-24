import sys
import time
import json
import machine
import network
import ubinascii
from umqtt.robust import MQTTClient

import micropython
micropython.alloc_emergency_exception_buf(100)

MACHINE_ID = ubinascii.hexlify(network.WLAN().config('mac')).decode()
global devices
devices = {}


class Device(object):
    def __init__(self, name, pin, irq=False, publish=None, mqtt=None, **kwargs):
        self.name = name
        self.kwargs = kwargs
        self.time = time.time()
        self.mqtt = mqtt

        func_name = kwargs.get('function', 'read_{0}'.format(name))
        self.function = getattr(self, func_name)

        try:
            func_sample = kwargs.get('function_sample', 'sample_{0}'.format(name))
            self.function_sample = getattr(self, func_sample)
        except:
            self.function_sample = None

        self.events = 0
        self.data = []

        self.pin_id = pin
        self.pin = machine.Pin(pin, machine.Pin.IN)
        if irq:
            self.pin.irq(trigger=machine.Pin.IRQ_FALLING, handler=self.callback)
        else:
            # Gather data in given interval if we are not going to use IRQ
            self.timer_callback = machine.Timer(-1)
            self.timer_callback.init(period=self.kwargs.get('interval', 30) * 1000, mode=machine.Timer.PERIODIC, callback=self.callback)

        if publish:
            self.publish = publish
            self.topic = "{0}/{1}".format(publish['topic_base'], self.name)
            self.timer_publish = machine.Timer(-1)
            self.timer_publish.init(period=publish['interval'] * 1000, mode=machine.Timer.PERIODIC, callback=self.publish_data)

    def callback(self, event=None):
        self.events += 1
        data = self.function()
        if data:
            self.data.append(data)

    def read_dht11(self):
        import dht
        d = dht.DHT11(machine.Pin(self.pin_id))
        d.measure()
        print("{0}: {1}C, {2}%".format(self.name, d.temperature(), d.humidity()))
        return({
            'temperature': d.temperature(),
            'humidity': d.humidity()
        })

    def read_dht22(self):
        import dht
        d = dht.DHT22(machine.Pin(self.pin_id))
        d.measure()
        print("{0}: {1}C, {2}%".format(self.name, d.temperature(), d.humidity()))
        return({
            'temperature': d.temperature(),
            'humidity': d.humidity()
        })

    def read_rpm(self):
        pass

    def sample_rpm(self):
        sample = time.time() - self.time
        print("{0}: {1} events in {2} seconds".format(self.name, self.events, sample))
        return [{
            'rounds': self.events,
            'sample': sample,
            'rps': self.events / sample,
            'rpm': self.events / sample * 60,
        }]

    def reset(self):
        self.events = 0
        self.data = []
        self.time = time.time()

    def read_data(self):
        irq_state = machine.disable_irq()

        if self.function_sample:
            data = self.function_sample()
        else:
            data = self.data

        ret = (self.events, data)
        self.reset()
        machine.enable_irq(irq_state)
        return ret

    def publish_data(self, event=None):
        # XXX: we receive following exception if called from callback:
        #   IndexError: bytes index out of range
        # but we can create connection from main and pass it to device objects,
        # anyway this is still issue when reconnection is needed. Also we cannot
        # handle catch exceptions from callbacks in main to simply reset.
        # self.mqtt.connect()
        for dat in self.read_data()[1]:
            self.mqtt.publish(self.topic, str(json.dumps(dat)))
        print("Sent data to server {0}, topic {1}".format(self.publish['server'], self.topic))
        # self.mqtt.disconnect()


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


class Config(object):
    # Default configuration
    CONFIG = {
        "sleep_type": "idle",
        "sleep_time": 60000,
        "exception_raise": False,
        "exception_wait": 10,
        "publish": {
            "topic_base": "esp/{0}".format(MACHINE_ID),
            "interval": 30,
        },
    }

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

        return self.dictmerge(self.CONFIG, data)


def main():
    conf = Config()
    while True:
        try:
            global devices
            # Initialize devices objects if not initialized yet
            for name, args in conf.config.get('device', {}).items():
                if name not in devices.keys():
                    if 'publish' not in args.keys():
                        args['publish'] = conf.config['publish']

                    client_id = "{0}_{1}".format(MACHINE_ID, name)
                    c = MQTTClient(bytes(client_id, 'ascii'), bytes(args['publish']['server'], 'ascii'))
                    if not c.connect(clean_session=False):
                        print("Connected to {0} as client {1}".format(args['publish']['server'], client_id))
                    args['mqtt'] = c

                    print("Initializing device {0} with args {1}".format(name, args))
                    devices[name] = Device(name, **args)

            sleep(conf.config['sleep_type'], conf.config['sleep_time'])
        except Exception as e:
            if conf.config.get('exception_raise', True):
                raise e
            else:
                sys.print_exception(e)
                print("Sleeping for {0}".format(conf.config['exception_wait']))
                time.sleep(conf.config['exception_wait'])


if __name__ == '__main__':
    main()
