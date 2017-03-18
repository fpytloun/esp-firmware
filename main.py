import time
import json
import esp
import machine


def read_dht11(pin):
    import dht
    d = dht.DHT11(machine.Pin(pin))

    retry = 0
    while retry < 3:
        try:
            d.measure()
            print("DHT11: {0}C, {1}%".format(d.temperature(), d.humidity()))
            return({
                'temperature': d.temperature(),
                'humidity': d.humidity()
            })
        except Exception as e:
            retry += 1
            print(e)
            if retry == 3:
                raise
            time.sleep(3)


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


def main():
    topic_base = "esp/{0}".format(esp.flash_id())
    data = read_dht11(14)
    publish_data("curumo.domecek", "{0}/dht11".format(topic_base), json.dumps(data))
    deepsleep(60000)


if __name__ == '__main__':
    main()
