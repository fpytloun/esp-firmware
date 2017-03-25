Flash firmware:

.. code-block:: bash

    python esptool.py --port /dev/ttyUSB0 --baud 460800 write_flash --flash_size=detect 0 esp8266-20170108-v1.8.7.bin

Upload files:

.. code-block:: bash

    for i in src/*.py conf/*.json; do  ampy -p /dev/ttyUSB0 put $i; done

Workaround for ``ampy.pyboard.PyboardError: could not enter raw repl`` issue:

.. code-block:: bash

    import os
    os.remove('main.py')
    # press ctrl+D to reset, disconnect from console and run ampy again
