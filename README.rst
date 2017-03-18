Flash firmware:

.. code-block:: bash

    python /home/filip/src/hacking/esptool/esptool.py --port /dev/ttyUSB0 --baud 460800 write_flash --flash_size=detect 0 esp8266-20170108-v1.8.7.bin

Update files:

.. code-block:: bash

    ampy -p /dev/ttyUSB0 -b 9600 put boot.py main.py
