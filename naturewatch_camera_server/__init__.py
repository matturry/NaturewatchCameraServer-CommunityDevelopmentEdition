#!../venv/bin/python
import logging
import pathlib
import sys
import os
from shutil import copyfile
from logging.handlers import RotatingFileHandler
from naturewatch_camera_server.CameraController import CameraController
from naturewatch_camera_server.ChangeDetector import ChangeDetector
from naturewatch_camera_server.FileSaver import FileSaver
from naturewatch_camera_server.ServerConfig import Config
from flask import Flask
from naturewatch_camera_server.api import api
from naturewatch_camera_server.data import data
from naturewatch_camera_server.static_page import static_page

if 'MOCK_VIDEO_PATH' in os.environ:
    from .driver.MockDriver import MockDriver as Driver
else:
    from .driver.RaspberryPiDriver import RPiDriver as Driver


MODULE_PATH = pathlib.Path(__file__).parent
CENTRAL_CONFIG_FILE = MODULE_PATH / "config.json"

def create_app():
    """
    Create flask app
    :return: Flask app object
    """
    flask_app = Flask(__name__, static_folder="static/client/build")
    flask_app.register_blueprint(api, url_prefix='/api')
    flask_app.register_blueprint(data, url_prefix='/data')
    flask_app.register_blueprint(static_page)

    # Setup logger
    flask_app.logger = logging.getLogger(__name__)
    flask_app.logger.setLevel(logging.INFO)
    # setup logging handler for stderr
    stderr_handler = logging.StreamHandler()
    stderr_handler.setLevel(logging.INFO)
    flask_app.logger.addHandler(stderr_handler)

    # Load configuration json
    flask_app.logger.info("Module path: %s", MODULE_PATH)
    # load central config file first
    flask_app.user_config = Config.load_from_file(CENTRAL_CONFIG_FILE)
    # load real config dir
    real_config = flask_app.user_config["data_path"] / "config.json"
    if not real_config.exists():
        flask_app.logger.warning("Config file does not exist within the data context, copying file")
        real_config_dir.parent.mkdir(exist_ok=True)
        copyfile(CENTRAL_CONFIG, real_config)

    flask_app.logger.info("Using config file from data context")
    flask_app.user_config = Config.load_from_file(real_config)

    # Set up logging to file
    file_handler = logging.handlers.RotatingFileHandler(
        flask_app.user_config['data_path'] / 'camera.log',
        maxBytes=1024000, backupCount=5
    )
    file_handler.setLevel(logging.INFO)
    numeric_loglevel = getattr(logging, flask_app.user_config["log_level"].upper(), None)
    if not isinstance(numeric_loglevel, int):
        flask_app.logger.info('Invalid log level %r in config file: %s', self.config["log_level"], real_config)
    else:
        file_handler.setLevel(numeric_loglevel)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    flask_app.logger.addHandler(file_handler)
    flask_app.logger.info("Logging to file initialised")

    # Find photos and videos paths
    flask_app.logger.info("Photos path: %s", flask_app.user_config["photos_path"])
    flask_app.user_config["photos_path"].mkdir(exist_ok=True)
    flask_app.logger.info("Videos path: %s", flask_app.user_config["videos_path"])
    flask_app.user_config["videos_path"].mkdir(exist_ok=True)

    # Instantiate classes
    flask_app.driver = Driver(flask_app.logger)
    flask_app.camera_controller = CameraController(flask_app.logger, flask_app.driver, flask_app.user_config)
    flask_app.logger.debug("Instantiating classes ...")
    flask_app.change_detector = ChangeDetector(flask_app.camera_controller, flask_app.user_config, flask_app.logger)
    flask_app.file_saver = FileSaver(flask_app.user_config, flask_app.logger)

    flask_app.logger.debug("Initialisation finished")
    return flask_app

def create_error_app(e):
    """
    Create flask app about an error occurred in the main app
    :return: Flask app object
    """
    flask_app = Flask(__name__, static_folder="static/client/build")

    @flask_app.route('/')
    def index():
        return f"<html><body><h1>Unable to start NaturewatchCameraServer.</h1>An error occurred:<pre>{e}</pre></body></html>"

    return flask_app
