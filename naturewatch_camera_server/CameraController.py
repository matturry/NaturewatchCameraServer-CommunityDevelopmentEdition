import threading
import cv2
import imutils
import time
import logging
import io
import numpy as np
import os
import enum
import datetime as dt
import subprocess
from bisect import bisect_left

from .driver.Interface import LEDState, ImageResolution

class CameraController(threading.Thread):
    def __init__(self, logger, driver, config):
        threading.Thread.__init__(self)
        self._stop_event = threading.Event()
        self.cancelled = False

        self.logger = logger
        self.config = config
        self.driver = driver

        self.driver.initialise_camera(config)

        # For photos
        self.picamera_photo_stream = None

        # Define the font style for the timestamps
        self.timestamp_format = {
            ImageResolution.LORES: {
                'color': (255, 255, 255),
                'bgcolor': (0, 0, 0),
                'text_box': [(0, 8), (115, 8)],
                'font': cv2.FONT_HERSHEY_PLAIN,
                'font_size': 0.6,
                'font_thickness': 1
            },
            ImageResolution.HIRES: {
                'color': (255, 255, 255),
                'bgcolor': (0, 0, 0),
                'text_box': [(0, 28), (390, 35)],
                'font': cv2.FONT_HERSHEY_SIMPLEX,
                'font_size': 1,
                'font_thickness': 2
            }
        }

        # We use a pre_callback function to add the timestamp to images and videos recorded.
        if self.config['timestamp'] == "on":
            self.driver.set_preprocess_callback(self.apply_timestamp)
      
        self.image = None
        self.yuvimage = None
        self.recording_active = False
        
    # Main routine, sits in a loop capturing an image and storing it
    def run(self):
        while not self.is_stopped():
            try:
                # Get image from Pi camera
                self.yuvimage = self.driver.get_yuv_image(ImageResolution.LORES)
                self.image = cv2.cvtColor(self.yuvimage, cv2.COLOR_YUV420p2RGB)
                if self.image is None:
                    self.logger.warning("CameraController: got empty image.")
                # While recording we do not need to check for motion, so we only
                # update this loop every 1s to update the web feed
                if self.recording_active is False:
                    time.sleep(0.03)
                else:
                    time.sleep(1)
            except KeyboardInterrupt:
                self.logger.info("CameraController: interrupted...")
                break
            except Exception as e:
                self.logger.error("CameraController: driver error, reinitialising.")
                self.logger.exception(e)
                self.driver.initialise_camera(self.config)
                time.sleep(0.02)

    # Callback to apply a datestamp to saved images and videos, this is called
    # by the driver before the image/video is returned.
    def apply_timestamp(self, array, res):
        timestamp = time.strftime("%d/%m/%Y %H:%M:%S")
        assert res in [ImageResolution.HIRES, ImageResolution.LORES]
        config = self.timestamp_format[res]
        cv2.rectangle(
            m.array, config['text_box'][0], config['text_box'][1],
            config['bgcolor'], -1
        )
        cv2.putText(
            m.array, timestamp, (0, 0), config['font'],
            config['font_size'], config['color'], config['font_thickness'])
  
    # Stop thread
    def stop(self):
        self.logger.info('CameraController: stopping ...')
        self._stop_event.set()
        self.driver.stop()

    # Check if thread is stopped
    def is_stopped(self):
        return self._stop_event.is_set()

    def get_md_yuvimage(self):
        if self.yuvimage is not None:
            return self.yuvimage.copy()

    def get_md_image(self):
        if self.image is not None:
            return self.image.copy()

    def get_image_binary(self):
        _, buf = cv2.imencode(".jpg", self.get_md_image())
        return buf

    # Start saving contents of circular video buffer to disk
    def start_saving_video(self, output_video):
        self.driver.start_video_capture(output_video)

    # Stop saving contents of circular video buffer to disk
    def stop_saving_video(self):
        self.driver.stop_video_capture()

    def start_video_stream(self):
        self.driver.start_video_buffer()

    def stop_video_stream(self):
        self.driver.stop_video_buffer()

    def wait_recording(self, delay):
        time.sleep(delay)

    def get_hires_image(self):
        self.logger.debug("CameraController: hires image requested.")
        return cv2.cvtColor(
            self.driver.get_yuv_image(ImageResolution.HIRES), cv2.COLOR_YUV420p2RGB
        )

    def run_autofocus(self):
        self.driver.autofocus()

    def set_camera_rotation(self, rotation):
        if (self.config["rotate_camera"] == 1) != rotation:
            self.config["rotate_camera"] = 1 if rotation else 0
            # changing rotation involves stoppping and starting the camera again,
            # might as well just reinitialise
            self.driver.initialise_camera(self.config)
            self.config.flush()

    # Set picamera exposure
    def set_exposure(self, ExposureTime, AnalogueGain):
        self.config["shutter_speed"] = ExposureTime
        self.config["analogue_gain"] = AnalogueGain
        self.config["exposure_mode"] = "off"
        self.driver.set_exposure(ExposureMode.MANUAL, ExposureTime, AnalogueGain)
        self.config.flush()

    def get_exposure_mode(self):
        self.logger.debug('Exposure mode is set to: %s', self.config["exposure_mode"])
        return self.config["exposure_mode"]

    def get_exposure_settings(self):
        settings = self.driver.get_exposure_settings()
        ExpList = [250, 313, 400, 500, 625, 800, 1000, 1250,
                   1563, 2000, 2500, 3125, 4000, 5000, 6250,
                   8000, 10000, 12500, 16666, 20000, 25000,
                   33333]
        exposure_value = self.find_closest_exposure(ExpList, settings['shutter_speed'])
        settings['shutter_speed'] = exposure_value
        settings['mode'] = settings['mode'].value
        return settings

    def find_closest_exposure(self, ExpList, ExpValue):
        """
        If two numbers are equally close, return the smallest number.
        """
        pos = bisect_left(ExpList, ExpValue)
        if pos == 0:
            return ExpList[0]
        if pos == len(ExpList):
            return ExpList[-1]
        before = ExpList[pos - 1]
        after = ExpList[pos]
        if after - ExpValue < ExpValue - before:
            return after
        else:
            return before

    def auto_exposure(self):
        self.config["exposure_mode"] = "auto"
        self.driver.set_exposure(ExposureMode.AUTO)
        self.config.flush()

    # Set camera resolution
    def set_resolution(self, resolution):
        if resolution != self.config["resolution"]:
            assert resolution in ["1640x1232", "1920x1080"]
            self.config["resolution"] = resolution
            width, height = resolution.split('x', 1)
            self.config["img_height"] = int(height)
            self.config["img_width"] = int(width)
            self.driver.initialise_camera(self.config)
            self.config.flush()

    # Set LED output
    def set_LED(self, LED):
        if self.config["LED"] != LED:
            if LED == "off":
                self.driver.configure_LED(LEDState.OFF)
                self.config["LED"] = "off"
                self.config.flush()
            else:
                self.driver.configure_LED(LEDState.ON)
                self.config["LED"] = "on"
                self.config.flush()

    # Synchronise time with client
    def set_Time(self, clienttime):
        self.logger.info('CameraController: Synchronising time with client')
        timesync_process = subprocess.run(['/bin/date', '-s', clienttime], capture_output=True, text=True)
        if timesync_process.stderr == "":
            self.logger.info('CameraController: Time successfully synchronised with client. New time is {}'.format(clienttime))
        else:
            self.logger.warning('CameraController: Failed to synchronise time with client.')


    # Set Timestamp Mode
    def set_TimestampMode(self, timestamp):
        if timestamp == "off":
            #Timestamps disabled
            self.timestamp = 0
            self.logger.debug('CameraController: Timestamps disabled')
            self.config["timestamp"] = "off"
            self.config.flush()
        else:
            #Timestamps enabled
            self.timestamp = 1
            self.logger.debug('CameraController: Timestamps enabled')
            self.config["timestamp"] = "on"
            self.config.flush()

    # Set Camera Sharpness
    def set_sharpness(self, sharpness_val, sharpness_mode):
        self.driver.set_sharpness(
            SharpnessMode.AUTO if sharpness_mode == "auto" else SharpnessMode.MANUAL,
            sharpness_val
        )
        self.config["sharpness_val"] = sharpness_val
        self.config["sharpness_mode"] = sharpness_mode
        self.config.flush()

    # Carry out Shutdown option
    def set_Shutdown(self, Shutdown):
        if Shutdown == "0":
            #Carry out shutdown
            subprocess.run(["sudo", "shutdown", "now"]) 
        else:
            #Carry out reboot
            subprocess.run(["sudo", "reboot", "now"]) 
