import json
import logging
import os
import sys
from shutil import copyfile
from logging.handlers import RotatingFileHandler
from naturewatch_camera_server.CameraController import CameraController
from naturewatch_camera_server.ChangeDetector import ChangeDetector
from naturewatch_camera_server.FileSaver import FileSaver
from flask import Flask
from naturewatch_camera_server.api import api
from naturewatch_camera_server.data import data
from naturewatch_camera_server.static_page import static_page
from naturewatch_camera_server.Config import Config, InvalidConfig


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
    flask_app.logger.info("Module path: " + Config.module_path)
    try:
        flask_app.user_config = Config.load_user_cfg()
    except Exception as e:
        return create_error_app(str(e))
       
    # Set up logging to file
    file_handler = logging.handlers.RotatingFileHandler(flask_app.user_config.camera_log_path), maxBytes=1024000, backupCount=5)
    file_handler.setLevel(logging.INFO)
    file_handler.setLevel(flask_app.user_config.log_level)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    flask_app.logger.addHandler(file_handler)
    flask_app.logger.info("Logging to file initialised")

    # Find photos and videos paths
    for p in [flask_app.user_config.photos_path, flask_app.user_config.videos_path]:
        if not p.exists():
            flask_app.logger.warning("Path %s does not exist, creating")
        if not p.is_dir():
            flask_app.logger.error("Path %s is not a directory!!", p)
            return create_error_app(f"Path {p} is not a directory!!")

    # Instantiate classes
    flask_app.camera_controller = CameraController(flask_app.logger, flask_app.user_config)
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
