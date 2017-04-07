import time
import machine
import json
from umqtt.simple import MQTTClient

from ubinascii import hexlify
from network import WLAN
MACHINE_ID = hexlify(WLAN().config('mac')).decode()


class Device(object):
    def __init__(self, name, pin=None, pwm=None, freq=1000, duty=1024, irq=False, read=None, publish=None, subscribe=None, mqtt=None, oneshot=False, **kwargs):
        self.name = name
        self.kwargs = kwargs
        self.time = time.time()

        if type(mqtt) == tuple:
            try:
                kwargs = mqtt[1]
            except IndexError:
                kwargs = {}
            self.mqtt = MQTTClient(
                bytes('{0}/{1}'.format(MACHINE_ID, self.name), 'ascii'),
                bytes(mqtt[0], 'ascii'),
                **kwargs
            )
        else:
            self.mqtt = mqtt

        if not self.mqtt.connect(clean_session=True):
            print("Connected to MQTT as client {0}".format(self.mqtt.client_id))

        try:
            func_sample = kwargs.get('function_sample', 'sample_{0}'.format(name))
            self.function_sample = getattr(self, func_sample)
        except:
            self.function_sample = None

        self.events = 0
        self.data = []

        if pin:
            self.pin_id = pin
            self.pin = machine.Pin(pin, machine.Pin.IN)
            self.pin_out = machine.Pin(pin, machine.Pin.OUT, value=self.pin.value)

        if pwm:
            self.pwm_id = pwm
            self.pwm = machine.PWM(machine.Pin(pwm), freq=freq, duty=duty)

        if read:
            self.read = read
            func_name = read.get('function', 'read_{0}'.format(name))
            self.function_read = getattr(self, func_name)
            if oneshot:
                self._callback_read()
            else:
                if read.get('irq'):
                    self.pin.irq(trigger=machine.Pin.IRQ_FALLING, handler=self._callback_read)
                else:
                    # Gather data in given interval if we are not going to use IRQ
                    self.timer_callback = machine.Timer(-1)
                    self.timer_callback.init(period=self.read['interval'] * 1000, mode=machine.Timer.PERIODIC, callback=self._callback_read)

        if publish is not None:
            self.publish = publish
            self.publish['topic'] = bytes(publish.get('topic', "{0}/{1}".format(
                publish.get('topic_base', "esp/{0}".format(MACHINE_ID)),
                self.name
            )), 'ascii')
            if oneshot:
                self.publish_data()
            else:
                self.timer_publish = machine.Timer(-1)
                self.timer_publish.init(period=publish.get('interval', 30) * 1000, mode=machine.Timer.PERIODIC, callback=self.publish_data)

        if subscribe is not None:
            self.subscribe = subscribe
            func_name = subscribe.get('function', 'write_{0}'.format(name))
            self.function_write = getattr(self, func_name)
            self.subscribe['topic'] = bytes(subscribe.get('topic', "{0}/{1}/control".format(
                subscribe.get('topic_base', "esp/{0}".format(MACHINE_ID)),
                self.name
            )), 'ascii')
            self.mqtt.set_callback(self._callback_subscribe)
            self.mqtt.subscribe(self.subscribe['topic'])
            if oneshot:
                self.subscribe_data()
            else:
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
            self.publish_data(*args, **kwargs)

    def read_dht11(self, *args, **kwargs):
        import dht
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

    def read_pwm(self, *args, **kwargs):
        return({
            'freq': self.pwm.freq(),
            'duty': self.pwm.duty(),
        })

    def write_pwm(self, topic, data):
        param = json.loads(data)
        if param.get('freq'):
            print("{0}: setting pwm freq to {1}".format(self.name, param['freq']))
            self.pwm.freq(param['freq'])
        if param.get('duty'):
            print("{0}: setting pwm duty to {1}".format(self.name, param['duty']))
            self.pwm.duty(param['duty'])
        return(param)

    def write_status(self, topic, value):
        self.pin_out.value(int(value))
        return({
            'value': value
        })

    def toggle_status(self, *args, **kwargs):
        self.pin_out.value(0 if self.pin.value() else 1)
        return({
            'value': self.pin.value()
        })

    def read_dht22(self, *args, **kwargs):
        import dht
        d = dht.DHT22(machine.Pin(self.pin_id))
        d.measure()
        print("{0}: {1}C, {2}%".format(self.name, d.temperature(), d.humidity()))
        return({
            'temperature': d.temperature(),
            'humidity': d.humidity()
        })

    def read_ds18x20(self, *args, **kwargs):
        import onewire
        import ds18x20
        ds = ds18x20.DS18X20(onewire.OneWire(self.pin))
        devs = ds.scan()
        ds.convert_temp()
        time.sleep_ms(750)

        data = {}
        i = 0
        for dev in devs:
            data['temperature{0}'.format(i)] = ds.read_temp(dev)
            print("{0}: {1}={2}C".format(self.name, i, data['temperature{0}'.format(i)]))
            i += 1

        return data

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
        if self.publish.get('retain', False):
            self.mqtt.publish(self.publish['topic'], bytes(json.dumps(self.read_data()[1][-1]), 'ascii'), retain=True)
        else:
            for dat in self.read_data()[1]:
                self.mqtt.publish(self.publish['topic'], bytes(json.dumps(dat), 'ascii'))
        print("Sent data to topic {0}".format(self.publish['topic']))

    def subscribe_data(self, *args, **kwargs):
        print("Reading data from topic {0}".format(self.name, self.subscribe['topic']))
        self.mqtt.check_msg()
