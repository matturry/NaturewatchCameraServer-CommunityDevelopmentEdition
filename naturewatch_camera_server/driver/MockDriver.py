import os
import copy
import time

import cv2

from .Interface import DriverInterface, LEDState, ExposureMode
from .Interface import SharpnessMode, ImageResolution

class MockDriver(DriverInterface):
    def __init__(self, logger):
        super().__init__(logger)
        self.LED = LEDState.OFF
        self.sharpness = {
            'mode': SharpnessMode.AUTO,
            'val': 1
        }
        self.exposure = {
            'mode': ExposureMode.AUTO,
            'analogue_gain': 0,
            'shutter_speed': 0
        }
        self.af_enable = True
        self.CPUTemp = '99.9'
        self.video = None
        self.lo_res = None
        self.hi_res = None
        # We want to process the video as though time has 
        # passed when we ask for a new frame, without this each
        # call to get an image would just give the next frame and
        # this would mess with the change detectors
        self.wall_time = None
        self.callback = None
        self.num_frames = None
        self.frame_rate = None
        self.vid_cap_start_time = None
        self.vid_cap_stop_time = None
        self.rotated = False

    def initialise_camera(self, config):
        self.configure_LED(
            LEDState.OFF if config['LED'] == 'off' else LEDState.ON
        )
        assert 'MOCK_VIDEO_PATH' in os.environ
        vid_path = os.environ['MOCK_VIDEO_PATH']
        # The CameraController will access the lo res video from a
        # different thread from the hi res video. OpenCV does not
        # support access to the same videocapture from two thread so
        # instead we create a video feed for both
        # XXX Should address the controller accessing from two threads
        # there are bound to be other places that this causes a problem
        self.video = {
            ImageResolution.HIRES: cv2.VideoCapture(vid_path),
            ImageResolution.LORES: cv2.VideoCapture(vid_path)
        }
        if any(not vid.isOpened() for vid in self.video.values()):
            self.logger.error('MockDriver: Failed to open %s', vid_path)
            raise Exception('Unable to create mock feed')
        self.res = {
            ImageResolution.HIRES: config['hi_res'],
            ImageResolution.LORES: config['lo_res']
        }
        for res in ImageResolution:
            self.video[res].set(cv2.CAP_PROP_FRAME_WIDTH, self.res[res][0])
            self.video[res].set(cv2.CAP_PROP_FRAME_HEIGHT, self.res[res][1])
        self.num_frames = self.video[ImageResolution.LORES].get(
            cv2.CAP_PROP_FRAME_COUNT
        )
        self.frame_rate = self.video[ImageResolution.LORES].get(
            cv2.CAP_PROP_FPS
        )
        self.af_enable = config['af_enable'] == 1
        self.sharpness['mode'] = (
            SharpnessMode.AUTO 
                if config["sharpness_mode"] == "auto" else 
            SharpnessMode.MANUAL
        )
        self.sharpness['val'] = config['sharpness_val']
        self.exposure['mode'] = (
            ExposureMode.AUTO
            if config["exposure_mode"] == "auto" else 
            ExposureMode.MANUAL
        )
        self.exposure['shutter_speed'] = config['shutter_speed']
        self.exposure['analogue_gain'] = config['analogue_gain']
        self.wall_time = time.time()
        self.time_before_trigger = config['video_duration_before_motion']
        self.rotated = config["rotate_camera"] == 1

    def advance_lores_video(self, shift=0):
        now = time.time()
        time_since_last_call = now - self.wall_time + shift
        frames_since_last_call = int(time_since_last_call * self.frame_rate)
        self.wall_time = now
        current_frame = self.video[ImageResolution.LORES].get(
            cv2.CAP_PROP_POS_FRAMES
        )
        self.video[ImageResolution.LORES].set(
            cv2.CAP_PROP_POS_FRAMES,
            (current_frame + frames_since_last_call) % self.num_frames
        )

    def configure_LED(self, state):
        self.LED = state

    def autofocus(self):
        pass

    def set_exposure(self, mode, exposure_time=None, analogue_gain=None):
        self.exposure = {
            'mode': mode,
            'shutter_speed': 1 if exposure_time is None else exposure_time,
            'analogue_gain': 1 if analogue_gain is None else analogue_gain
        }

    def get_exposure_settings(self):
        return copy.deepcopy(self.exposure)

    def stop(self):
        for vid in self.video.values():
            if vid and vid.isopen():
                vid.release()

    @property
    def can_autofocus(self):
        return self.af_enable
    
    def set_preprocess_callback(self, callback):
        self.callback = callback
    
    def get_yuv_image(self, resolution):
        frame_idx = self.advance_lores_video()
        ret, frame = self.video[resolution].read()
        assert ret == True
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2YUV_I420)
        if self.rotated:
            frame = cv2.flip(frame, 0)
        return frame

    def start_video_buffer(self):
        pass

    def stop_video_buffer(self):
        pass

    def start_video_capture(self, file_path):
        self.vid_cap_start_time = time.time() - self.time_before_trigger
        self.vid_cap_start_frame = (
            self.video[ImageResolution.HIRES].get(cv2.CAP_PROP_POS_FRAMES) - 
                self.time_before_trigger * self.frame_rate
        ) % self.num_frames
        self.vid_cap_file_path = file_path

    def stop_video_capture(self):
        num_frames = int(
            (time.time() - self.vid_cap_start_time) * self.frame_rate
        )
        # This will not work if you just pip install opencv-python. You
        # will need create a build against the installed opencv. Either
        # install the package from the distro or build yourself.
        # See https://github.com/opencv/opencv-python/issues/207
        out_vid = cv2.VideoWriter(
            self.vid_cap_file_path, cv2.VideoWriter_fourcc(*'avc1'),
            self.frame_rate, self.res[ImageResolution.HIRES]
        )
        for i in range(num_frames):
            ret, frame = self.video[ImageResolution.HIRES].read()
            if not ret:
                self.video[ImageResolution.HIRES].set(cv2.CAP_PROP_POS_FRAMES, 0)
                ret, frame = self.video[ImageResolution.HIRES].read()
                assert ret
            if self.rotated:
                frame = cv2.flip(frame, 0)
            out_vid.write(frame)
        out_vid.release()

    def get_cpu_temp(self):
        return self.CPUTemp

    def shutdown(self, reboot):
        pass
