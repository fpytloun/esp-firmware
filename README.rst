================================
Micropython firmware for ESP8266
================================

Quickstart
==========

Flash firmware:

.. code-block:: bash

    python esptool.py --port /dev/ttyUSB0 --baud 460800 write_flash --flash_size=detect 0 esp8266-20170108-v1.8.7.bin

Create simple ``.wireless`` file containing:

::

    networkssid
    password

Next prepare config file for your device, it must be named by your device's
MAC address. Example files can be found in conf directory.

Upload files:

.. code-block:: bash

    for i in src/*.py conf/<devicemac>.json .wireless; do ampy -p /dev/ttyUSB0 put $i; done

Build mpy files
===============

To optimize the code, you can build mpy files using ``mpy-cross`` tool (see
https://github.com/micropython/micropython/tree/master/mpy-cross).

.. code-block:: bash

    ls src/*.py | while read i; do ./mpy-cross $i; done

.. code-block:: bash

    find src -name "*.mpy" -a ! -name "main.py" -a ! -name "boot.py" -exec ampy -p /dev/ttyUSB0 put {}\;
    ampy -p /dev/ttyUSB0 put src/boot.py
    ampy -p /dev/ttyUSB0 put src/main.py


Troubleshooting
===============

``ampy.pyboard.PyboardError: could not enter raw repl``
-------------------------------------------------------
.. code-block:: bash

    import os
    os.remove('main.py')
    # press ctrl+D to reset, disconnect from console and run ampy again
