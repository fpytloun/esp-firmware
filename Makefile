all: build put

build:
	(ls src/*.py | while read i; do \
		echo "Building $$i"; \
		mpy-cross $$i || exit 1; done)

put:
	find src -name "*.mpy" -a ! -name "main.mpy" -a ! -name "boot.mpy" | while read i; do \
		echo "Uploading $$i"; \
		ampy -p /dev/ttyUSB0 put $$i || exit 1; done
	ampy -p /dev/ttyUSB0 put src/boot.py
	ampy -p /dev/ttyUSB0 put src/main.py
