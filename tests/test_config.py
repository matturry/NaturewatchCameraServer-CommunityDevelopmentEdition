from io import StringIO
import json
import copy
import pytest

from naturewatch_camera_server.Config import Config, SupportedResolution, InvalidConfig, ControlMode

DEFAULT_CONFIG={
    "resolution": "1640x1232",
    "log_level": "INFO",
    "LED": "off",
    "sharpness_mode": "auto",
    "sharpness_val": 1,
    "timestamp": "off",
    "exposure_mode": "auto",
    "rotate_camera": "1",
    "frame_rate": 10,
    "video_duration_before_motion": 1,
    "video_duration_after_motion": 2,
    "shutter_speed": 2000,
    "analogue_gain": 1.0,
    "af_enable": True,
    "min_photo_interval_s": 1,
    "sensitivity": 4,
    "timelapse_interval": 10,
    "timelapse_active": False,
    "tn_width": 100,
}


def load_config_with_default(**overrides):
    config = {**DEFAULT_CONFIG, **overrides}
    return Config.load_from_json_dict(config), config

@pytest.mark.parametrize("res,enum_res", [("1640x1232", SupportedResolution.RES_1640x1232), ("1920x1080", SupportedResolution.RES_1920x1080)]) 
def test_valid_resolution(res, enum_res):
    cfg, _ = load_config_with_default(resolution=res)
    assert cfg.resolution == enum_res

def test_invalid_resolution():
    with pytest.raises(InvalidConfig):
        load_config_with_default(resolution="124x1232")

@pytest.mark.parametrize("key", ["resolution", "log_level"]) 
def test_missing_key_error(key):
    bad_cfg = copy.deepcopy(DEFAULT_CONFIG)
    del bad_cfg[key]
    with pytest.raises(InvalidConfig):
        Config.load_from_json_dict(bad_cfg)

@pytest.mark.parametrize("level_str,level_int", [("DEBUG", 10), ("INFO", 20), ("WARNING", 30), ("ERROR", 40), ("CRITICAL", 50)])
def test_valid_log_levels(level_str, level_int):
    cfg, _ = load_config_with_default(log_level=level_str)
    assert cfg.log_level == level_int
    cfg, _ = load_config_with_default(log_level=level_str.lower())
    assert cfg.log_level == level_int

def test_invalid_log_level():
    with pytest.raises(InvalidConfig):
        load_config_with_default(log_level="BAD_LOG_LEVEL")

@pytest.mark.parametrize("val", range(0, 17))
def test_sharpness_value_manual(val):
    cfg, _ = load_config_with_default(sharpness_val=str(val), sharpness_mode="manual")
    assert cfg.sharpness_val == val
    cfg, _ = load_config_with_default(sharpness_val=val, sharpness_mode="manual")
    assert cfg.sharpness_val == val

@pytest.mark.parametrize("val", range(0, 17))
def test_sharpness_value_auto(val):
    cfg, _ = load_config_with_default(sharpness_val=str(val), sharpness_mode="auto")
    assert cfg.sharpness_val == 1
    cfg, _ = load_config_with_default(sharpness_val=val, sharpness_mode="auto")
    assert cfg.sharpness_val == 1
   
@pytest.mark.parametrize("val", [None, "notanumber", "-1", "17", -1, 17])
def test_invalid_sharpness_val(val):
    with pytest.raises(InvalidConfig):
        load_config_with_default(sharpness_val=val)

@pytest.mark.parametrize("val", range(0, 17))
def test_sharpness_value_auto(val):
    cfg, _ = load_config_with_default(sharpness_val=str(val), sharpness_mode="auto")
    assert cfg.sharpness_val == 1
    cfg, _ = load_config_with_default(sharpness_val=val, sharpness_mode="auto")
    assert cfg.sharpness_val == 1

@pytest.mark.parametrize("val", range(1, 11))
def test_sensitivity(val):
    cfg, _ = load_config_with_default(sensitivity=str(val))
    assert cfg.sensitivity == val
    cfg, _ = load_config_with_default(sensitivity=val)
    assert cfg.sensitivity == val
   
@pytest.mark.parametrize("val", [None, "notanumber", "-1", "17", -1, 17])
def test_invalid_sensitivity_val(val):
    with pytest.raises(InvalidConfig):
        load_config_with_default(sensitivity=val)

@pytest.mark.parametrize("rate,duration", [(1, 1_000_000), (25, 40_000), (12, 83_333)])
def test_frame_rate(rate, duration):
    cfg, _ = load_config_with_default(frame_rate=str(rate))
    assert cfg.frame_rate == rate
    assert cfg.frame_duration == duration
    cfg, _ = load_config_with_default(frame_rate=rate)
    assert cfg.frame_rate == rate
    assert cfg.frame_duration == duration
 
@pytest.mark.parametrize("val", [None, "notanumber", "-1", -1])
def test_invalid_frame_rate(val):
    with pytest.raises(InvalidConfig):
        load_config_with_default(frame_rate=val)

@pytest.mark.parametrize("duration,frame_rate,buf_size", [(1, 10, 21), (1, 20, 42), (2, 20, 62), (5, 3, 18), (5, 2, 12)])
def test_video_duration_before_motion(duration, frame_rate, buf_size):
    cfg, _ = load_config_with_default(video_duration_before_motion=str(duration), frame_rate=frame_rate)
    assert cfg.video_duration_before_motion == duration
    assert cfg.video_buffer_size == buf_size
    cfg, _ = load_config_with_default(video_duration_before_motion=duration, frame_rate=frame_rate)
    assert cfg.video_duration_before_motion == duration
    assert cfg.video_buffer_size == buf_size
 
@pytest.mark.parametrize("val", [None, "notanumber", "-1", -1])
def test_invalid_video_duration_before_motion(val):
    with pytest.raises(InvalidConfig):
        load_config_with_default(video_duration_before_motion=val)

@pytest.mark.parametrize("val", [2000, 1000, 10, 20, 1])
def test_video_duration_after_motion(val):
    cfg, _ = load_config_with_default(video_duration_after_motion=str(val))
    assert cfg.video_duration_after_motion == val
    cfg, _ = load_config_with_default(video_duration_after_motion=val)
    assert cfg.video_duration_after_motion == val
   
@pytest.mark.parametrize("val", [None, "notanumber", "-1", -1, 0, "0"])
def test_invalid_video_duration_after_motion(val):
    with pytest.raises(InvalidConfig):
        load_config_with_default(video_duration_after_motion=val)

@pytest.mark.parametrize("val", [2000, 1000, 10, 20, 1])
def test_shutter_speed(val):
    cfg, _ = load_config_with_default(shutter_speed=str(val))
    assert cfg.shutter_speed == val
    cfg, _ = load_config_with_default(shutter_speed=val)
    assert cfg.shutter_speed == val
   
@pytest.mark.parametrize("val", [None, "notanumber", "-1", -1, 0, "0"])
def test_invalid_shutter_speed(val):
    with pytest.raises(InvalidConfig):
        load_config_with_default(shutter_speed=val)

@pytest.mark.parametrize("val", [1.0, 0.5, 2.0, 5, 2])
def test_analogue_gain(val):
    cfg, _ = load_config_with_default(analogue_gain=str(val))
    assert cfg.analogue_gain == val
    cfg, _ = load_config_with_default(analogue_gain=val)
    assert cfg.analogue_gain == val
   
@pytest.mark.parametrize("val", [None, "notanumber", "-1", -1, 0, "0"])
def test_invalid_analogue_gain(val):
    with pytest.raises(InvalidConfig):
        load_config_with_default(analogue_gain=val)

@pytest.mark.parametrize("val", [1, 5, 10])
def test_min_photo_interval(val):
    cfg, _ = load_config_with_default(min_photo_interval_s=str(val))
    assert cfg.min_photo_interval_s == val
    cfg, _ = load_config_with_default(min_photo_interval_s=val)
    assert cfg.min_photo_interval_s == val

@pytest.mark.parametrize("val", [None, "notanumber", "-1", -1])
def test_invalid_min_photo_interval_s(val):
    with pytest.raises(InvalidConfig):
        load_config_with_default(min_photo_interval_s=val)

@pytest.mark.parametrize("val", [100, 1024, 50])
def test_tn_width(val):
    cfg, _ = load_config_with_default(tn_width=str(val))
    assert cfg.tn_width == val
    cfg, _ = load_config_with_default(tn_width=val)
    assert cfg.tn_width == val

@pytest.mark.parametrize("val", [None, "notanumber", "-1", -1])
def test_invalid_tn_width(val):
    with pytest.raises(InvalidConfig):
        load_config_with_default(tn_width=val)

@pytest.mark.parametrize("val", [1, 5, 10])
def test_timelapse_interval(val):
    cfg, _ = load_config_with_default(timelapse_interval=str(val))
    assert cfg.timelapse_interval == val
    cfg, _ = load_config_with_default(timelapse_interval=val)
    assert cfg.timelapse_interval == val

@pytest.mark.parametrize("val", [None, "notanumber", "-1", -1])
def test_invalid_timelapse_interval(val):
    with pytest.raises(InvalidConfig):
        load_config_with_default(timelapse_interval=val)

BOOL_FIELDS = ["timestamp", "LED", "rotate_camera", "af_enable", "timelapse_active"]

@pytest.mark.parametrize("field", BOOL_FIELDS)
def test_on_off_field(field):
    for on_val in ["yes", 1, True, "true", "on"]:
        cfg, _ = load_config_with_default(**{field: on_val})
        assert getattr(cfg, field) == True
    for off_val in ["no", 0, False, "false", "off"]:
        cfg, _ = load_config_with_default(**{field: off_val})
        assert getattr(cfg, field) == False

@pytest.mark.parametrize("field", BOOL_FIELDS)
def test_bad_on_off_field(field):
    with pytest.raises(InvalidConfig):
        load_config_with_default(**{field: "both"})


MODE_FIELDS = ["sharpness_mode", "exposure_mode"]

@pytest.mark.parametrize("field", MODE_FIELDS)
def test_mode_field(field):
    cfg, _ = load_config_with_default(**{field: "auto"})
    assert getattr(cfg, field) == ControlMode.AUTO
    cfg, _ = load_config_with_default(**{field: "manual"})
    assert getattr(cfg, field) == ControlMode.MANUAL

@pytest.mark.parametrize("field", MODE_FIELDS)
def test_bad_mode_field(field):
    with pytest.raises(InvalidConfig):
        load_config_with_default(**{field: "invalid"})


KEY_MAP=[
    ("resolution", [["1640x1232"], ["1920x1080"]], ["1640x1232", "1920x1080"]),
    ("log_level", [("DEBUG", "debug"), ("INFO", "info"), ("WARNING", "warning"), ("ERROR", "error"), ("CRITICAL", "critical")], ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]),
    ("LED", [["off", 0, "0", False, "false"], ["on", 1, "1", True, "true"]], ["off", "on"]),
    ("sharpness_mode", [["auto"], ["manual"]], ["auto", "manual"]),
    ("sharpness_val", [[1, "1"], [2, "2"]], [1, 2]),
    ("timestamp", [["off", 0, "0", False, "false", "no"], ["on", 1, "1", True, "true", "yes"]], ["off", "on"]),
    ("exposure_mode", [["auto"], ["manual"]], ["auto", "manual"]),
    ("rotate_camera", [["off", 0, "0", False, "false", "no"], ["on", 1, "1", True, "true", "yes"]], [0, 1]),
    ("frame_rate", [[10], [15]], [10, 15]),
    ("video_duration_before_motion", [[1], [10]], [1, 10]),
    ("video_duration_after_motion", [[2], [20]], [2, 20]),
    ("shutter_speed", [[2000], [200]], [2000, 200]),
    ("analogue_gain", [[1.0], [1.1]], [1.0, 1.1]),
    ("af_enable", [["off", 0, "0", False, "false", "no"], ["on", 1, "1", True, "true", "yes"]], [0, 1]),
    ("min_photo_interval_s", [[1], [5]], [1, 5]),
    ("sensitivity", [[4], [6]], [4, 6]),
    ("timelapse_interval", [[10], [1]], [10, 1]),
    ("timelapse_active", [["off", 0, "0", False, "false", "no"], ["on", 1, "1", True, "true", "yes"]], [False, True]),
    ("tn_width", [[100], [200]], [100, 200]),
]


@pytest.mark.parametrize("cfg_key,inputs,outputs", KEY_MAP)
def test_config_in_to_config_out(cfg_key, inputs, outputs):
    for cfg_in_vals, cfg_out_val  in zip(inputs, outputs):
        for cfg_val in cfg_in_vals:
            cfg, cfg_in = load_config_with_default(**{cfg_key: cfg_val})
            assert cfg.export_json_dict()[cfg_key] == cfg_out_val, f"key {cfg_key}: {cfg_val} did not come out as {cfg_out_val}"
