# octopusLAB solar regulator 
# The MIT License (MIT)
# Copyright (c) 2017-2020 Jan Copak, Petr Kracik, Vasek Chalupnicek
"""
main lib: github.com/octopusengine/octopuslab/tree/master/esp32-micropython
ampy -p /COM6 put _projects/solar2/solar2.py main.py
"""
_ver = "v0.3 - 28.4.2020"

from time import sleep
from util.pinout import set_pinout
from util.rgb import Rgb
from util.button import Button
from util.analog import Analog
from util.iot import Relay
from util.octopus import w, disp7_init
from machine import Pin, Timer
# from machine import RTC
from config import Config
from util.database.influxdb import InfluxDB
from gc import mem_free

errorcount = 0
powerMode = False

print("octopusLab solar regulator: ", _ver)

# --- init ---
print("--- init --- RAM free: " + str(mem_free()))
pinout = set_pinout()
ws = Rgb(pinout.WS_LED_PIN,1)

led_button = Button(0, release_value=1)
built_in_led = Pin(2, Pin.OUT)

anB = Analog(36)  # Battery
anS = Analog(39)  # Solar

re1 = Relay(pinout.PWM1_PIN)
re2 = Relay(pinout.PWM2_PIN)
re1.value(1) # inverse
re2.value(1)


def batt_adc():
    valB =  anB.get_adc_aver(8)
    print(valB)
    d7.show(valB)
    sleep(1)
    d7.show("")


def solar_adc(d7show = True):
    global powerMode
    valS1 =  anS.get_adc_aver(8)
    print(valS1)
    if d7show:
        d7.show(valS1)
        sleep(1)
        d7.show("")

    # if powerMode:
    if valS1 > 2000: # firstLimit 
        re1.value(0) # on
        sleep(1)
        valS2 =  anS.get_adc_aver(8)
        print(valS2)
        if d7show: d7.show(valS2)
        re1.value(1) # off
        sleep(1)
        d7.show("")
        sleep(1)
        if valS2 > treshold:
            re2.value(0)
            powerMode = True
        else:
            re2.value(1)
            powerMode = False
        print("powerMode: ", powerMode)

    else: 
        valS2 = 0
        re1.value(0)
        powerMode = False

    valSdiff = valS1 - valS2
    if d7show: d7.show(valSdiff)

    send_solar(valS1, valS2)

    if valSdiff < treshold:
        ws.color((0,128,0))
    else:
        ws.color((128,0,0))
    sleep(1)
    ws.color((0,0,0))
    d7.show("")
    sleep(1)


def wait_connect():
    retry = 0
    print("Connecing")
    while not net.sta_if.isconnected():
        print(".")
        retry += 1
        time.sleep(1)

        if retry > 30:
            break


def reconect():
    global errorcount
    errorcount+=1
    if errorcount > 4:
        machine.reset()
    else:
        net.sta_if.disconnect()
        net.sta_if.connect()
        wait_connect()


def bmp_init():
   from util.octopus import i2c_init
   # "-1" > SW for old lib:
   i2c = i2c_init(1,100000,-1)

   from bmp280 import BMP280

   bmp = BMP280(i2c)
   return bmp


def send_boot():
    try:
        print("influx.write: start_boot")
        influx.write("octopuslab", start_boot = 1)
    except Exception as e:
        print("influx send_bme Exception: {0}".format(e))


def send_bmp():
    temp = bmp.temperature
    press = bmp.pressure
    
    try:
        print("influx.write: ", temp, press)
        influx.write("octopuslab", temperature = temp, pressure= press)
    except Exception as e:
        print("influx send_bme Exception: {0}".format(e))
        reconect()


def send_solar(s20=0,s21=0):
    try:
        print("influx.write: ", s20, s21)
        influx.write("octopuslab", solar20 = s20, solar21 = s21)
    except Exception as e:
        print("influx send_solar Exception: {0}".format(e))
        reconect()


minute = 1 # 10
it = 0 # every 10 sec.
def timer10s():
    global it
    it = it + 1
    print(">" + str(it))

    if (it == 6*timer_interval): # 6 = 1min / 60 = 10min
        print("ok --- 10 min")
        solar_adc(False)
        show_temp()
        send_bmp()
        it = 0


def timer_init():
    print("timer init > stop: tim1.deinit()")
    tim1.init(period=10000, mode=Timer.PERIODIC, callback=lambda t:timer10s())


def show_temp():
    t = bmp.temperature
    print(t)
    d7.show(str(t)+"c")
    sleep(2)
    d7.show("")
    return t


@led_button.on_press
def on_press_top_button():
    print("on_press_top_button")
    solar_adc()
    show_temp()


print("config/solar.json -->")
config = Config("solar2") # = config/solar.json
try:
    timer_interval = config.get("timer_interval") # minutes
    treshold = config.get("treshold") # RAW adc difference
    print("setup: ", timer_interval, treshold)
    iurl = config.get("influx_url")
    idb = config.get("influx_db")
    iusr = config.get("influx_usr")
    ipsw = config.get("influx_psw")
    influx = InfluxDB(iurl, idb, iusr, ipsw, "solar2", place="lab")
    print("influx: ", iurl, idb)
except Exception as e:
    print("config Exception: {0}".format(e))


# --- test ---
print("--- test --- RAM free: " + str(mem_free()))
print("test: led")
built_in_led.on()
sleep(1)
built_in_led.off()

print("test: RGB led")
ws.simpleTest()

print("test: display 7 digit")
d7 = disp7_init()
sleep(2)
d7.show("")

print("test: bmp")
bmp = bmp_init()
temp = show_temp()
net = w()
send_boot()
send_bmp()
solar_adc()

# rtc = RTC() # real time
tim1 = Timer(0)     # for main 10 sec timer
timer_init()


# --- run ---
print("--- run --- RAM free: " + str(mem_free()))
