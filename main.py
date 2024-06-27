import math
import os
import datetime

from astral import LocationInfo
from astral.sun import sun
from PIL import Image, ImageFont, ImageDraw
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.schedulers.blocking import BlockingScheduler

from function.sql import Database
from interface.ICM20948 import ICM20948  # Gyroscope/Acceleration/Magnetometer
from interface.BME280 import BME280  # Atmospheric Pressure/Temperature and humidity
from interface.LTR390 import LTR390  # UV
from interface.TSL2591 import TSL2591  # LIGHT
from interface.SGP40 import SGP40  # Gas
from lib import epd2in13b_V4

picdir = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), "pic")
fontdir = os.path.join(os.path.dirname(os.path.dirname((os.path.realpath(__file__)))), "font")
libdir = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), "lib")


def photo():
    os.makedirs("./img", exist_ok=True)
    file_name = datetime.datetime.now().strftime("%H-%M-%S")
    today = datetime.datetime.today()
    city = LocationInfo("guangzhou", "China", "Asia/Harbin", 23.109866, 113.2683)
    s = sun(city.observer, date=datetime.date(today.year, today.month, today.day), tzinfo=city.timezone)

    sunrise = int((s["sunrise"] + datetime.timedelta(minutes=-20)).timestamp())
    sunset = int((s["sunset"] + datetime.timedelta(minutes=20)).timestamp())
    if int(datetime.datetime.now().timestamp()) > sunset or int(datetime.datetime.now().timestamp()) < sunrise:
        os.system(f"libcamera-still --nopreview --shutter 6000000 --rotation 180 --ev 0.5 --metering centre --awb daylight -o ./img/{file_name}.jpg")
    else:
        os.system(f"libcamera-still --nopreview --rotation 180 --metering centre --awb daylight -o ./img/{file_name}.jpg")
    if len(os.listdir("./img")) > 288:
        file_list = os.listdir("./data/photo")
        file_list.sort(key=lambda x: os.path.getmtime(os.path.join("./img", x)))
        os.remove(os.path.join("./img", file_list[0]))


class OnBoardSensor:
    def __init__(self) -> None:
        self.icm = ICM20948()
        self.bme = BME280()
        self.bme.get_calib_param()
        self.uv = LTR390()
        self.light = TSL2591()
        self.sgp = SGP40()

    def information(self):
        print("TSL2591 Light I2C address:0X29")
        print("LTR390 UV I2C address:0X53")
        print("SGP40 VOC I2C address:0X59")
        print("icm20948 9-DOF I2C address:0X68")
        print("bme280 T&H I2C address:0X76")

    def read(self):
        bme = self.bme.readData()
        icm = self.icm.getdata()
        bme = self.bme.readData()
        icm = self.icm.getdata()
        self.pressure = round(bme[0], 2)
        self.temp = round(bme[1], 2)
        self.hum = round(bme[2], 2)
        self.lux = round(self.light.Lux(), 2)
        self.uvs = self.uv.UVS()
        self.gas = round(self.sgp.measureRaw(int(self.temp), int(self.hum)), 2)
        self.roll, self.pitch, self.yaw = round(icm[0], 2), round(icm[1], 2), round(icm[2], 2)
        self.acceleration = (round(icm[3]), round(icm[4]), round(icm[5]))
        self.gyroscope = (round(icm[6]), round(icm[7]), round(icm[8]))
        self.magnetic = (round(icm[9]), round(icm[10]), round(icm[11]))
        data = (
            [self.temp, self.hum, self.pressure, self.lux, self.uvs, self.gas, self.roll, self.pitch, self.yaw]
            + list(self.acceleration)
            + list(self.gyroscope)
            + list(self.magnetic)
        )
        # shake = math.sqrt(int(pow(int(self.acceleration[0]), 2)) + int(pow(int(self.acceleration[1]), 2)) + int(pow(int(self.acceleration[2]), 2)))
        shake = round(math.sqrt(pow(self.roll, 2) + pow(self.pitch, 2) + pow(self.yaw, 2)), 4)
        _ = shake
        database.insert(data)


class Display:
    def __init__(self) -> None:
        self.epd = epd2in13b_V4.EPD()
        self.font = ImageFont.truetype("./font/Minecraft.ttf", 16)
        self.sensor = OnBoardSensor()

    def basic(self):
        self.sensor.read()
        self.epd.init()
        HBlackimage = Image.new("1", (self.epd.height, self.epd.width), 255)  # 250*122
        Redimage = Image.new("1", (self.epd.height, self.epd.width), 255)
        drawblack = ImageDraw.Draw(HBlackimage)
        drawred = ImageDraw.Draw(Redimage)
        drawblack.text((5, 5), text=f"温度 {self.sensor.temp}", font=self.font, fill=0)
        drawblack.text((5, 25), text=f"湿度 {self.sensor.hum}", font=self.font, fill=0)
        drawblack.text((5, 45), text=f"气压 {self.sensor.pressure}", font=self.font, fill=0)
        drawblack.text((5, 65), text=f"光照 {self.sensor.lux}", font=self.font, fill=0)
        drawblack.text((5, 85), text=f"紫外 {self.sensor.uvs}", font=self.font, fill=0)
        drawblack.text((5, 105), text=f"乙醇 {self.sensor.gas}", font=self.font, fill=0)
        drawred.line((108, 0, 108, 0), fill=0)
        drawred.line((109, 0, 109, 0), fill=0)
        HBlackimage = HBlackimage.rotate(180)
        self.epd.display(self.epd.getbuffer(HBlackimage), self.epd.getbuffer(Redimage))
        self.epd.sleep()


if __name__ == "__main__":
    display = Display()
    database = Database("record.db")

    if not os.path.exists("disk.db"):
        database.init()
    try:
        background_scheduler = BackgroundScheduler()
        background_scheduler.add_job(photo, "interval", seconds=60)
        background_scheduler.start()
        block_scheduler = BlockingScheduler()
        block_scheduler.add_job(display.basic, "interval", seconds=60)
        block_scheduler.start()
    except KeyboardInterrupt:
        display.epd.sleep()
        database.close()
