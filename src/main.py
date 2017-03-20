import sys
import time
import json
import machine
import network
import ubinascii

MACHINE_ID = ubinascii.hexlify(network.WLAN().config('mac')).decode()

# Default configuration
CONFIG = {
    "sleep_time": 60000,
    "exception_raise": True,
    "exception_wait": 30,
    "publish": {
        "topic_base": "esp/{0}"
    },
}


def read_dht11(pin):
    import dht
    d = dht.DHT11(machine.Pin(pin))
    d.measure()
    print("DHT11: {0}C, {1}%".format(d.temperature(), d.humidity()))
    return({
        'temperature': d.temperature(),
        'humidity': d.humidity()
    })


def read_dht22(pin):
    import dht
    d = dht.DHT22(machine.Pin(pin))
    d.measure()
    print("DHT22: {0}C, {1}%".format(d.temperature(), d.humidity()))
    return({
        'temperature': d.temperature(),
        'humidity': d.humidity()
    })


def publish_data(server, topic, data):
    from umqtt.simple import MQTTClient
    c = MQTTClient("umqtt_client", server)
    retry = 0
    while retry < 3:
        try:
            c.connect()
            c.publish(topic, str(data))
            c.disconnect()
            print("Sent data to server {0}, topic {1}".format(server, topic))
            break
        except Exception as e:
            retry += 1
            print(e)
            if retry == 3:
                raise
            time.sleep(3)


def deepsleep(sleep_time=60000):
    rtc = machine.RTC()
    rtc.irq(trigger=rtc.ALARM0, wake=machine.DEEPSLEEP)
    rtc.alarm(rtc.ALARM0, sleep_time)
    print("Putting device into deep sleep for {0} seconds".format(sleep_time / 1000))
    machine.deepsleep()


def dictmerge(a, b, path=None):
    if path is None:
        path = []
    for key in b:
        if key in a:
            if isinstance(a[key], dict) and isinstance(b[key], dict):
                dictmerge(a[key], b[key], path + [str(key)])
            elif a[key] == b[key]:
                pass
            else:
                a[key] = b[key]
        else:
            a[key] = b[key]
    return a


def parse_config(config_file=None, default=None):
    if not config_file:
        config_file = "{0}.json".format(MACHINE_ID)

    with open(config_file, 'r') as fh:
        data = json.load(fh)

    return dictmerge(CONFIG, data)


def main():
    conf = parse_config(None, CONFIG)
    topic_base = conf['publish']['topic_base'].format(MACHINE_ID)

    for name, args in conf.get('read', {}).items():
        func_name = args.get('function', 'read_{0}'.format(name))
        func = globals().get(func_name)
        data = func(**args.get('args', args))
        publish_data(conf['publish']['server'], "{0}/{1}".format(topic_base, name), json.dumps(data))

    deepsleep(conf['sleep_time'])


if __name__ == '__main__':
    while True:
        try:
            main()
        except Exception as e:
            if CONFIG.get('exception_raise', True):
                raise e
            else:
                sys.print_exception(e)
                print("Sleeping for {0}".format(CONFIG['exception_wait']))
                time.sleep(CONFIG['exception_wait'])
