# main.py -- put your code here!
#
# Hardware requirement:
# 1. WiPy 3.0
# 2. Expansion Board 2.0
#
# Program Description:
# Check door status (open or close) and publish it to Adafruit IO

from network import WLAN      # For operation of WiFi network
import time                   # Allows use of time.sleep() for delays
import pycom                  # Base library for Pycom devices
from umqtt import MQTTClient  # For use of MQTT protocol to talk to Adafruit IO
import ubinascii              # Needed to run any MicroPython code
import machine                # Interfaces with hardware components
import micropython            # Needed to run any MicroPython code
from machine import Pin

# Wireless network
WIFI_SSID = "WIFI_SSID" # put your WIFI name here
WIFI_PASS = "WIFI_PASSWORD" # put your WIFI password here

# Adafruit IO (AIO) configuration
AIO_SERVER = "io.adafruit.com"
AIO_PORT = 1883
AIO_USER = "AIO_USER" # put your AIO USER here
AIO_KEY = "AIO_KEY" # put your AIO KEY here
AIO_CLIENT_ID = ubinascii.hexlify(machine.unique_id())  # Can be anything

AIO_CHART_FEED = "iprayudi/feeds/system-status"
AIO_RESET_FEED = "iprayudi/feeds/reset-button"
AIO_STATUS_FEED = "iprayudi/feeds/status-button"

# Global variables
curr_state = "CLOSE"
next_state = "OPEN"

print("PROGRAM: DOOR CHECK")

pycom.heartbeat(False)
time.sleep(0.1) # Workaround for a bug.
                # Above line is not actioned if another
                # process occurs immediately afterwards
pycom.rgbled(0x220000)  # Status red = not working

# Connecting to WIFI
wlan = WLAN(mode=WLAN.STA)
wlan.connect(WIFI_SSID, auth=(WLAN.WPA2, WIFI_PASS), timeout=5000)

print("Connecting to: " + WIFI_SSID)
while not wlan.isconnected():    # Code waits here until WiFi connects
    machine.idle()

print("Connected to Wifi")
pycom.rgbled(0x000022) # Status blue

def check_door(p):
    global curr_state
    global next_state
    send_msg = -1

    if (p.value() == 1): # check if door is open
        next_state = "OPEN"
        if (next_state != curr_state):
            curr_state = next_state
            send_msg = 100
    else: # door is close
        next_state = "CLOSE"
        if (next_state != curr_state):
            curr_state = next_state
            send_msg = 0

    if (send_msg != -1):
        try:
            # client.publish(topic=AIO_CHART_FEED, msg=str(send_msg))
            client.publish(topic=AIO_CHART_FEED, msg=curr_state) # publish door status to AIO
            print("DOOR: " + curr_state)
        except:
            print("Publishing: FAILED")
        finally:
            print("Publishing: SUCCESS")

# Function to respond to messages from Adafruit IO
def sub_cb(topic, msg):          # sub_cb means "callback subroutine"
    # print((topic, msg))          # print out the message that was received. Debugging use.
    if (topic.decode("utf-8") == AIO_RESET_FEED): # check if it is reset button
        if msg == b'1':             # If pressed
            print('System reboot')
            client.publish(topic=AIO_CHART_FEED, msg="System reboot in 2sec")
            time.sleep(2)
            machine.reset()
    elif (topic.decode("utf-8") == AIO_STATUS_FEED): # check if it is status button
        if msg == b'1':             # If pressed
            print('System alive')
            pycom.rgbled(0x000022) # Status blue
            time.sleep(2)
            client.publish(topic=AIO_CHART_FEED, msg="System alive")
            client.publish(topic=AIO_CHART_FEED, msg=curr_state)
            pycom.rgbled(0x002200) # Status green

# Use the MQTT protocol to connect to Adafruit IO
print("Connecting to IO-Adafruit")
client = MQTTClient(AIO_CLIENT_ID, AIO_SERVER, AIO_PORT, AIO_USER, AIO_KEY)

client.set_callback(sub_cb) # set callback function
client.connect() # connect to AIO
client.subscribe(AIO_RESET_FEED) # subscribe to reset button feed
client.subscribe(AIO_STATUS_FEED) # subscribe to status button feed

print("Connected to IO-Adafruit. Client ID: %s" % AIO_CLIENT_ID)
pycom.rgbled(0x002200) # Status green

# Pin declaration
p_in = Pin('P11', mode=Pin.IN, pull=Pin.PULL_UP)
print("Door is connected to %s" % p_in.id())

# main loop
try:
    print("Entering main loop ... ")
    client.publish(topic=AIO_CHART_FEED, msg="WiPy is connected")
    while 1:
        client.check_msg()
        check_door(p_in)
        time.sleep(0.1) # delay to avoid debouncing
except KeyboardInterrupt:
    print("Key pressed. Program exiting ... ")
finally:                  # If an exception is thrown ...
    client.disconnect()   # ... disconnect the client and clean up.
    client = None
    wlan.disconnect()
    wlan = None
    pycom.rgbled(0x222200) # Status red: stopped
    print("Disconnected from: " + WIFI_SSID)
    print("End of program")
