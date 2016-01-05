#!/usr/bin/env python

"""
Zeroconf Discovery for Rigol DS1000Z-series scopes
--------------------------------------------------

Documentation worth looking at:
* http://lxistandard.org/Documents/Specifications/LXI%20Device%20Specification%202011%20rev%201.4.pdf
* http://lxistandard.org/GuidesForUsingLXI/Introducing%20LXI%20To%20Your%20Network%20Administrator%20May%2024_2013.pdf
* http://lxistandard.org/GuidesForUsingLXI/LXI_Getting_Started_Guide_May_1_2013.pdf
* http://beyondmeasure.rigoltech.com/acton/attachment/1579/f-0386/1/-/-/-/-/DS1000Z_Programming%20Guide_EN.pdf

TODO:
foo/bar...
remove debug
"""

from zeroconf import *
import socket
import time
import requests
from lxml import etree
import re
import sys
import os
import liblo
from Tkinter import *
import tkMessageBox
import thread

import pyvona
v = pyvona.create_voice('GDNAIMFKLLI6XPXAMQAQ', 'L31mKbG0ScMJQHN6OeWNlcjOT4chB0AgFEVnq8pS')
v.speech_rate = "fast"

global results

def strType(var):
    try:
        if int(var) == float(var):
            return 'int'
    except:
        try:
            float(var)
            return 'float'
        except:
            return 'str'
            
def evaluate(calling):
	c = str(text.get("1.0",END)).strip()
	for result in results:
				print('Trying to connect to {}...'.format(socket.inet_ntoa(result['zc_info'].address)))
				scpi_connection = get_scpi_connection_tuple((socket.inet_ntoa(result['zc_info'].address), result['zc_info'].port))
				
				if scpi_connection is not (None, None):
					if any("?" in s for s in c):
						rs = receive_scpi(scpi_connection, c)
						textb.delete("1.0", END)
						if strType(rs) == "float":
							t = str(float(rs))
						else:
							t = str(rs)
						textb.insert(END, t)
						if ttsenabled.get():
							thread.start_new_thread(tts, (t,))
					else:
						send_scpi(scpi_connection, str(text.get("1.0",END)).strip())
	text.delete("1.0", END)

countersay = 0
def sayittb(calling):
	c = str(textb.get("1.0",END)).strip().split(" ")
	print c
	if ttsenabled.get():
		global countersay
		thread.start_new_thread(tts, (c[countersay],))
		countersay = countersay + 1

def sayittbreset(calling):
	global countersay
	countersay = 0
	textb.delete("1.0", END)
	
top = Tk()
text = Text(top)
text.config(font=('helvetica', 24, 'normal')) 
text.config(width=20, height=4)
text.insert(INSERT, "")
text.bind("<Return>", evaluate)
text.pack(expand=YES, fill=X)
textb = Text(top)
textb.config(font=('helvetica', 24, 'normal')) 
textb.config(width=4, height=4, background="black", foreground="white")
textb.insert(INSERT, "")
textb.bind("<space>", sayittb)
textb.bind("<Return>", sayittbreset)
textb.pack(expand=YES, fill=X)
speechenabled = IntVar()  
speechenabled.set(1)

ttsenabled = IntVar()  
ttsenabled.set(1)
        
c = Checkbutton(top, text="Enable Speech Recognition", variable=speechenabled)
c.pack(padx=0, pady=10, side=LEFT)

tts = Checkbutton(top, text="Enable Text to Speech", variable=ttsenabled)
tts.pack(padx=5, pady=10, side=LEFT)

micoff = PhotoImage(file="micoff.gif")
micon = PhotoImage(file="mic.gif")
recreadyicon = Label(top, image=micon)
recreadyicon.photo = micon
recreadyicon.pack(padx=5, pady=10, side=RIGHT)

# create server, listening on port 1234
try:
    server = liblo.Server(1234)
except liblo.ServerError as err:
    print(err)
    sys.exit()

try:
    clock = time.perf_counter
except AttributeError:
    clock = time.time


class Listener(object):
    def __init__(self, filter_func=None):
        self.results = []
        self.filter_func = filter_func

    def remove_service(self, zeroconf, zc_type, zc_name):
        #print('Service "{0}" removed'.format(zc_name))
        pass

    def add_service(self, zeroconf, zc_type, zc_name):
        zc_info = zeroconf.get_service_info(zc_type, zc_name)
        zc_info._properties = {k: v for k, v in zc_info.properties.items() if v is not None}

        result = {
          'zc_name' : zc_name,
          'zc_type' : zc_type,
          'zc_info' : zc_info,
        }
        if self.filter_func:
            if self.filter_func(result):
                self.results.append(result)
        else:
            self.results.append(result)

    @staticmethod
    def pprint(zc_name, zc_type, zc_info):
        print('\nService "{0}" found'.format(zc_name))
        print('\tType: {0}'.format(zc_type))

        if zc_info:
            print('\tAddress: {0}:{1}'.format(socket.inet_ntoa(zc_info.address), zc_info.port))
            print('\tServer name: {0}'.format(zc_info.server))

            prop = zc_info.properties
            if prop:
                print('\tProperties:')
                for key, value in prop.items():
                    if not value: continue
                    (key, value) = (key.decode('ascii'), value.decode('ascii'))
                    print('\t\t{0}: {1}'.format(key, value))


def get_ds1000z_results(if_any_return_after=0.8, timeout=10):
    """
    Zeroconf service discovery of "_scpi-raw._tcp.local."
    The results are filtered for entries matching the Rigol DS1000Z scope series.
    """
    zc = Zeroconf()

    def ds1000z_filter(result):
        check_results = [
          re.match(b'DS1\d\d\dZ', result['zc_info'].properties[b'Model']),
          re.match(b'RIGOL TECHNOLOGIES', result['zc_info'].properties[b'Manufacturer']),
        ]
        if not all(check_results):
            return False
            
        return True

    listener = Listener(filter_func=ds1000z_filter)
    browser = ServiceBrowser(zc, '_scpi-raw._tcp.local.', listener=listener)

    start = clock()
    while True:
        # Because multithreading sucks.
        et = clock() - start # elapsed time
        if len(listener.results) and et >= if_any_return_after:
            break
        if et >= timeout:
            break
        time.sleep(0.005)

    zc.close()

    return listener.results


def get_scpi_connection_tuple(http_connection_tuple):
    """
    * Get XML config from http://<address>:<port>/lxi/identification
    * My scope has malformed XML in the namespace attributes, where there is a newline before the closing quote, causing
      the parser to bork. We should just be able to concat the whole string together by removing newlines.
    * Use XPath selector: "ns:Interface[@InterfaceType = 'LXI']/ns:InstrumentAddressString" with the
      "http://www.lxistandard.org/InstrumentIdentification/1.0" namespace.
    * For each InstrumentAddressString, split on "::" and look for an IP address followed by a port
    * My scope yields a VISA type of "INSTR" for both TCPIP interfaces, when technically it should be "SOCKET" I think
      (see: http://zone.ni.com/reference/en-XX/help/371361J-01/lvinstio/visa_resource_name_generic/ and
      http://digital.ni.com/public.nsf/allkb/6A9285AC83C646BA86256BDC004FD4D4)
    * Guessing that an address with no port, or port 80, is the web interface, assume the first one we come across with a
      high-range port is our SCPI interface.
    * By convention this is port 5025, but Rigol has chosen 5555.
    """

    lxi_ident_url = 'http://{0}:{1}/lxi/identification'.format(*http_connection_tuple)

    r = requests.get(lxi_ident_url)

    doc = etree.fromstring(r.content.replace(b'\n', b''))

    scpi_address = None
    scpi_port = None

    for e in doc.xpath("ns:Interface[@InterfaceType = 'LXI']/ns:InstrumentAddressString", namespaces={'ns': 'http://www.lxistandard.org/InstrumentIdentification/1.0'}):
        visa_resource = e.text.split('::')
        interface_type = visa_resource[0]

        if interface_type.startswith('TCPIP'):
            address = visa_resource[1:-1]

            if len(address) == 2 and int(address[1]) > 1024:
                # This is most likely our SCPI address.
                scpi_address = address[0]
                scpi_port = int(address[1])
                break

    return (scpi_address, scpi_port)


def test_scpi(scpi_connection_tuple):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    s.connect(scpi_connection_tuple)
    s.send(b':TRIG:STAT?')
    trig_status = s.recv(32)
    print trig_status
    if trig_status.strip() == b'STOP':
        print('Starting acquisition now...')
        s.send(b':RUN')
    else:
        print('Stoping acquisition now...')
        s.send(b':STOP')
    s.close()

sent = True
def send_scpi(scpi_connection_tuple, command):
    sent = False
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    s.connect(scpi_connection_tuple)
    s.send(command)
    s.close()
    sent = True
    
def receive_scpi(scpi_connection_tuple, command):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    s.connect(scpi_connection_tuple)
    s.send(command)
    trig_status = s.recv(32)
    print trig_status
    s.close()
    return trig_status


units = [
        "zero", "one", "two", "three", "four", "five", "six", "seven", "eight",
        "nine", "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen",
        "sixteen", "seventeen", "eighteen", "nineteen",
      ]

tens = ["", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]

scales = ["hundred", "thousand", "million", "billion", "trillion"]
      
def text2int(textnum, numwords={}):
    if not numwords:
      numwords["and"] = (1, 0)
      for idx, word in enumerate(units):    numwords[word] = (1, idx)
      for idx, word in enumerate(tens):     numwords[word] = (1, idx * 10)
      for idx, word in enumerate(scales):   numwords[word] = (10 ** (idx * 3 or 2), 0)

    current = result = 0
    for word in textnum.split():
        if word not in numwords:
          raise Exception("Illegal word: " + word)

        scale, increment = numwords[word]
        current = current * scale + increment
        if scale > 100:
            result += current
            current = 0

    return result + current

def recready_callback(path, args):
	if args[0]:
		recreadyicon.configure(image = micon)
		recreadyicon.image = micon
	else:
		recreadyicon.configure(image = micoff)
		recreadyicon.image = micoff

def reco_callback(path, args):
	
	#check if not running a scpi command
	if sent:
		words = str(args)
		words = words.split("-")
		myString = " ".join(words )

		#--------------------------------------------------------------------------------------------------------------------
		# RECOGNITION
		if any("resume" in s for s in words):
			speechenabled.set(1)
			text.insert(END, "Speech recognition enabled" + "\n")
		elif any("pause" in s for s in words):
			text.delete("1.0", END)
			text.insert(END, "Speech recognition disabled" + "\n")
			speechenabled.set(0)
		
		if speechenabled.get():
			
			text.delete("1.0", END)
			text.insert(END, str(myString[2:-2]) + "\n")
			
			for result in results:
				print('Trying to connect to {}...'.format(socket.inet_ntoa(result['zc_info'].address)))
				scpi_connection = get_scpi_connection_tuple((socket.inet_ntoa(result['zc_info'].address), result['zc_info'].port))
				
				if scpi_connection is not (None, None):
				
					#--------------------------------------------------------------------------------------------------------------------
					# GENERIC
					if len(words) == 2:
						if words[0] == "['autoscale":
							scpi_cmd = ":AUT"
							text.insert(END, str(scpi_cmd) + "\n")
							send_scpi(scpi_connection, scpi_cmd)
						elif words[0] == "['clear":
							scpi_cmd = ":CLE"
							text.insert(END, str(scpi_cmd) + "\n")
							send_scpi(scpi_connection, scpi_cmd)
							scpi_cmd = ":MEASure:COUNter:SOURce OFF"
							send_scpi(scpi_connection, scpi_cmd)
						elif words[0] == "['run":
							scpi_cmd = ":RUN"
							text.insert(END, str(scpi_cmd) + "\n")
							send_scpi(scpi_connection, scpi_cmd)
						elif words[0] == "['stop":
							scpi_cmd = ":STOP"
							text.insert(END, str(scpi_cmd) + "\n")
							send_scpi(scpi_connection, scpi_cmd)
					
					#--------------------------------------------------------------------------------------------------------------------
					# TIME
					if any("time" in s for s in words):
						if any("scale" in s for s in words):
							#:TIMebase:MAIN:SCALe
							if len(words) == 5:
								if words[3] == "s":
									scpi_cmd = ":TIMebase:MAIN:SCALe "+str(float(float(text2int(words[2])) / 1))
								elif words[3] == "m":
									scpi_cmd = ":TIMebase:MAIN:SCALe "+str(float(float(text2int(words[2])) / 1000))
								elif words[3] == "u":
									scpi_cmd = ":TIMebase:MAIN:SCALe "+str(float(float(text2int(words[2])) / 1000000))
							else:
								if words[4] == "s":
									scpi_cmd = ":TIMebase:MAIN:SCALe "+str(float(float(text2int(words[2] + " " + words[3])) / 1))
								elif words[4] == "m":
									scpi_cmd = ":TIMebase:MAIN:SCALe "+str(float(float(text2int(words[2] + " " + words[3])) / 1000))
								elif words[4] == "u":
									scpi_cmd = ":TIMebase:MAIN:SCALe "+str(float(float(text2int(words[2] + " " + words[3])) / 1000000))
							
							text.insert(END, str(scpi_cmd) + "\n")
							send_scpi(scpi_connection, scpi_cmd)	
							
					#--------------------------------------------------------------------------------------------------------------------
					# FREQUENCY COUNTER
					if any("counter" in s for s in words):
						if any("show" in s for s in words):
							scpi_cmd = ":MEASure:COUNter:SOURce CHANnel"+str(text2int(words[3]))
							send_scpi(scpi_connection, scpi_cmd)
							time.sleep(2)
							rs = receive_scpi(scpi_connection, ":MEASure:COUNter:VALue?")
							textb.delete("1.0", END)
							t = str(float(rs)) + " hertz"
							textb.insert(END, t)
							if ttsenabled.get():
								thread.start_new_thread(tts, (t,))
							
					#--------------------------------------------------------------------------------------------------------------------
					# TRIGGER
					if any("trigger" in s for s in words):
						if any("level" in s for s in words):
							if len(words) == 6:
								if words[4] == "v":
									scpi_cmd = ":TRIG:EDG:LEV "+str(float(float(text2int(words[2] + " " + words[3])) / 1))
								else:
									scpi_cmd = ":TRIG:EDG:LEV "+str(float(float(text2int(words[2] + " " + words[3])) / 1000))
							else:
								if words[3] == "v":
									scpi_cmd = ":TRIG:EDG:LEV "+str(float(float(text2int(words[2])) / 1))
								else:
									scpi_cmd = ":TRIG:EDG:LEV "+str(float(float(text2int(words[2])) / 1000))
							text.insert(END, str(scpi_cmd) + "\n")
							send_scpi(scpi_connection, scpi_cmd)
							
						else:
							if any("single" in s for s in words):
								scpi_cmd = ":SINGle"
								text.insert(END, str(scpi_cmd) + "\n")
								send_scpi(scpi_connection, scpi_cmd)
							elif any("force" in s for s in words):
								scpi_cmd = ":TFORce"
								text.insert(END, str(scpi_cmd) + "\n")
								send_scpi(scpi_connection, scpi_cmd)
					
					#--------------------------------------------------------------------------------------------------------------------
					# CHANNEL
					if any("channel" in s for s in words):
						if any("coupling" in s for s in words):
							#CO: COUPLING CHANNEL NUM ACDC
							#:CHAN1:COUP AC
							scpi_cmd = ":CHAN"+str(text2int(words[2]))+":COUP "+words[3].upper()
							text.insert(END, str(scpi_cmd) + "\n")
							send_scpi(scpi_connection, scpi_cmd)
						if any("scale" in s for s in words):
							#:CHANnel<n>:SCALe
							if len(words) == 6:
								if words[4] == "v":
									scpi_cmd = ":CHAN"+str(text2int(words[1]))+":SCALe "+str(float(float(text2int(words[3])) / 1))
								else:
									scpi_cmd = ":CHAN"+str(text2int(words[1]))+":SCALe "+str(float(float(text2int(words[3])) / 1000))
							else:
								if words[5] == "v":
									scpi_cmd = ":CHAN"+str(text2int(words[1]))+":SCALe "+str(float(float(text2int(words[3] + " " + words[4])) / 1))
								else:
									scpi_cmd = ":CHAN"+str(text2int(words[1]))+":SCALe "+str(float(float(text2int(words[3] + " " + words[4])) / 1000))
							text.insert(END, str(scpi_cmd) + "\n")
							send_scpi(scpi_connection, scpi_cmd)
						else:
							#:CHANnel1:DISPlay ON
							scpi_cmd = ":CHAN"+str(text2int(words[1]))+":DISP "+words[2].upper()
							text.insert(END, str(scpi_cmd) + "\n")
							send_scpi(scpi_connection, scpi_cmd)
					
    
    
results = get_ds1000z_results()

def tts(t):
	v.speak(t)
	
def task():
    server.recv(100)
    top.after(50, task)

def quit():
	os.system("killall speechreco")
	top.destroy()
	sys.exit()


def key(event):
	if speechenabled.get():
		speechenabled.set(0)
	else:
		speechenabled.set(1)
		

def genericpop():
   tkMessageBox.showinfo("Generic", "run\nstop\nautoscale\nclear")

def chpop():
   tkMessageBox.showinfo("Channel", "channel one off/on\ncoupling channel two ac/dc")
       
def triggerpop():
   tkMessageBox.showinfo("Channel", "single trigger\nforce trigger\ntrigger level 160 millivolt")
              
              
       
def helppop():
   tkMessageBox.showinfo("Speech2SCPI", "You need a microphone an oscilloscope that is connected on the same network as your computer (this program is using zeroconf to automagically find your scope IP / PORT).\n\nThen you can start speaking some commands (ie: channel one off).\n\nCoded by Patrick Coulombe from http://www.workinprogress.ca")
       
def main():

    if not results:
		print "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
		print "Didn't find any Rigol DS1000Z scope series"
		print "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
		top.destroy()
		sys.exit()
		
    for result in results:
        Listener.pprint(**result)
        print()

	os.system("./speechreco -C speechreco.conf &")
	server.add_method("/reco", 's', reco_callback)
	server.add_method("/recready", 'i', recready_callback)
	
	top.wm_title("Speech2SCPI")
	top.resizable(width=FALSE, height=FALSE)
	top.minsize(width=780, height=240)
	#Button(top, text="Quit", command=quit).pack()
	top.bind("<space>", key)
	menubar = Menu(top)
	menubar.add_command(label="Generic", command=genericpop)
	menubar.add_command(label="Channel", command=chpop)
	menubar.add_command(label="Trigger", command=triggerpop)
	menubar.add_command(label="Help", command=helppop)
	menubar.add_command(label="Quit", command=quit)
	top.config(menu=menubar)
    
    while True:
			top.after(1, task)
			top.mainloop()

if __name__ == '__main__':
    main()
