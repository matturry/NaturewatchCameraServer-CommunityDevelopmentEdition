import threading
import cv2
import imutils
import time
import logging
import io
import json
import numpy as np
import os
import datetime as dt
import RPi.GPIO as GPIO
import subprocess

try:
    from picamera2 import Picamera2, MappedArray
    from picamera2.encoders import H264Encoder, Quality
    from picamera2.outputs import CircularOutput
    from libcamera import controls
    from libcamera import Transform
    from bisect import bisect_left
    picamera_exists = True 
  
except ImportError:
    Picamera2 = None
    picamera_exists = False


class CameraController(threading.Thread):

    def __init__(self, logger, config):
        threading.Thread.__init__(self)
        self._stop_event = threading.Event()
        self.cancelled = False

        self.logger = logger
        self.config = config

        # Use BCM GPIO references instead of physical pin numbers
        GPIO.setmode(GPIO.BCM)

        # Disable GPIO warnings 
        GPIO.setwarnings(False)

        # Define GPIO pins to use
        # GPIO 16 for LED 
        GPIO.setup(16, GPIO.OUT)



# For photos
        self.picamera_photo_stream = None

# Define the font style for the timestamps
        self.colour = (255, 255, 255) # text colour
        self.bgcolour = (0, 0, 0) # background colour
        self.origin = (0, 28) # bottom left hand corner of text on hires images
        self.lores_origin = (0, 8) # bottom left hand corner of text on lores stream
        self.bgend = (390, 35) # bottom right corner of background on hi res images
        self.lores_bgend = (115, 8) # bottom right corner of background on lores stream
        self.bgstart = (0, 0) # top left corner of background on hi res images
        self.lores_bgstart = (0, 0) # top left corner of background on lores stream
        self.font = cv2.FONT_HERSHEY_SIMPLEX # hires font
        self.lores_font = cv2.FONT_HERSHEY_PLAIN #lores font
        self.scale = 1 # hires font size
        self.lores_scale = 0.6 # lores font size
        self.thickness = 2 # hires font thickness
        self.lores_thickness = 1 # lores font thickness

        self.camera = None

        if picamera_exists:
            self.initialise_picamera()
            # We use a pre_callback function to add the timestamp to images and videos recorded. This doesn't apply to the live stream viewed through the web interface
            self.camera.pre_callback = self.apply_timestamp
      
        self.image = None
        self.hires_image = None
        self.encoder = H264Encoder(repeat=True, iperiod=15)
        self.encoder.output = CircularOutput(buffersize=self.config.video_buffer_size)
        self.logger.debug('CameraController: Video buffer size allocated = %d', self.config.video_buffer_size)
        self.recording_active = False
        
    # Main routine
    def run(self):
        while not self.is_stopped():
            try:
                if picamera_exists:
                    try:
                        # Get image from Pi camera
                        self.yuvimage = self.camera.capture_array("lores")
                        if self.config.timestamp:
                            timestamp = time.strftime("%d/%m/%Y %H:%M:%S")
                            cv2.rectangle(self.yuvimage, self.lores_bgstart, self.lores_bgend, self.bgcolour, -1)
                            cv2.putText(self.yuvimage, timestamp, self.lores_origin, self.lores_font, fontScale=self.lores_scale, thickness=self.lores_thickness, color=self.colour)
                        self.image = cv2.cvtColor(self.yuvimage, cv2.COLOR_YUV420p2RGB)
                        if self.image is None:
                            self.logger.warning("CameraController: got empty image.")
                        # While recording we do not need to check for motion, so we only update this loop every 1s to update the web feed
                        if not self.recording_active:
                            time.sleep(0.03)
                        else:
                            time.sleep(1)
                    except Exception as e:
                        self.logger.error("CameraController: picamera error.")
                        self.logger.exception(e)
                        self.initialise_picamera()
                        time.sleep(0.02)
            except KeyboardInterrupt:
                self.logger.i

    # Apply a datestamp to saved images and videos. This doesn't apply to the live stream viewed through the web interface
    def apply_timestamp(self, request):
        if self.config.timestamp:
            timestamp = time.strftime("%d/%m/%Y %H:%M:%S")
            with MappedArray(request, "main") as m:
                cv2.rectangle(m.array, self.bgstart, self.bgend, self.bgcolour, -1)
                cv2.putText(m.array, timestamp, self.origin, self.font, self.scale, self.colour, self.thickness)
  
    # Stop thread
    def stop(self):
        self._stop_event.set()

        if picamera_exists:
            # Close pi camera
            self.camera.stop_encoder()
            self.camera.stop()
            self.camera.close()
            self.camera = None

        self.logger.info('CameraController: stopping ...')

    # Check if thread is stopped
    def is_stopped(self):
        return self._stop_event.is_set()

    # Get MD YUV image
    def get_md_yuvimage(self):
        if self.yuvimage is not None:
            return self.yuvimage.copy()

    # Get MD image
    def get_md_image(self):
        if self.image is not None:
            return self.image.copy()

    # Get MD image in binary jpeg encoding format
    def get_image_binary(self):
        r, buf = cv2.imencode(".jpg", self.get_md_image())
        return buf

    # Start saving contents of circular video buffer to disk
    def start_saving_video(self, output_video):
        if picamera_exists:
            self.encoder.output.fileoutput = output_video
            self.encoder.output.start()

    # Stop saving contents of circular video buffer to disk
    def stop_saving_video(self):
        if picamera_exists:
            self.encoder.output.stop()
            self.encoder.output.fileoutput = None

    def start_video_stream(self):
        if picamera_exists:
            self.camera.start_encoder(self.encoder, self.encoder.output, quality=Quality.HIGH)
            self.logger.debug('CameraController: recording started to circular buffer')

    def stop_video_stream(self):
        if picamera_exists:
            self.camera.stop_encoder()
            self.logger.debug('CameraController: recording stopped')

    def wait_recording(self, delay):
        if picamera_exists:
            time.sleep(delay)

    # Get high res image
    def get_hires_image(self):
        self.logger.debug("CameraController: hires image requested.")
        if picamera_exists:
            self.hires_yuvimage = self.camera.capture_array("main")
            s = cv2.cvtColor(self.hires_yuvimage, cv2.COLOR_YUV420p2RGB)
            if s is not None:
                return s.copy()
            else:
                return None

    # Initialise picamera. If already started, close and reinitialise.
    def initialise_picamera(self):
        self.logger.debug('CameraController: initialising picamera ...')

        # If there is already a running instance, close it
        if self.camera is not None:
            self.camera.close()

        # Create a new instance of Picamera2 and attempt to connect to the camera
        try:
            self.camera = Picamera2()
        except Exception as e:
            self.logger.error('CameraController: Unable to connect to camera')
            raise Exception("Unable to connect to camera")

        # Check for module revision
        # TODO: set maximum resolution based on module revision
        self.camera_model = self.camera.camera_properties['Model']
        self.logger.info('CameraController: camera module revision {} detected.'.format(self.camera_model))

        
        GPIO.output(16, self.config.LED)
        self.logger.debug('CameraController: LED %s', 'enabled' if self.config.LED else 'disabled')


        # Set up main imaging resolution and motion detection resolution (lores) and
        self.camera.lsize = (self.config.resolution.value.md_width, self.config.resolution.value.md_height)
        self.camera.mainsize = (self.config.resolution.value.width, self.config.resolution.value.height)

        video_config = self.camera.create_video_configuration(
            main={"size": self.camera.mainsize,
                  "format": "YUV420"},
            lores={"size": self.camera.lsize,
                   "format": "YUV420"},
            raw={"size": self.camera.mainsize},
            transform=Transform(hflip=self.config.rotate_camera, vflip=self.config.rotate_camera),
            controls={"FrameDurationLimits": (self.config.frame_duration, self.config.frame_duration)}
        )
        self.camera.configure(video_config)
        self.camera.start()

        # Check the current exposure mode and apply relevant settings
        if self.config.exposure_mode == ControlMode.AUTO:
            self.logger.info('Initialising with automatic exposure time.')
        else:
            self.logger.info('Initialising with exposure time:  %d', self.config.shutter_speed)
            self.logger.info('Initialising with analogue gain:  %f', self.config.analogue_gain)
            self.set_exposure(self.config.shutter_speed, self.config.analogue_gain)

        self.logger.info('CameraController: camera initialised with a resolution of {} and a framerate of {} fps'.format(self.camera.mainsize, int(1/(self.camera.capture_metadata()["FrameDuration"]/1000000))))
        self.logger.info('CameraController: Note that frame rates above 12fps lead to dropped frames on a Pi Zero and frame rates above 25fps can lock up the Pi Zero 2W')
        self.logger.debug('CameraController: Motion detection stream prepared with resolution %dx%d.',
                          self.config.resolution.value.md_width, self.config.resolution.value.md_height)

        # Check camera model to see if autofocus is supported and enable if configured in settings file
        # imx708 models correspond to the Raspberry Pi Camera Model 3
        if self.config.af_enable and self.af_supported:
            if "imx708" in self.camera_model:
                self.camera.set_controls({"AfMode": controls.AfModeEnum.Auto})
                self.run_autofocus()

        # Set the user configured image sharpness
        self.set_sharpness(self.sharpness_val, self.sharpness_mode)

    @property
    def af_supported(self):
        return "im708" in self.camera_model

    # Carry out the autofocus routine
    def run_autofocus(self):
        if self.config.af_enable and self.af_supported:
            success = self.camera.autofocus_cycle()
            i = 0
            while not success and i < 5:
                i+=1
                time.sleep(1)
            if success:
                self.logger.debug('CameraController: autofocus routine completed successfully')
            else:
                self.logger.debug('CameraController: autofocus routine timed out')


    # Set camera rotation
    def set_camera_rotation(self, rotation: bool):
        if self.config.rotate_camera != rotation:
            self.config.rotate_camera = rotation
            self.camera.rotation = 180 if rotation else 0
            self.camera.stop()
            video_config = self.camera.create_video_configuration(
                    main={"size": self.camera.mainsize, 
                          "format": "YUV420"},
                    lores={"size": self.camera.lsize,
                           "format": "YUV420"},
                    raw={"size": self.camera.mainsize},
                    transform=Transform(hflip=rotation, vflip=rotation))
            self.camera.configure(video_config)
            self.camera.start()
            self.config.flush()

    # Set picamera exposure
    def set_exposure(self, ExposureTime: int, AnalogueGain: float):
        if picamera_exists:
            self.camera.set_controls({
                "ExposureTime": ExposureTime,
                "AnalogueGain": AnalogueGain,
                "AwbMode" : controls.AwbModeEnum.Auto
            })
            # Need to wait a short while for the new settings to take effect
            # before we query the new value from the camera
            time.sleep(0.5)
            self.config.shutter_speed = ExposureTime
            self.config.exposure_mode = Config.ControlMode.MANUAL
            self.config.analogue_gain = AnalogueGain
            self.config.flush()

    def get_exposure_mode(self):
        if picamera_exists:
            self.logger.debug('Exposure mode is set to: {}'.format(self.config.exposure_mode))
            return self.config.exposure_mode

    def get_MetaData(self, control):
        if picamera_exists:         
            request = self.camera.capture_request()
            metadata = request.get_metadata()
            request.release()
            self.logger.debug('{} is set to: {}'.format(control, metadata[control]))

            # Exposure values are usually set to a value close to, but not exactly equal to the value requested.
            # So when we query the actual exposure value set we need to work out which exposure from our custom list is closest to the actual value
            if control == "ExposureTime":
                ExpList = [250, 313, 400, 500, 625, 800, 1000, 1250, 1563, 2000, 2500, 3125, 4000, 5000, 6250, 8000, 10000, 12500, 16666, 20000, 25000, 33333]
                ExpValue = self.find_closest_exposure(ExpList, metadata[control])
                self.logger.debug('Closest preset exposure value is: {}'.format(ExpValue))
                return ExpValue
            else:
                return metadata[control]


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
        """
        Set picamera exposure to auto
        :return: none
        """
        if picamera_exists:
            self.config.exposure_mode = ControlMode.AUTO
            self.camera.set_controls({
                "ExposureTime": 0,
                "AnalogueGain": 0,
                "AwbMode" : controls.AwbModeEnum.Auto
            })
            self.config.flush()

    # Set camera resolution
    def set_resolution(self, resolution: SupportedResolution):
        if self.config.resolution != resolution:
            self.config.resolution = resolution
            self.config.flush()
            subprocess.run(["sudo", "systemctl", "restart", "python.naturewatch.service"])        

    # Set LED output
    def set_LED(self, LED):
        if self.config.LED != LED:
            self.config.LED = LED
            GPIO.output(16, self.config.LED)
            self.logger.debug('CameraController: LED %s', "enabled" if self.config.LED else "disabled")
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
        self.logger.debug('CameraController: Timestamps %s', 'enabled' if timestamp else 'disabled')
        self.config.timestamp = timestamp
        self.flush()

    # Set Camera Sharpness
    def set_sharpness(self, sharpness_val: int, sharpness_mode: Config.ControlMode):
        self.config.sharpness_mode = sharpness_mode
        self.config.sharpness_val = sharpness_val
        self.camera.set_controls({"Sharpness": sharpness_val})
        self.logger.debug('CameraController: Sharpness set to {}'.format(sharpness_val))
        self.config.flush()

    # Carry out Shutdown option
    def set_Shutdown(self, Shutdown):
        if Shutdown == "0":
            #Carry out shutdown
            subprocess.run(["sudo", "shutdown", "now"]) 
        else:
            #Carry out reboot
            subprocess.run(["sudo", "reboot", "now"]) 
