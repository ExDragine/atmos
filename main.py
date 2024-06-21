import os
import datetime

from PIL import Image, ImageFont, ImageDraw

from interface.ICM20948 import ICM20948  # Gyroscope/Acceleration/Magnetometer
from interface.BME280 import BME280  # Atmospheric Pressure/Temperature and humidity
from interface.LTR390 import LTR390  # UV
from interface.TSL2591 import TSL2591  # LIGHT
from interface.SGP40 import SGP40  # Gas
from lib import epd2in13b_V4

picdir = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'pic')
fontdir = os.path.join(os.path.dirname(os.path.dirname((os.path.realpath(__file__)))), 'font')
libdir = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'lib')


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
        self.pressure = round(bme[0], 2)
        self.temp = round(bme[1], 2)
        self.hum = round(bme[2], 2)
        self.lux = round(self.light.Lux(), 2)
        self.uv = self.uv.UVS()
        self.gas = round(self.sgp.raw(), 2)
        self.roll, self.pitch, self.yaw = round(icm[0], 2), round(icm[1], 2), round(icm[2], 2)
        self.acceleration = (icm[3], icm[4], icm[5])
        self.gyroscope = (icm[6], icm[7], icm[8])
        self.magnetic = (icm[9], icm[10], icm[11])

    def photo(self):
        os.makedirs("./img", exist_ok=True)
        file_name = datetime.datetime.now().strftime("%H-%M-%S")
        # if night:
        #     os.system("libcamera-still --nopreview --shutter 6000000 --rotation 180 --ev 0.5 --metering centre -o ./data/photo/{file_name}.jpg")
        os.system(f"libcamera-still --nopreview --rotation 180 --metering centre -o ./data/photo/{file_name}.jpg")
        if len(os.listdir("./data/photo")) > 288:
            file_list = os.listdir("./data/photo")
            file_list.sort(key=lambda x: os.path.getmtime(os.path.join("./data/photo", x)))
            os.remove(os.path.join("./data/photo", file_list[0]))


class Display:
    def __init__(self) -> None:
        self.epd = epd2in13b_V4.EPD()
        self.font = ImageFont.truetype(os.path.join(fontdir, 'Font.ttc'), 5)
        self.sensor = OnBoardSensor()
        self.epd.init()
        self.epd.clear()
        self.epd.sleep()

    def basic(self):
        self.epd.init()
        HBlackimage = Image.new("1", (self.epd.height, self.epd.width), 255)  # 250*122
        Redimage = Image.new("1", (self.epd.height, self.epd.width), 255)
        drawblack = ImageDraw.Draw(HBlackimage)
        drawred = ImageDraw.Draw(Redimage)
        drawblack.text((5, 0), text=f"温度: {self.sensor.temp}", font=self.font, fill=0)
        drawblack.text((5, 20), text=f"湿度: {self.sensor.hum}", font=self.font, fill=0)
        drawblack.text((5, 40), text=f"气压: {self.sensor.pressure}", font=self.font, fill=0)
        drawblack.text((5, 80), text=f"光照: {self.sensor.light}", font=self.font, fill=0)
        drawblack.text((5, 100), text=f"紫外: {self.sensor.uv}", font=self.font, fill=0)
        drawblack.text((130, 0), text=f"乙醇: {self.sensor.gas}", font=self.font, fill=0)
        drawblack.text((130, 20), text=f"姿态: Roll = {self.sensor.roll} Pitch = {self.sensor.pitch} Yaw = {self.sensor.yaw}", font=self.font, fill=0)
        drawblack.text(
            (130, 40),
            text=f"加速度: X= {self.sensor.acceleration[0]} Y = {self.sensor.acceleration[1]} Z = {self.sensor.acceleration[2]}",
            font=self.font,
            fill=0,
        )
        drawblack.text(
            (130, 60),
            text=f"陀螺仪: X= {self.sensor.gyroscope[0]} Y = {self.sensor.gyroscope[1]} Z = {self.sensor.gyroscope[2]}",
            font=self.font,
            fill=0,
        )
        drawblack.text(
            (130, 80),
            text=f"磁力计: X= {self.sensor.magnetic[0]} Y = {self.sensor.magnetic[1]} Z = {self.sensor.magnetic[2]}",
            font=self.font,
            fill=0,
        )
        drawred.line((125, 0, 125, 0), fill=0)
        HBlackimage = HBlackimage.rotate(180)
        self.epd.display(self.epd.getbuffer(HBlackimage), self.epd.getbuffer(Redimage))
        self.epd.sleep()


if __name__ == '__main__':
    display = Display()
    display.basic()
    exit()
