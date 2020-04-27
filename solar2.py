# octopusLAB solar regulator v0.21 - 25.4.2020
# The MIT License (MIT)
# Copyright (c) 2017-2020 Jan Copak, Petr Kracik, Vasek Chalupnicek
"""
main lib: github.com/octopusengine/octopuslab/tree/master/esp32-micropython
ampy -p /COM6 put _projects/solar2/solar2.py main.py
"""

from time import sleep
from util.pinout import set_pinout
from util.rgb import Rgb
from util.button import Button
from util.octopus import disp7_init
from util.analog import Analog
from util.iot import Relay
from util.octopus import w
from machine import Pin, RTC, Timer
from config import Config
from util.database.influxdb import InfluxDB
from gc import mem_free


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


def solar_adc():
    valS1 =  anS.get_adc_aver(8)
    print(valS1)
    d7.show(valS1)
    sleep(1)
    d7.show("")

    re1.value(0) # on
    sleep(1)
    valS2 =  anS.get_adc_aver(8)
    print(valS2)
    d7.show(valS2)
    re1.value(1) # off
    sleep(1)
    d7.show("")
    sleep(1)

    valSdiff = valS1 - valS2
    d7.show(valSdiff)

    if valSdiff < treshold:
        ws.color((0,128,0))
    else:
        ws.color((128,0,0))
    sleep(1)
    ws.color((0,0,0))
    d7.show("")
    sleep(1)


def bmp_init():
   from util.octopus import i2c_init
   # "-1" > SW for old lib:
   i2c = i2c_init(1,100000,-1)

   from bmp280 import BMP280

   bmp = BMP280(i2c)
   return bmp


minute = 1 # 10
it = 0 # every 10 sec.
def timer10s():
    global it
    it = it + 1
    print(">" + str(it))

    if (it == 6*timer_interval): # 6 = 1min / 60 = 10min
        print("ok ------------------- 10 min")
        solar_adc()
        show_temp()
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
press = bmp.pressure

w()
try:
   print("test influx.write: ", temp, press)
   influx.write("octopuslab", temperature = temp, pressure= press, solar20 = 123, solar21 = 123, solarBar = 0)
except Exception as e:
    print("influx test Exception: {0}".format(e))


post_url="https://parallelgarden.surikata.info:8086/write?db=octopuslab&u=octopus&p=chobotni4ky"
post_data="solar,place=octopuslab,id=1 keepalive={0},solarVolt={1}"


# rtc = RTC() # real time
tim1 = Timer(0)     # for main 10 sec timer
timer_init()


# --- run ---
print("--- run --- RAM free: " + str(mem_free()))
