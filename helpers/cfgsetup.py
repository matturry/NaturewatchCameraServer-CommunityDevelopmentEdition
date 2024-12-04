# -*- coding: utf-8 -*-
"""Automatically generate a unique SSID for the MyNaturewatch WiFi hotspot,
based on the Pi's serial number."""
import os
import subprocess
import time

# Get SSID and passphrase from hostapd.conf
#HOST_CONFIG_FILE_PATH = "/etc/hostapd/hostapd.conf"

#with open(HOST_CONFIG_FILE_PATH, "r", encoding="utf-8") as config_file:
#    host_config_file = config_file.readlines()

#current_ssid = host_config_file[2][5:].strip()
#print(f"hostapd configuration - SSID: {current_ssid}")

# Generate a unique SSID based on the Pi's serial number
unique_id = subprocess.check_output(
    r"sed -n 's/^Serial\s*: 0*//p' /proc/cpuinfo", shell=True
)
unique_ssid = f"MyNaturewatch-{unique_id.strip().decode('utf-8')[-8:]}"

#if unique_ssid == current_ssid:
#    print("Unique SSID already set, no further action is needed.")
#else:
print("Updating hotspot")
os.system("sudo iw reg set US")
os.system("sudo ifconfig wlan0 up")
os.system("sudo nmcli r wifi on") 
os.system("sudo nmcli device wifi hotspot ssid " + unique_ssid + " password badgersandfoxes ifname wlan0")
