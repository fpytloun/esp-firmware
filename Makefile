CWD=$(shell pwd)

.PHONY: espsdk micropython micropython-lib

all: build put

build:
	(ls src/*.py | while read i; do \
		echo "Building $$i"; \
		mpy-cross $$i || exit 1; done)

put-lib: build
	find src/lib -name "*.mpy" -a ! -name "main.mpy" -a ! -name "boot.mpy" | while read i; do \
		echo "Uploading $$i"; \
		ampy -p /dev/ttyUSB0 put $$i || exit 1; done

put-scripts:
	ampy -p /dev/ttyUSB0 put src/boot.py
	ampy -p /dev/ttyUSB0 put src/main.py

put-config:
	[ ! -f conf/.wireless ] || ampy -p /dev/ttyUSB0 put conf/.wireless
	[ ! -f conf/webrepl_cfg.py ] || ampy -p /dev/ttyUSB0 put conf/webrepl_cfg.py
	[ ! -f conf/$(DEVICE).json ] || ampy -p /dev/ttyUSB0 put conf/$(DEVICE).json

put: put-lib put-config put-scripts

flash: micropython flash-erase flash-write

flash-erase: espsdk
	./espsdk/esptool/esptool.py --port /dev/ttyUSB0 erase_flash

flash-write: espsdk micropython
	./espsdk/esptool/esptool.py --port /dev/ttyUSB0 --baud 460800 write_flash --flash_size=detect 0 ./micropython/esp8266/build/firmware-combined.bin

submodule:
	git submodule update --init --recursive

espsdk: submodule
	# XXX: this make always returns failure so pretend it's ok
	(cd espsdk; make -j4 STANDALONE=y || true)

micropython: submodule espsdk mpy_cross micropython-lib
	cp src/lib/* micropython/esp8266/modules/
	(cd micropython/esp8266; export PATH=$${PATH}:$(CWD)/espsdk/crosstool-NG/bin:$(CWD)/espsdk/xtensa-lx106-elf/bin; make -j4)

micropython-lib: submodule
	(cd micropython-lib; \
		make install PREFIX=$(CWD)/micropython/esp8266/modules MOD=umqtt.simple)

mpy_cross: submodule
	(cd micropython; make -C mpy-cross)
