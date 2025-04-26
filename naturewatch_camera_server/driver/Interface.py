import abc
import enum

class LEDState(enum.Enum):
    OFF = False
    ON = True

class ExposureMode(enum.Enum):
    AUTO = "auto"
    MANUAL = "manual"

class SharpnessMode(enum.Enum):
    AUTO = "auto"
    MANUAL = "manual"

class ImageResolution(enum.Enum):
    LORES = "lores"
    HIRES = "main"

class DriverInterface(abc.ABC):
    def __init__(self, logger):
        self.logger = logger
        self.preprocess_callback = None

    @abc.abstractmethod
    def initialise_camera(self, config):
        pass

    @abc.abstractmethod
    def configure_LED(self, state):
        pass

    @abc.abstractmethod
    def autofocus(self):
        pass

    @abc.abstractmethod
    def set_exposure(self, mode, exposure_time=None, analogue_gain=None):
        pass

    @abc.abstractmethod
    def get_exposure_settings(self):
        pass

    @abc.abstractmethod
    def stop(self):
        pass

    @property
    @abc.abstractmethod
    def can_autofocus(self):
        pass
    
    @abc.abstractmethod
    def set_preprocess_callback(self, callback):
        pass
    
    @abc.abstractmethod
    def get_yuv_image(self, resolution):
        pass

    @abc.abstractmethod
    def start_video_buffer(self):
        pass

    @abc.abstractmethod
    def stop_video_buffer(self):
        pass

    @abc.abstractmethod
    def start_video_capture(self):
        pass

    @abc.abstractmethod
    def stop_video_capture(self):
        pass

    @abc.abstractmethod
    def get_cpu_temp(self):
        pass

    @abc.abstractmethod
    def shutdown(self, reboot):
        pass
