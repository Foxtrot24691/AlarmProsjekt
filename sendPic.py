#importerer biblioteker
from flask import Flask,send_file,request
import socket
import time
from threading import Thread
from SimpleCV import *

def runWebserver():	#om noen gaar in paa 128.39.113.151:5000/img last opp bildet test.jpg
	app = Flask(__name__)
	print("starting server ")
	@app.route('/img')
	def SendImage():
	    return send_file("test.jpg", mimetype='image/jpg')
	    print("sendt image")

	if __name__ == '__main__':
		app.run(host='0.0.0.0') #everyone is allowed to access my Server
	
#aapner webserveren som thread, orginalt skulle webserveren vaere i en thread i hovedprogrammet, 
#men webserveren gjorde at hovedprogrammet ikke fortsatte mens threaden var aktiv
tr2 = Thread(target=runWebserver())
tr2.daemon=True
tr2.start()
