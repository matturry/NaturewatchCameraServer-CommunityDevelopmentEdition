import enum
import dataclasses
import json
import logging

class InvalidConfig(Exception):
    pass

@dataclasses.dataclass(frozen=True)
class Resolution:
    width: int
    height: int
    md_width: int
    md_height: int
    string_name: str = dataclasses.field(init=False)

    def __post_init__(self):
        if self.height <= 0 or self.width <= 0:
            raise Exception(f"Invalid resolution {self.width}x{self.height}")
        if self.md_height <= 0 or self.md_width <= 0:
            raise Exception(
                f"Invalid md resolution {self.md_width}x{self.md_height}"
            )
        # frozen prevents these arrtibutes from being updated by just doing
        # self.string_name = thing. This is to prevent accidental change later
        # We need to override that here.
        object.__setattr__(self, 'string_name', f"{self.width}x{self.height}")


class SupportedResolution(enum.Enum):
    RES_1640x1232 = Resolution(1640, 1232, 320, 240)
    RES_1920x1080 = Resolution(1920, 1080, 320, 180)

    @classmethod
    def from_string(cls, string_name: str) -> 'SupportedResolution':
        for res in SupportedResolution:
            if res.value.string_name == string_name:
                return res
        raise InvalidConfig(f"{string_name} is not a valid resolution")

class ControlMode(enum.StrEnum):
    AUTO = enum.auto()
    MANUAL = enum.auto()

    @classmethod
    def from_string(cls, string_option: str|int) -> 'OnOffState':
        if string_option in ['on', 'yes', 1, 'true', True]:
            return cls.ON
        elif string_option in ['off', 'no', 0, 'false', False]:
            return cls.OFF

class Config:
    REQUIRED_KEYS = set(["resolution", "log_level", "timestamp", "LED", "sharpness_mode",
                         "sharpness_val", "exposure_mode", "frame_rate", "rotate_camera",
                         "video_duration_before_motion", "video_duration_after_motion",
                         "shutter_speed", "analogue_gain", "af_enable", "min_photo_interval_s",
                         "tn_width", "timelapse_active", "timelapse_interval", "sensitivity"])

    def __init__(self, resolution: SupportedResolution, log_level: int, timestamp: bool, LED: bool,
                 sharpness_mode: ControlMode, sharpness_val: int, exposure_mode: ControlMode,
                 frame_rate: int, rotate_camera: bool, video_duration_before_motion: int,
                 video_duration_after_motion: int, shutter_speed: int, analogue_gain: float,
                 af_enable: bool, min_photo_interval_s: int, sensitivity: int,
                 timelapse_interval: int, timelapse_active: bool, tn_width: int):
        self.resolution: SupportedResolution = resolution
        self.log_level: int = log_level
        self.timestamp: bool = timestamp
        self.LED: bool = LED
        self.sharpness_mode: ControlMode = sharpness_mode
        self.sharpness_val: int = sharpness_val
        self.exposure_mode: ControlMode = exposure_mode
        self.frame_rate: int = frame_rate
        self.video_duration_before_motion: int = video_duration_before_motion
        self.video_duration_after_motion: int = video_duration_after_motion
        self.shutter_speed: int = shutter_speed
        self.analogue_gain: float = analogue_gain
        self.af_enable: bool = af_enable
        self.rotate_camera: bool = rotate_camera
        self.min_photo_interval_s: int = min_photo_interval_s
        self.sensitivity: int = sensitivity
        self.timelapse_interval: int = timelapse_interval
        self.timelapse_active: bool = timelapse_active
        self.tn_width: int = tn_width

    @classmethod
    def load_user_cfg(cls) -> 'Config':
        if not cls.user_config_path.getLevelNameexists():
            flask_app.logger.info("Config not found, creating new one at %s", cls.user_config_path)
            Config.data_path.mkdir(exist_ok=True)
            copyfile(cls.default_config_path, cls.user_config_path)
        with open(cls.data_path / 'config.json') as fp:
            jconfig = json.load(fp)
            return cls.load_from_file(jconfig)

    @classmethod
    def load_from_json_dict(cls, jconfig: dict[Any, Any]) -> 'Config':
        missing_keys = cls.REQUIRED_KEYS - set(jconfig.keys())
        if missing_keys:
            raise InvalidConfig(f"Missing keys {missing_keys}")
        resolution = SupportedResolution.from_string(jconfig['resolution'])
        log_level = logging.getLevelName(jconfig['log_level'].upper())
        if not isinstance(log_level, int):
            raise InvalidConfig(f"Unknown log level {jconfig['log_level']}")
        sharpness_mode = cls.process_mode_field('sharpness_mode', jconfig['sharpness_mode'])
        sharpness_val = cls.process_int_field('sharpness_val', jconfig['sharpness_val'])
        timestamp = cls.process_bool_field('timestamp', jconfig['timestamp'])
        LED = cls.process_bool_field('LED', jconfig['LED'])
        exposure_mode = cls.process_mode_field("exposure_mode", jconfig['exposure_mode'])
        rotate_camera = cls.process_bool_field('rotate_camera', jconfig['rotate_camera'])
        frame_rate = cls.process_int_field('frame_rate', jconfig['frame_rate'])
        video_duration_before_motion = cls.process_int_field('video_duration_before_motion', jconfig['video_duration_before_motion'])
        video_duration_after_motion = cls.process_int_field('video_duration_after_motion', jconfig['video_duration_after_motion'])
        shutter_speed = cls.process_int_field("shutter_speed", jconfig['shutter_speed'])
        analogue_gain = cls.process_float_field("analogue_gain", jconfig["analogue_gain"])
        af_enable = cls.process_bool_field('af_enable', jconfig['af_enable'])
        min_photo_interval_s = cls.process_int_field('min_photo_interval_s', jconfig['min_photo_interval_s'])
        sensitivity = cls.process_int_field('sensitivity', jconfig['sensitivity'])
        timelapse_interval = cls.process_int_field('timelapse_interval', jconfig['timelapse_interval'])
        timelapse_active = cls.process_bool_field('timelapse_active', jconfig['timelapse_active'])
        tn_width = cls.process_int_field('tn_width', jconfig['tn_width'])
        return cls(resolution=resolution,
                   log_level=log_level,
                   sharpness_mode=sharpness_mode,
                   sharpness_val=sharpness_val,
                   LED=LED,
                   timestamp=timestamp,
                   exposure_mode=exposure_mode,
                   frame_rate=frame_rate,
                   video_duration_before_motion=video_duration_before_motion,
                   video_duration_after_motion=video_duration_after_motion,
                   shutter_speed=shutter_speed,
                   analogue_gain=analogue_gain,
                   af_enable=af_enable,
                   rotate_camera=rotate_camera,
                   min_photo_interval_s=min_photo_interval_s,
                   sensitivity=sensitivity,
                   timelapse_interval=timelapse_interval,
                   timelapse_active=timelapse_active,
                   tn_width=tn_width)

    def export_json_dict(self):
        return {
            "resolution": self.resolution.value.string_name,
            "log_level": logging.getLevelName(self.log_level),
            "LED": "on" if self.LED else "off",
            "sharpness_mode": self.sharpness_mode,
            "sharpness_val": self._sharpness_val, # with auto this gets capped to 1, write out the actual value
            "timestamp": "on" if self.timestamp else "off",
            "exposure_mode": self.exposure_mode,
            "rotate_camera": 1 if self.rotate_camera else 0,
            "frame_rate": self.frame_rate,
            "video_duration_before_motion": self.video_duration_before_motion,
            "video_duration_after_motion": self.video_duration_after_motion,
            "shutter_speed": self.shutter_speed,
            "analogue_gain": self.analogue_gain,
            "af_enable": 1 if self.af_enable else 0,
            "min_photo_interval_s": self.min_photo_interval_s,
            "sensitivity": self.sensitivity,
            "timelapse_interval": self.timelapse_interval,
            "timelapse_active": True if self.timelapse_active else False,
            "tn_width": self.tn_width,
        }

    def flush(self, fp):
        with open(self.user_config_path, 'w') as json_file:
            new_config = self.export_json_dict()
            contents = json.dumps(new_config, sort_keys=True, indent=4, separators=(',', ': '))
            json_file.write(contents)

    @staticmethod
    def process_int_field(field: str, value: str|int) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            raise InvalidConfig(f"Invalid {field} {value}")

    @staticmethod
    def process_float_field(field: str, value: str|int|float) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            raise InvalidConfig(f"Invalid {field} {value}")

    @staticmethod
    def process_bool_field(field: str, value: str) -> bool:
        if value in ['on', 'yes', 1, '1', 'true', True]:
            return True
        elif value in ['off', 'no', 0, '0', 'false', False]:
            return False
        raise InvalidConfig(f'{field} can be either "on/yes/1/true" or "off/no/0/false"')

    @staticmethod
    def process_mode_field(field: str, value: str) -> ControlMode:
        try:
            return ControlMode(value)
        except:
            raise InvalidConfig(f'{field} can be either "auto" or "manual"')

    @property
    def sharpness_val(self) -> int:
        if self.sharpness_mode == ControlMode.AUTO:
            return 1
        return self._sharpness_val

    @sharpness_val.setter
    def sharpness_val(self, val: int):
        if val < 0 or val > 16:
            raise InvalidConfig("sharpness_val must be between 0 and 16")
        self._sharpness_val = val

    @property
    def sensitivity(self) -> int:
        return self._sensitivity

    @sensitivity.setter
    def sensitivity(self, val: int):
        if val <= 0 or val > 10:
            raise InvalidConfig("sensitivity must be between 1 and 10")
        self._sensitivity = val

    @property
    def timelapse_interval(self) -> int:
        return self._timelapse_interval

    @timelapse_interval.setter
    def timelapse_interval(self, val: int):
        if val <= 0:
            raise InvalidConfig("timelapse_interval must be > 0")
        self._timelapse_interval = val

    @property
    def tn_width(self) -> int:
        return self._tn_width

    @tn_width.setter
    def tn_width(self, val: int):
        if val <= 0:
            raise InvalidConfig("tn_width must be > 0")
        self._tn_width = val

    @property
    def frame_rate(self) -> int:
        return self._frame_rate

    @frame_rate.setter
    def frame_rate(self, val: int):
        if val <= 0:
            raise InvalidConfig("frame_rate must be > 0")
        self._frame_rate = val

    @property
    def video_duration_before_motion(self) -> int:
        return self._video_duration_before_motion

    @video_duration_before_motion.setter
    def video_duration_before_motion(self, val: int):
        if val <= 0:
            raise InvalidConfig("video_duration_before_motion must be > 0")
        self._video_duration_before_motion = val

    @property
    def video_duration_after_motion(self) -> int:
        return self._video_duration_after_motion

    @video_duration_after_motion.setter
    def video_duration_after_motion(self, val: int):
        if val <= 0:
            raise InvalidConfig("video_duration_after_motion must be > 0")
        self._video_duration_after_motion = val

    @property
    def shutter_speed(self) -> int:
        return self._shutter_speed

    @shutter_speed.setter
    def shutter_speed(self, val: int):
        if val <= 0:
            raise InvalidConfig("shutter_speed must be > 0")
        self._shutter_speed = val
    
    @property
    def analogue_gain(self):
        return self._analogue_gain

    @analogue_gain.setter
    def analogue_gain(self, val):
        if val <= 0:
            raise InvalidConfig("analogue_gain must be > 0")
        self._analogue_gain = val

    @property
    def min_photo_interval_s(self):
        return self._min_photo_interval_s

    @min_photo_interval_s.setter
    def min_photo_interval_s(self, val):
        if val <= 0:
            raise InvalidConfig("min_photo_interval_s must be > 0")
        self._min_photo_interval_s = val

    @property
    def video_buffer_size(self):
        # CircularOutput buffer size. One buffer per frame.
        # Add an extra 1.1s to ensure we get the full time expected
        # as this was found to be necessary in testing
        return int(self.frame_rate * (self.video_duration_before_motion + 1.1))

    @property
    def frame_duration(self):
        return 1_000_000 // self.frame_rate

    @classmethod
    @property
    def module_path(cls) -> pathlib.Path:
        return pathlib.Path(__file__).parent.resolve()

    @classmethod
    @property
    def data_path(cls) -> pathlib.Path:
        return cls.module_path / 'static' / 'data'

    @classmethod
    @property
    def user_config_path() -> pathlib.Path:
        return cls.data_path / 'config.json'

    @classmethod
    @property
    def default_config_path() -> pathlib.Path:
        return cls.module_path / 'config.json'

    @classmethod
    @property
    def camera_log_path() -> pathlib.Path:
        return cls.data_path / 'camera.log'

    @classmethod
    @property
    def photos_path() -> pathlib.Path:
        return cls.data_path / 'photos'

    @classmethod
    @property
    def videos_path() -> pathlib.Path:
        return cls.data_path / 'videos'
