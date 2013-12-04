#! /usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (C) 2011~2012 Deepin, Inc.
#               2011~2012 Kaisheng Ye
#
# Author:     Kaisheng Ye <kaisheng.ye@gmail.com>
# Maintainer: Kaisheng Ye <kaisheng.ye@gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os
import gtk
import pango
import apt_pkg
from datetime import datetime
import threading as td
import time
from tempfile import mkstemp
from zipfile import ZipFile

from dtk.ui.label import Label
from deepin_utils.config import Config
from deepin_utils.file import touch_file

from constant import (
        CONFIG_INFO_PATH, 
        DEFAULT_UPDATE_INTERVAL, 
        DEFAULT_DOWNLOAD_DIRECTORY, 
        DEFAULT_DOWNLOAD_NUMBER, 
        PROGRAM_NAME,
        dsc_root_dir,
        LANGUAGE
        )
from logger import newLogger
from nls import _

global_logger = newLogger('global')

LOG_PATH = "/tmp/dsc-frontend.log"
SYS_CONFIG_INFO_PATH = "/var/cache/deepin-software-center/config_info.ini"
BACKEND_PID = "/tmp/deepin-software-center/backend_running.pid"

def get_backend_running():
    return os.path.exists(BACKEND_PID)

def get_last_update_time():
    config = Config(SYS_CONFIG_INFO_PATH)

    if os.path.exists(SYS_CONFIG_INFO_PATH):
        config.load()
        if config.has_option("update", "last_update_time"):
            return config.get("update", "last_update_time")
        else:
            return ""
    else:
        return ""

def get_current_mirror_hostname():
    apt_pkg.init_config()
    apt_pkg.init_system()
    source_list_obj = apt_pkg.SourceList()
    source_list_obj.read_main_list()
    url = source_list_obj.list[0].uri
    hostname = url.split(":")[0] + "://" + url.split("/")[2]
    return hostname

def create_right_align_label(strings):
    return Label(strings, text_x_align=pango.ALIGN_RIGHT, text_size=10)

def create_left_align_label(strings):
    return Label(strings, text_size=10)

def create_align(init, padding):
    align = gtk.Alignment(*init)
    align.set_padding(*padding)
    return align

def sort_for_home_page_data(infos):
    new_infos = []
    new_infos.append(tuple(infos[0]))
    for i in xrange(len(infos)-1):
        new_infos.insert(0, tuple(infos[i+1]))

    # bubble sort
    number = len(new_infos)
    for i in xrange(number-1):
        for j in xrange(number-i-1):
            if (new_infos[j][1] < new_infos[j+1][1]):
                new_infos[j], new_infos[j+1] = new_infos[j+1], new_infos[j]
    return new_infos

def get_common_image(name):
    return os.path.join(dsc_root_dir, "image", name)

def get_common_locale_image(folder, name):
    locale_image = os.path.join(dsc_root_dir, "image", folder, LANGUAGE, name)
    if not os.path.exists(locale_image):
        locale_image = os.path.join(dsc_root_dir, "image", folder, name)
    return locale_image

def get_common_image_pixbuf(name):
    if os.path.exists(get_common_image(name)):
        return gtk.gdk.pixbuf_new_from_file(get_common_image(name))
    else:
        return None

def get_common_locale_image_pixbuf(folder, name):
    if os.path.exists(get_common_locale_image(folder, name)):
        return gtk.gdk.pixbuf_new_from_file(get_common_locale_image(folder, name))
    else:
        return None

def get_recommend_mode():

    recommend_modes = {
            'test' : '2',
            'publish' : '3',
            'archive' : '4',
            }

    config = get_config_info_config()
    if config.has_option("recommend", "mode"):
        mode = recommend_modes.get(config.get('recommend', 'mode'))
        if mode:
            return mode
        else:
            return '3'
    else:
        return '3'

def bit_to_human_str(size):
    if size < 1024:
        return "%sB" % size
    else:
        size = size/1024.0
        if size <= 1024:
            return "%.2fKB" % size
        else:
            size = size/1024.0
            if size <= 1024:
                return "%.2fMB" % size
            else:
                size = size/1024.0
                return "%.2fGB" % size

def write_log(message):
    if not os.path.exists(LOG_PATH):
        open(LOG_PATH, "w").close()
        os.chmod(LOG_PATH, 0777)
    with open(LOG_PATH, "a") as file_handler:
        now = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
        file_handler.write("%s %s\n" % (now, message))

def handle_dbus_reply(obj=None):
    global_logger.loginfo("Dbus Reply OK: %s", obj)
    
def handle_dbus_error(obj, error=None):
    global_logger.logerror("Dbus Reply Error: %s", obj)
    global_logger.logerror("ERROR MESSAGE: %s", error)

def is_64bit_system():
    if os.uname()[-1] == "x86_64":
        return True
    else:
        return False

def set_last_upgrade_time():
    config_info_config = get_config_info_config()
    config_info_config.set("upgrade", "last_upgrade_time", time.time())
    config_info_config.write()

def get_last_upgrade_time():
    config_info_config = get_config_info_config()
    if config_info_config.has_option("upgrade", "last_upgrade_time"):
        return config_info_config.get("upgrade", "last_upgrade_time")
    else:
        config_info_config.set("upgrade", "last_upgrade_time", "")
        config_info_config.write()
        return ""

def get_config_info_config():
    config_info_config = Config(CONFIG_INFO_PATH)

    if os.path.exists(CONFIG_INFO_PATH):
        config_info_config.load()
    else:
        touch_file(CONFIG_INFO_PATH)
        config_info_config.load()

    return config_info_config

def is_first_started():
    config = get_config_info_config()
    return not config.has_option("settings" , "first_started")

def set_first_started():
    config = get_config_info_config()
    config.set("settings", "first_started", "false")    
    config.write()

def get_purg_flag():
    config = get_config_info_config()
    if config.has_option('uninstall', 'purge'):
        flag = config.get('uninstall', 'purge')
        if isinstance(flag, str):
            return eval(flag)
        else:
            return flag
    else:
        config.set('uninstall', 'purge', False)
        config.write()
        return False

def set_purge_flag(value):
    config = get_config_info_config()
    config.set('uninstall', 'purge', value)
    config.write()

def get_config_info(section, key):
    config = get_config_info_config()
    if config.has_option(section, key):
        return config.get(section, key)
    else:
        return None

def set_config_info(section, key, value):
    config = get_config_info_config()
    config.set(section, key, value)
    config.write()

def is_auto_update():
    config_info_config = get_config_info_config()
    if config_info_config.has_option('update', 'auto'):
        if config_info_config.get('update', 'auto') == 'False':
            return False
        else:
            return True
    else:
        return True

def set_auto_update(b):
    config_info_config = get_config_info_config()
    config_info_config.set('update', 'auto', b)
    config_info_config.write()

def get_update_interval():
    config_info_config = get_config_info_config()
    if config_info_config.has_option('update', 'interval'):
        return config_info_config.get('update', 'interval')
    else:
        return DEFAULT_UPDATE_INTERVAL

def set_update_interval(hour):
    config_info_config = get_config_info_config()
    config_info_config.set('update', 'interval', hour)
    config_info_config.write()

def get_software_download_dir():
    config_info_config = get_config_info_config()
    if config_info_config.has_option('download', 'directory'):
        return config_info_config.get('download', 'directory')
    else:
        return DEFAULT_DOWNLOAD_DIRECTORY
    
def set_software_download_dir(local_dir):
    config_info_config = get_config_info_config()
    config_info_config.set('download', 'directory', local_dir)
    config_info_config.write()

def get_download_number():
    config_info_config = get_config_info_config()
    if config_info_config.has_option('download', 'number'):
        return config_info_config.get('download', 'number')
    else:
        return DEFAULT_DOWNLOAD_NUMBER
    
def set_download_number(number):
    config_info_config = get_config_info_config()
    config_info_config.set('download', 'number', number)
    config_info_config.write()

header_ids = [
        "Running",
        "Preparing",
        "Unpacking",
        "Preparing to configure",
        "Configuring",
        "Installed",
        ]

header_ids_l18n = {
        "Running": _("Running"),
        "Preparing": _("Preparing"),
        "Unpacking": _("Unpacking"),
        "Preparing to configure": _("Preparing to configure"),
        "Configuring": _("Configuring"),
        "Installed":  _("Installed"),
        }

def l18n_status_info(status):
    for key in header_ids_l18n.keys():
        if status.startswith(key):
            return status.replace(key, header_ids_l18n[key])
    return status

update_header_ids = {
        "Err": _("Err"),
        "Ign": _("Ign"),
        "Get": _("Get"),
        "Hit": _("Hit"),
        }
def update_l18n_status_info(status):
    for key in update_header_ids.keys():
        if status.startswith(key):
            return status.replace(key, update_header_ids[key])
    return status

LOG_DICT = ["/tmp/dsc-backend.log", "/tmp/dsc-frontend.log"]
def generate_log_tar():
    tmp = mkstemp(".zip", PROGRAM_NAME)
    os.close(tmp[0])
    filename = tmp[1]
    with ZipFile(filename, 'w') as myzip:
        for log in LOG_DICT:
            if os.path.exists(log):
                myzip.write(log)
    return filename

class ThreadMethod(td.Thread):
    '''
    func: a method name
    args: arguments tuple
    '''
    def __init__(self, func, args, daemon=False):
        td.Thread.__init__(self)
        self.func = func
        self.args = args
        self.setDaemon(daemon)

    def run(self):
        self.func(*self.args)

if __name__ == '__main__':
    print update_l18n_status_info("Ign http://test.packages.linuxdeepin.com raring/universe Translation-en")
