!/usr/bin/python3

import serial
import sys
import time
ser = serial.Serial('/dev/ttyACM0', 9600,
parity=serial.PARITY_NONE,
stopbits=serial.STOPBITS_ONE,
bytesize=serial.EIGHTBITS)

ser.flushInput()               

time.sleep(0.01) 

ser.write(str(sys.argv[1]))
