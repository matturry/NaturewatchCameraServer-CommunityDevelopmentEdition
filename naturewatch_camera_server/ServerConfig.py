import json
import pathlib
from threading import Lock

MODULE_PATH = pathlib.Path(__file__).parent

class Config:
    def __init__(self, config):
        self.config = config
        self.file_lock = Lock()

    @classmethod
    def load_from_file(cls, path):
        with open(path, 'r') as f:
            return cls(json.loads(f.read()))

    @property
    def config_path(self):
        config_path = pathlib.Path(self.config["data_path"])
        if not config_path.is_absolute():
            config_path = MODULE_PATH / config_path
        return config_path

    def flush(self):
        self.file_lock.acquire()
        try:
            with open(self.config_path, 'w') as f:
                contents = json.dumps(
                    new_config, sort_keys=True, indent=4,
                    separators=(',', ': ')
                )
                json_file.write(contents)
        finally:
            self.file_lock.release()

    def __getitem__(self, item):
        if hasattr(self, item):
            return getattr(self, item)
        return self.config[item]

    def __setitem__(self, item, val):
        if hasattr(self, item):
            setattr(self, item)
        self.config[item] = val

    @property
    def data_path(self):
        return MODULE_PATH / self.config['data_path']

    @property
    def photos_path(self):
        return self.data_path / self.config['photos_path']

    @property
    def videos_path(self):
        return self.data_path / self.config['videos_path']

    @property
    def hi_res(self):
        width, height = self.config["resolution"].split('x', 1)
        res = (int(width), int(height))
        assert res in [(1640, 1232), (1920, 1080)]
        return  res

    @property
    def lo_res(self):
        assert self.hi_res in [(1640, 1232), (1920, 1080)]
        if self.hi_res == (1640, 1232):
            return (320, 240)
        return (320, 180)
