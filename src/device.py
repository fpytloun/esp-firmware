import dht
import time
import machine
import json

import ubinascii
import network
MACHINE_ID = ubinascii.hexlify(network.WLAN().config('mac')).decode()


class Device(object):
    def __init__(self, name, pin, irq=False, read=None, publish=None, subscribe=None, mqtt=None, **kwargs):
        self.name = name
        self.kwargs = kwargs
        self.time = time.time()
        self.mqtt = mqtt

        try:
            func_sample = kwargs.get('function_sample', 'sample_{0}'.format(name))
            self.function_sample = getattr(self, func_sample)
        except:
            self.function_sample = None

        self.events = 0
        self.data = []

        self.pin_id = pin
        self.pin = machine.Pin(pin, machine.Pin.IN)
        self.pin_out = machine.Pin(pin, machine.Pin.OUT, value=self.pin.value)

        if read:
            self.read = read
            func_name = read.get('function', 'read_{0}'.format(name))
            self.function_read = getattr(self, func_name)
            if read.get('irq'):
                self.pin.irq(trigger=machine.Pin.IRQ_FALLING, handler=self._callback_read)
            else:
                # Gather data in given interval if we are not going to use IRQ
                self.timer_callback = machine.Timer(-1)
                self.timer_callback.init(period=self.read['interval'] * 1000, mode=machine.Timer.PERIODIC, callback=self._callback_read)

        if publish:
            self.publish = publish
            self.publish['topic'] = bytes(publish.get('topic', "{0}/{1}".format(
                publish.get('topic_base', "esp/{0}".format(MACHINE_ID)),
                self.name
            )), 'ascii')
            self.timer_publish = machine.Timer(-1)
            self.timer_publish.init(period=publish.get('interval', 30) * 1000, mode=machine.Timer.PERIODIC, callback=self.publish_data)

        if subscribe:
            self.subscribe = subscribe
            func_name = subscribe.get('function', 'write_{0}'.format(name))
            self.function_write = getattr(self, func_name)
            self.subscribe['topic'] = bytes(subscribe.get('topic', "{0}/{1}/control".format(
                subscribe.get('topic_base', "esp/{0}".format(MACHINE_ID)),
                self.name
            )), 'ascii')
            self.mqtt.set_callback(self._callback_subscribe)
            self.mqtt.subscribe(self.subscribe['topic'])
            self.timer_subscribe = machine.Timer(-1)
            self.timer_subscribe.init(period=subscribe.get('interval', 10) * 1000, mode=machine.Timer.PERIODIC, callback=self.subscribe_data)

    def _callback_read(self, *args, **kwargs):
        self.events += 1
        data = self.function_read(*args, **kwargs)
        if data:
            self.data.append(data)

    def _callback_subscribe(self, *args, **kwargs):
        print("{0}: received data over MQTT (args: {1}, kwargs: {2})".format(self.name, args, kwargs))
        self.events += 1
        data = self.function_write(*args, **kwargs)
        if data:
            self.data.append(data)

    def read_dht11(self, *args, **kwargs):
        d = dht.DHT11(machine.Pin(self.pin_id))
        d.measure()
        print("{0}: {1}C, {2}%".format(self.name, d.temperature(), d.humidity()))
        return({
            'temperature': d.temperature(),
            'humidity': d.humidity()
        })

    def read_status(self, *args, **kwargs):
        print("{0}: status is {1}".format(self.name, self.pin.value()))
        return({
            'value': self.pin.value()
        })

    def write_status(self, topic, value):
        self.pin_out.value(int(value))

    def toggle_status(self, *args, **kwargs):
        self.pin_out.value(0 if self.pin.value() else 1)

    def read_dht22(self, *args, **kwargs):
        d = dht.DHT22(machine.Pin(self.pin_id))
        d.measure()
        print("{0}: {1}C, {2}%".format(self.name, d.temperature(), d.humidity()))
        return({
            'temperature': d.temperature(),
            'humidity': d.humidity()
        })

    def read_rpm(self, *args, **kwargs):
        pass

    def sample_rpm(self, *args, **kwargs):
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

    def read_data(self, *args, **kwargs):
        irq_state = machine.disable_irq()

        if self.function_sample:
            data = self.function_sample()
        else:
            data = self.data

        ret = (self.events, data)
        self.reset()
        machine.enable_irq(irq_state)
        return ret

    def publish_data(self, *args, **kwargs):
        for dat in self.read_data()[1]:
            self.mqtt.publish(self.publish['topic'], bytes(json.dumps(dat), 'ascii'))
        print("Sent data to topic {0}".format(self.publish['topic']))

    def subscribe_data(self, *args, **kwargs):
        print("Reading data from topic {0}".format(self.name, self.subscribe['topic']))
        self.mqtt.check_msg()
