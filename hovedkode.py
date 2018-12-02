#importerer biblioteker
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

#setter opp kamera
cam = Camera()


bus = smbus.SMBus(1) #opens /dev/i2c-1
address=0x52         #the Nunchuk I2C address 
bus.write_byte_data(address,0x40,0x00)
bus.write_byte_data(address,0xF0,0x55)
bus.write_byte_data(address,0xFB,0x00)
time.sleep(0.1)

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
blobSize=20
'''
bus.write_byte(address,0x00)
oldArData0 =  bus.read_byte(address)
oldArData1 =  bus.read_byte(address)
oldArData2 =  bus.read_byte(address)
oldArData3 =  bus.read_byte(address)
oldArData4 =  bus.read_byte(address)
oldArData5 =  bus.read_byte(address)
oldArData = [oldArData0, oldArData1, oldArData2, oldArData3, oldArData4, oldArData5]  
'''

def bevegelseSensor():      
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
    arData[4] = arData[4].rstrip()
    print("printer ra data og ardata "+data+" ",arData)

    
    #hvis knapp Z paa nunchuck eller signal fra GUI ber om det: ta bilde
    if(arData[4]=='1')or(zBut==0):
	    taBilde()

    print("Alarmstatus for skjekk: ",on)
    #pinne 23 skrur alarmen av og pa hvis det er endring paa av/paa knappen paa rPi eller endring i signal fra GUI
	  input23 = GPIO.input(23)
    if (input23 != old23)or(arData[1]!=oldArData[1]):
		  print("arData[1] er: " +str(arData[1])+ " gammel verdi: "+str(oldArData[1]))
      print("GPIO 23   er: " +str(input23)+ " gammel verdi: "+str(old23))
		  oldArData[1]=arData[1]
      old23=input23
	    on = not on
    else:
        pass

	print("Kontrollstatus for skjekk: ",kontrollStatus)
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
      print("styrer lokalt")
      GPIO.output(27, GPIO.LOW)
      #ser etter signal fra nunchuck, modifiserer servoint for aa rotere kamera
      if((joy_x >= 181)and(servoInt <= 245)):
        servoInt += 10
      elif((joy_x <= 101)and(servoInt >= 10)):
        servoInt -= 10
      else: 
        pass
      #skriver over strengen servoValue med den modifiserte servoInt
      servoValue = str(servoInt).zfill(3)#padder servoValue slik at den bestaar av 3 chars

    else:
		  print("extern styring")	
		  GPIO.output(27, GPIO.HIGH)
		  servoValue= arData[3]#henter data fra GUI og skriver over servoverdi
	

    #sender kontrollsignal til servo ved aa kjore servoCommand.py med argument for onsket servo posisjon
    os.system("python servoCommand.py "+ servoValue)

    print('ServoVerdi', servoValue )
    print('arData', str(arData))
	
	#samler data fra alarmknapp, alarmstatus, kontrollstatus, servoposisjon og zknapp status i en komma separert streng(CSV) 
    Message= "$SW,"+str(input23)+","+str(on)+","+str(kontrollStatus)+","+str(servoValue.zfill(3))+","+str(zBut)
	
    #Sender CSV strengen som UDP melding
    sock.sendto(Message, (SEND_UDP_IP, UDP_PORT))
    print "Sendt Message: "+Message

    #Setter led 17 pa om alarmen er pa for aa vise at alarmen er paa og ser etter bevegelse
	#hvis alarmen er av skrus av alarm led 17 og deteksjons led 22
    if (on == True):
       	GPIO.output(17, GPIO.HIGH)
		    bevegelseSensor()
    else:
       	GPIO.output(17, GPIO.LOW)
		    GPIO.output(22, GPIO.LOW)
    time.sleep(0.1)

