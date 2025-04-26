from picamera2 import Picamera2, MappedArray
from picamera2.encoders import H264Encoder, Quality
from picamera2.outputs import CircularOutput
from libcamera import controls
from libcamera import Transform
from bisect import bisect_left
import RPi.GPIO as GPIO

from .driver.Interface import LEDState, ExposureMode, DriverInterface
from .driver.Interface import ImageFormat, ImageResolution, SharpnessMode

class RPiDriver(DriverInterface):
    LED_GPIO = 16

    def __init__(self, logger):
        super().__init__(logger)
        self.camera = None
        self.camera_model = None

    def stop(self):
        self.logger.info('RPiDriver: stopping ...')
        self.camera.stop_encoder()
        self.camera.stop()
        self.camera.close()
        self.camera = None

    @property
    def can_autofocus(self):
        return "imx708" in self.camera_model 

    def initialise_camera(self, config):
        self.initialise_GPIO(config)
        self.initialise_picamera(config)

    def initialise_GPIO(self, config):
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        GPIO.setup(self.LED_GPIO, GPIO.OUT)
        self.configure_LED(
            LEDState.OFF if config['LED'] == 'off' else LEDState.ON
        )

    def initialise_picamera(self, config):
        self.logger.debug('RPiDriver: initialising picamera ...')
        if self.camera is not None:
            self.camera.close()
        try:
            self.camera = Picamera2()
        except Exception as e:
            self.logger.error('RPiDriver: Unable to connect to camera')
            raise Exception("Unable to connect to camera")
        self.camera_model = self.camera.camera_properties['Model']
        self.logger.info(
            'RPiDriver: camera module revision %s detected.',
            self.camera_model
        )
        frame_duration = 1_000_000 // config["frame_rate"]
        rotated = config["rotate_camera"] == 1
        video_config = self.camera.create_video_configuration(**{
            ImageResolution.HIRES: {
                "size": config["hi_res"],
                "format": "YUV420"
            },
            ImageResolution.LORES: {
                "size": config["lo_res"],
                "format": "YUV420"
            }, 
            'raw' :{
                "size": config["hi_res"]
            },
            'transform': Transform(hflip=rotated, vflip=rotated),
            'controls' : {
                "FrameDurationLimits": (frame_duration, frame_duration)
            }
        })
        self.camera.configure(video_config)
        self.camera.start()
        self.logger.info(
            'RPiDriver: camera initialised with a resolution of %s and a framerate of %s fps',
            self.camera.mainsize, 1 // (self.camera.capture_metadata()["FrameDuration"] / 1_000_000)
        )
        self.logger.info(
            'RPiDriver: Note that frame rates above 12fps lead to dropped frames on a Pi Zero'
            'and frame rates above 25fps can lock up the Pi Zero 2W'
        )
        self.logger.debug(
            'RPiDriver: Motion detection stream prepared with resolution %dx%d',
            *config['lo_res']
        )
        exposure_mode = ExposureMode.AUTO if config["exposure_mode"] == "auto" else ExposureMode.MANUAL
        self.set_exposure(exposure_mode, config["shutter_speed"], config["analogue_gain"])
        if config["af_enable"] == 1:
            self.autofocus()
        sharpness_mode = SharpnessMode.AUTO if config["sharpness_mode"] == "auto" else SharpnessMode.MANUAL
        self.set_sharpness(sharpness_mode, config["sharpness_val"])
        # Set CircularOutput buffer size. One buffer per frame so it's framerate x total
        # number of seconds we wish to retain before motion is detected. 
        # We add an extra 1.1s to ensure we get the full time expected as this
        # was found to be necessary in testing
        self.video_buffer_size = int(
            config["frame_rate"] * (config["video_duration_before_motion"] + 1.1)
        )
        self.encoder = H264Encoder(repeat=True, iperiod=15)
        self.encoder.output = CircularOutput(buffersize=self.video_buffer_size)
        self.logger.debug('RPiDriver: Video buffer size allocated = {}'.format(self.video_buffer_size))
 
    def autofocus(self):
        assert self.camera is not None
        if can_autofocus:
            self.camera.set_controls({"AfMode": controls.AfModeEnum.Auto})
            for _ in range(5):
                success = self.camera.autofocus_cycle()
                if success:
                    self.logger.debug('RPiDriver: autofocus routine completed successfully')
                    return
                time.sleep(1)
            self.logger.debug('RPiDriver: autofocus routine timed out')
        else:
            self.logger.debug('RPiDriver: autofocus not supported')

    def set_exposure(self, mode, exposure_time=None, analogue_gain=None):
        assert self.camera is not None
        if mode == ExposureMode.AUTO:
            self.logger.info('RPiDriver: Configuring automatic exposure time.')
            self.camera.set_controls({
                "ExposureTime": 0,
                "AnalogueGain": 0,
                "AwbMode": controls.AwbModeEnum.Auto
            })
        else:
            self.logger.info('RPiDriver: Configuring manual exposure with')
            self.logger.info('RPiDriver: Exposure Time: %d', exposure_time)
            self.logger.info('RPiDriver: Analogue Gain: %d', analogue_gain)
            assert exposure_time is not None
            assert analogue_gain is not None
            assert mode == ExposureMode.MANUAL
            self.camera.set_controls({
                "ExposureTime": exposure_time,
                "AnalogueGain": analogue_gain,
                "AwbMode": controls.AwbModeEnum.Auto
            })
        # Need to wait a short while for the new settings
        # to take effect before we query the new value from the camera
        time.sleep(0.5)

    def configure_LED(self, state):
        GPIO.output(16, state)
        self.logger.debug('RPiDriver: LED %s', state)

    def set_sharpness(self, sharpness_mode, sharpness_val=None):
        if sharpness_mode == SharpnessMode.AUTO:
            sharpness_val = 1
        else:
            assert shapness_mode == SharpnessMode.MANUAL
        self.camera.set_controls({"Sharpness": sharpness_val})
        self.logger.debug('RPi Driver: Sharpness set to %d', sharpness_val)

    def get_exposure_settings(self):
        assert self.camera is not None
        req = self.camera.capture_request()
        metadata = req.get_metadata()
        req.release()
        return {
            "mode": ExposureMode.AUTO if metadata['AeEnable'] else ExposureMode.MANUAL,
            "analogue_gain": metadata["AnalogueGain"],
            "shutter_speed": metadata["ExposureTime"]
        }

    def picamera_callback(self, request):
        assert self.preprocess_callback is not None
        with MappedArray(request, ImageResolution.HIRES) as m:
            self.preprocess_callback(m.array, ImageResolution.HIRES)
        with MappedArray(request, ImageResolution.LORES) as m:
            self.preprocess_callback(m.array, ImageResolution.LORES)

    def set_preprocess_callback(self, callback):
        assert self.camera is not None
        self.preprocess_callback = callback
        if self.preprocess_callback is not None:
            self.camera.pre_callback = self.picamera_callback
        else:
            self.camera.pre_callback = None

    def get_yuv_image(self, resolution):
        return self.camera.capture_array(resolution)

    def start_video_buffer(self):
        self.camera.start_encoder(
            self.encoder, self.encoder.output, quality=Quality.HIGH
        )
        self.logger.debug(
            'RPiDriver: starting video buffer'
        )

    def stop_video_buffer(self):
        self.camera.stop_encoder()
        self.logger.debug('RPiDriver:stopping video buffer')

    def start_video_capture(self, file_path):
        self.encoder.output.fileoutput = file_path
        self.encoder.output.start()

    def stop_video_capture(self):
        self.encoder.output.stop()
        self.encoder.output.fileoutput = None
