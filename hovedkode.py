# -*- coding: utf-8 -*-
#^^ inkluderer ÆØÅ
#importerer biblioteker
from flask import Flask,send_file,request
import RPi.GPIO as GPIO
import time
import smbus 
import socket
from threading import Thread
import os
import sys
import binascii
import struct
from SimpleCV import *
from bluepy.btle import UUID, Peripheral
import serial

#setter opp kamera
cam = Camera()

#setter opp seriekommunikasjon med stepper motor controller
ser = serial.Serial('/dev/ttyACM0', 9600,
parity=serial.PARITY_NONE,
stopbits=serial.STOPBITS_ONE,
bytesize=serial.EIGHTBITS)
global servoValue
servoValue ="000"

#setter opp bluetooth service
button_service_uuid = UUID(0xA000)
button_char_uuid    = UUID(0xA002)

bus = smbus.SMBus(1) #opens /dev/i2c-1
address=0x52         #the Nunchuk I2C address 
bus.write_byte_data(address,0x40,0x00)
bus.write_byte_data(address,0xF0,0x55)
bus.write_byte_data(address,0xFB,0x00)

#velger IP addresse for sending og mottak
SEND_UDP_IP = "128.39.112.171"
#SEND_UDP_IP = "128.39.113.151"
REC_UDP_IP = "128.39.113.151"
#REC_UDP_IP = "128.39.112.171"

#maalport for UDP mottak og sending
UDP_PORT = 9050

print "UDP target sending IP:",   SEND_UDP_IP
print "UDP target recive IP:",   REC_UDP_IP
print "UDP target port:", UDP_PORT
 
sock = socket.socket(socket.AF_INET,     # Internet protocol
                     socket.SOCK_DGRAM)  # User Datagram (UDP)
Lsock = socket.socket(socket.AF_INET,    # Internet protocol
      			 socket.SOCK_DGRAM) # User Datagram (UDP)
Lsock.bind((REC_UDP_IP, UDP_PORT))

#initialiserer GPIO pinner
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(23, GPIO.IN)
GPIO.setup(18, GPIO.IN)
GPIO.setup(24, GPIO.IN)
GPIO.setup(17, GPIO.OUT)
GPIO.setup(22, GPIO.OUT)
GPIO.setup(27, GPIO.OUT)
GPIO.output(17, GPIO.LOW)
GPIO.output(27, GPIO.LOW)
GPIO.output(22, GPIO.LOW)

#initialiserer variabler
on = False
oldOn = False
old23=0
old18=0
kontrollStatus =0
global blobSize
blobSize=20
sisteEndring=0

bus.write_byte(address,0x00)
oldArData0 =  bus.read_byte(address)
oldArData1 =  bus.read_byte(address)
oldArData2 =  bus.read_byte(address)
oldArData3 =  bus.read_byte(address)
oldArData4 =  bus.read_byte(address)
oldArData5 =  bus.read_byte(address)
oldArData = [oldArData0, oldArData1, oldArData2, oldArData3, oldArData4, oldArData5]  
app = Flask(__name__)
global BLE_status
BLE_status =0
prev_BLE_status =0

def bevegelseSensor():
	global blobSize       
	print("looking for blobs")
	lastImg = Image("oldImg.jpg")#henter bildet som ble tatt i starten av hoved while loopen
	time.sleep(.01) 
	newImg = cam.getImage()  #tar et nytt bilde 
	time.sleep(.01) 
	trackImg = newImg -  lastImg    #sammenligner nytt og gammelt bilde
	blobs = trackImg.findBlobs(blobSize) #bruker adaptiv blob deteksjon for aa se etter 
	#samlinger av forskjeller mellom bildene
	if blobs: #hvis en blob paa blobSize er funnet sett led som viser bevegelse hoy og lagre bildene som satte i gang alarmen
		print("movement found!")
		lastImg.save("lastTrig.jpg")
		newImg.save("newTrig.jpg")
		GPIO.output(22, GPIO.HIGH)

def taBilde():#tar et bilde og lagrer det i filen test.jpg som webserveren laster opp bilder fra
	print("Tar bilde")
  	bilde = cam.getImage()
	bilde.save("test.jpg")

def runWebserver():	#om noen gaar in paa 128.39.113.151:5000/img last opp bildet test.jpg
	while True:
		@app.route('/img')
		def SendImage():
		    return send_file("test.jpg", mimetype='image/jpg')
		if __name__ == '__main__':
			app.run(host='0.0.0.0') #everyone is allowed to access my Server
def BLE():
	global button_service_uuid
        global ButtonService
	global button_char_uuid
	global BLE_status
	p = Peripheral("f7:3d:1b:24:9f:0a", "random")
	ButtonService=p.getServiceByUUID(button_service_uuid)
	try:
		ch = ButtonService.getCharacteristics(button_char_uuid)[0]
		while(ch.supportsRead()):
        	    	val = binascii.b2a_hex(ch.read())
			if(val=="00"):
				BLE_status=0
			else:
				BLE_status=1
	except IOError as e:
		print e
	finally:
		p.disconnect()

def servoCtrl():
	global servoValue
	while True:
		ser.flushInput()               
		time.sleep(0.01) 
		ser.write(str(servoValue))

#starter webserveren som en thread, daemon gør at serveren stenger når hovedprogrammet stenger
tr2 = Thread(target=runWebserver)
tr2.daemon=True
tr2.start()

#starter BLE som en thread, daemon gør at BLE stenger når hovedprogrammet stenger
tr1 = Thread(target=BLE)
tr1.daemon=True
tr1.start()

#starter servoCtrl som en thread, daemon gør at den stenger når hovedprogrammet stenger
tr3 = Thread(target=servoCtrl)
tr3.daemon=True
tr3.start()
	
while True:
	#tar et bilde faar aa sammenligne med senere
	newImg =cam.getImage()
	newImg.save("oldImg.jpg")
	
	#Henter nunchuck data
	bus.write_byte(address,0x00)
	data0 =  bus.read_byte(address)
	data1 =  bus.read_byte(address)
	data2 =  bus.read_byte(address)
	data3 =  bus.read_byte(address)
	data4 =  bus.read_byte(address)
	data5 =  bus.read_byte(address)
	data = [data0, data1, data2, data3, data4, data5]  
	joy_x = data[0]
	joy_y = data[1]
	cBut = (data[5]&0x02)>>1
	zBut = (data[5]&0x01)
	print "joyX: %s joyY: %s" % (joy_x ,joy_y) + "Button C: %s Button Z: %s"%(cBut,zBut)

	#henter data fra UDP
	data, addr = Lsock.recvfrom(1280) # Max recieve size is 1280 bytes
	print "received message:", data
    
	#splitter datastrengen fra UDP fra GUI til et array paa 5 chars
	#char 0 holder navn paa meldingen, char 1 holder alarmsignal,
	#char 2 holder kontrollsignal, char 3 holder servo verdi,
	#char 4 holer signal for aa ta ett bilde
	#det siste bitet maa rstripes for aa fjaerne en newline character ("\n")
	arData = data.split(",")
	arData[5] = arData[5].rstrip()
	print("printer ra data "+str(data))

    
	#hvis knapp Z paa nunchuck eller signal fra GUI ber om det: ta bilde
	if(arData[4]=='1')or(zBut==0):
		taBilde()

	print("Alarmstatus for skjekk: "+str(on))
	#pinne 23 skrur alarmen av og pa hvis det er endring paa av/paa knappen paa rPi eller endring i signal fra GUI eller BLE
	input23 = GPIO.input(23)
	if (input23 != old23):
		print("arData[1] er: " +str(arData[1])+ " gammel verdi: "+str(oldArData[1]))
		print("GPIO 23   er: " +str(input23)+ " gammel verdi: "+str(old23))
		print("BLE       er: " +str(BLE_status)+ " gammel verdi: "+str(prev_BLE_status))
		oldArData[1]=arData[1]
        	prev_BLE_status=BLE_status
		old23=input23
		on = not on
		sisteEndring=1	#sier ifra at alarmen ble skrudd av/på av rPi
	elif(arData[1]!=oldArData[1]):
		print("arData[1] er: " +str(arData[1])+ " gammel verdi: "+str(oldArData[1]))
		print("GPIO 23   er: " +str(input23)+ " gammel verdi: "+str(old23))
		print("BLE       er: " +str(BLE_status)+ " gammel verdi: "+str(prev_BLE_status))
		oldArData[1]=arData[1]
        	prev_BLE_status=BLE_status
		old23=input23
		on = not on
		sisteEndring=2	##sier ifra at alarmen ble skrudd av/på av GUI
	elif(BLE_status != prev_BLE_status):
		print("arData[1] er: " +str(arData[1])+ " gammel verdi: "+str(oldArData[1]))
        	print("GPIO 23   er: " +str(input23)+ " gammel verdi: "+str(old23))
		print("BLE       er: " +str(BLE_status)+ " gammel verdi: "+str(prev_BLE_status))
		oldArData[1]=arData[1]
        	prev_BLE_status=BLE_status
        	old23=input23
		on = not on
		sisteEndring=3	##sier ifra at alarmen ble skrudd av/på av BLE
	else:
		pass
	#pinne 18 skrur av/pa lokal kontroll hvis det er endring paa kontroll knappen paa rPi eller endring i signal fra GUI
	input18 = GPIO.input(18)
	if (input18 != old18)or(arData[2]!=oldArData[2]):
		print("GPIO 18   er: " +str(input18)+ " gammel verdi: "+str(old18))
		print("arData[2] er: " +str(arData[2])+ " gammel verdi: "+str(oldArData[2]))
		old18=input18
		oldArData[2]=arData[2]
		kontrollStatus = not kontrollStatus
		print("Kontrollstatus: ",kontrollStatus)
	else: 
		pass

	#kontrollerer servo
	#ser om gui eller gpio skal styre servo, 0 gir lokal kontroll, 1 gir ekstern kontroll
	if(kontrollStatus==0):#lokal servokontroll
		print("Styrer lokalt")
		GPIO.output(27, GPIO.LOW)
		#ser etter signal fra nunchuck, modifiserer servoint for aa rotere kamera
		if((joy_x >= 181)and(servoInt <= 245)):
			servoInt += 10
		elif((joy_x <= 101)and(servoInt >= 10)):
			servoInt -= 10
		else: 
			pass
		#skriver over strengen servoValue med den modifiserte servoInt
		servoValue = str(servoInt).zfill(3)#padder servoValue slik at den består av 3 chars

	else:
		print("Styrer eksternt")	
		GPIO.output(27, GPIO.HIGH)
		servoValue= arData[3]#henter data fra GUI og skriver over servoverdi
		servoInt= int(servoValue)

	

	#sender kontrollsignal til servo ved aa kjore servoCommand.py med argument for onsket servo posisjon
	
	#system("python servoCommand.py "+ servoValue)

	print("ServoVerdi "+ str(servoValue) )
	print("arData "+ str(arData))
	
	#samler data fra alarmknapp, alarmstatus, kontrollstatus, servoposisjon og zknapp status i en komma separert streng(CSV) 
	Message= "$SW,"+str(input23)+","+str(on)+","+str(kontrollStatus)+","+str(servoValue.zfill(3))+","+str(zBut)+","+str(sisteEndring)
	
	#Sender CSV strengen som UDP melding
	sock.sendto(Message, (SEND_UDP_IP, UDP_PORT))
	print "Sendt Message: "+Message

	#Setter led 17 pa om alarmen er pa for aa vise at alarmen er paa og ser etter bevegelse
	#hvis alarmen er av skrus av alarm led 17 og deteksjons led 22
	if (on == True):
		GPIO.output(17, GPIO.HIGH)
		blobSize=int(arData[5])
		bevegelseSensor()
	else:
		GPIO.output(17, GPIO.LOW)
		GPIO.output(22, GPIO.LOW)
	time.sleep(0.1)

