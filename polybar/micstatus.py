#!/usr/bin/env python3

VERSION = '1.5.1'

import time
import curses
import functools
import getopt
import operator
import os
import re
import signal
import sys
import threading
import traceback
from collections import OrderedDict
from configparser import ConfigParser
# from ctypes import *
import ctypes as C
from itertools import takewhile
from pprint import pprint
from select import select
from shutil import get_terminal_size
from textwrap import dedent
from time import sleep
from unicodedata import east_asian_width
from queue import Queue
#########################################################################################
# v bindings

try:
    DLL = C.CDLL("libpulse.so.0")
except Exception as e:
    sys.exit(e)

PA_VOLUME_NORM = 65536
PA_CHANNELS_MAX = 32
PA_USEC_T = C.c_uint64
PA_CONTEXT_READY = 4
PA_CONTEXT_FAILED = 5
PA_SUBSCRIPTION_MASK_ALL = 0x02ff


class Struct(C.Structure): pass
PA_PROPLIST = PA_OPERATION = PA_CONTEXT = PA_THREADED_MAINLOOP = PA_MAINLOOP_API = Struct


class PA_SAMPLE_SPEC(C.Structure):
    _fields_ = [
        ("format",      C.c_int),
        ("rate",        C.c_uint32),
        ("channels",    C.c_uint32)
    ]


class PA_CHANNEL_MAP(C.Structure):
    _fields_ = [
        ("channels",    C.c_uint8),
        ("map",         C.c_int * PA_CHANNELS_MAX)
    ]


class PA_CVOLUME(C.Structure):
    _fields_ = [
        ("channels",    C.c_uint8),
        ("values",      C.c_uint32 * PA_CHANNELS_MAX)
    ]


class PA_PORT_INFO(C.Structure):
    _fields_ = [
        ('name',        C.c_char_p),
        ('description', C.c_char_p),
        ('priority',    C.c_uint32),
        ("available",   C.c_int),
    ]


class PA_SINK_INPUT_INFO(C.Structure):
    _fields_ = [
        ("index",           C.c_uint32),
        ("name",            C.c_char_p),
        ("owner_module",    C.c_uint32),
        ("client",          C.c_uint32),
        ("sink",            C.c_uint32),
        ("sample_spec",     PA_SAMPLE_SPEC),
        ("channel_map",     PA_CHANNEL_MAP),
        ("volume",          PA_CVOLUME),
        ("buffer_usec",     PA_USEC_T),
        ("sink_usec",       PA_USEC_T),
        ("resample_method", C.c_char_p),
        ("driver",          C.c_char_p),
        ("mute",            C.c_int),
        ("proplist",        C.POINTER(PA_PROPLIST))
    ]


class PA_SINK_INFO(C.Structure):
    _fields_ = [
        ("name",                C.c_char_p),
        ("index",               C.c_uint32),
        ("description",         C.c_char_p),
        ("sample_spec",         PA_SAMPLE_SPEC),
        ("channel_map",         PA_CHANNEL_MAP),
        ("owner_module",        C.c_uint32),
        ("volume",              PA_CVOLUME),
        ("mute",                C.c_int),
        ("monitor_source",      C.c_uint32),
        ("monitor_source_name", C.c_char_p),
        ("latency",             PA_USEC_T),
        ("driver",              C.c_char_p),
        ("flags",               C.c_int),
        ("proplist",            C.POINTER(PA_PROPLIST)),
        ("configured_latency",  PA_USEC_T),
        ('base_volume',         C.c_int),
        ('state',               C.c_int),
        ('n_volume_steps',      C.c_int),
        ('card',                C.c_uint32),
        ('n_ports',             C.c_uint32),
        ('ports',               C.POINTER(C.POINTER(PA_PORT_INFO))),
        ('active_port',         C.POINTER(PA_PORT_INFO))
    ]


class PA_SOURCE_OUTPUT_INFO(C.Structure):
    _fields_ = [
        ("index",           C.c_uint32),
        ("name",            C.c_char_p),
        ("owner_module",    C.c_uint32),
        ("client",          C.c_uint32),
        ("source",          C.c_uint32),
        ("sample_spec",     PA_SAMPLE_SPEC),
        ("channel_map",     PA_CHANNEL_MAP),
        ("buffer_usec",     PA_USEC_T),
        ("source_usec",     PA_USEC_T),
        ("resample_method", C.c_char_p),
        ("driver",          C.c_char_p),
        ("proplist",        C.POINTER(PA_PROPLIST)),
        ("corked",          C.c_int),
        ("volume",          PA_CVOLUME),
        ("mute",            C.c_int),
    ]


class PA_SOURCE_INFO(C.Structure):
    _fields_ = [
        ("name",                 C.c_char_p),
        ("index",                C.c_uint32),
        ("description",          C.c_char_p),
        ("sample_spec",          PA_SAMPLE_SPEC),
        ("channel_map",          PA_CHANNEL_MAP),
        ("owner_module",         C.c_uint32),
        ("volume",               PA_CVOLUME),
        ("mute",                 C.c_int),
        ("monitor_of_sink",      C.c_uint32),
        ("monitor_of_sink_name", C.c_char_p),
        ("latency",              PA_USEC_T),
        ("driver",               C.c_char_p),
        ("flags",                C.c_int),
        ("proplist",             C.POINTER(PA_PROPLIST)),
        ("configured_latency",   PA_USEC_T),
        ('base_volume',          C.c_int),
        ('state',                C.c_int),
        ('n_volume_steps',       C.c_int),
        ('card',                 C.c_uint32),
        ('n_ports',              C.c_uint32),
        ('ports',                C.POINTER(C.POINTER(PA_PORT_INFO))),
        ('active_port',          C.POINTER(PA_PORT_INFO))
    ]


class PA_CLIENT_INFO(C.Structure):
    _fields_ = [
        ("index",        C.c_uint32),
        ("name",         C.c_char_p),
        ("owner_module", C.c_uint32),
        ("driver",       C.c_char_p)
    ]


class PA_CARD_PROFILE_INFO(C.Structure):
    _fields_ = [
        ('name',        C.c_char_p),
        ('description', C.c_char_p),
        ('n_sinks',     C.c_uint32),
        ('n_sources',   C.c_uint32),
        ('priority',    C.c_uint32),
    ]


class PA_CARD_PROFILE_INFO2(C.Structure):
    _fields_ = PA_CARD_PROFILE_INFO._fields_ + [('available',   C.c_int)]


class PA_CARD_INFO(C.Structure):
    _fields_ = [
        ('index',           C.c_uint32),
        ('name',            C.c_char_p),
        ('owner_module',    C.c_uint32),
        ('driver',          C.c_char_p),
        ('n_profiles',      C.c_uint32),
        ('profiles',        C.POINTER(PA_CARD_PROFILE_INFO)),
        ('active_profile',  C.POINTER(PA_CARD_PROFILE_INFO)),
        ('proplist',        C.POINTER(PA_PROPLIST)),
        ('n_ports',         C.c_uint32),
        ('ports',           C.POINTER(C.POINTER(C.c_void_p))),
        ('profiles2',       C.POINTER(C.POINTER(PA_CARD_PROFILE_INFO2))),
        ('active_profile2', C.POINTER(PA_CARD_PROFILE_INFO2))
    ]


class PA_SERVER_INFO(C.Structure):
    _fields_ = [
        ('user_name',           C.c_char_p),
        ('host_name',           C.c_char_p),
        ('server_version',      C.c_char_p),
        ('server_name',         C.c_char_p),
        ('sample_spec',         PA_SAMPLE_SPEC),
        ('default_sink_name',   C.c_char_p),
        ('default_source_name', C.c_char_p),
    ]


PA_STATE_CB_T              = C.CFUNCTYPE(C.c_int, C.POINTER(PA_CONTEXT), C.c_void_p)
PA_CLIENT_INFO_CB_T        = C.CFUNCTYPE(C.c_void_p, C.POINTER(PA_CONTEXT), C.POINTER(PA_CLIENT_INFO), C.c_int, C.c_void_p)
PA_SINK_INPUT_INFO_CB_T    = C.CFUNCTYPE(C.c_int, C.POINTER(PA_CONTEXT), C.POINTER(PA_SINK_INPUT_INFO), C.c_int, C.c_void_p)
PA_SINK_INFO_CB_T          = C.CFUNCTYPE(C.c_int, C.POINTER(PA_CONTEXT), C.POINTER(PA_SINK_INFO), C.c_int, C.c_void_p)
PA_SOURCE_OUTPUT_INFO_CB_T = C.CFUNCTYPE(C.c_int, C.POINTER(PA_CONTEXT), C.POINTER(PA_SOURCE_OUTPUT_INFO), C.c_int, C.c_void_p)
PA_SOURCE_INFO_CB_T        = C.CFUNCTYPE(C.c_int, C.POINTER(PA_CONTEXT), C.POINTER(PA_SOURCE_INFO), C.c_int, C.c_void_p)
PA_CONTEXT_SUCCESS_CB_T    = C.CFUNCTYPE(C.c_void_p, C.POINTER(PA_CONTEXT), C.c_int, C.c_void_p)
PA_CARD_INFO_CB_T          = C.CFUNCTYPE(None, C.POINTER(PA_CONTEXT), C.POINTER(PA_CARD_INFO), C.c_int, C.c_void_p)
PA_SERVER_INFO_CB_T        = C.CFUNCTYPE(None, C.POINTER(PA_CONTEXT), C.POINTER(PA_SERVER_INFO), C.c_void_p)
PA_CONTEXT_SUBSCRIBE_CB_T  = C.CFUNCTYPE(C.c_void_p, C.POINTER(PA_CONTEXT), C.c_int, C.c_int, C.c_void_p)

pa_threaded_mainloop_new = DLL.pa_threaded_mainloop_new
pa_threaded_mainloop_new.restype = C.POINTER(PA_THREADED_MAINLOOP)
pa_threaded_mainloop_new.argtypes = []

pa_threaded_mainloop_free = DLL.pa_threaded_mainloop_free
pa_threaded_mainloop_free.restype = C.c_void_p
pa_threaded_mainloop_free.argtypes = [C.POINTER(PA_THREADED_MAINLOOP)]

pa_threaded_mainloop_start = DLL.pa_threaded_mainloop_start
pa_threaded_mainloop_start.restype = C.c_int
pa_threaded_mainloop_start.argtypes = [C.POINTER(PA_THREADED_MAINLOOP)]

pa_threaded_mainloop_stop = DLL.pa_threaded_mainloop_stop
pa_threaded_mainloop_stop.restype = None
pa_threaded_mainloop_stop.argtypes = [C.POINTER(PA_THREADED_MAINLOOP)]

pa_threaded_mainloop_lock = DLL.pa_threaded_mainloop_lock
pa_threaded_mainloop_lock.restype = None
pa_threaded_mainloop_lock.argtypes = [C.POINTER(PA_THREADED_MAINLOOP)]

pa_threaded_mainloop_unlock = DLL.pa_threaded_mainloop_unlock
pa_threaded_mainloop_unlock.restype = None
pa_threaded_mainloop_unlock.argtypes = [C.POINTER(PA_THREADED_MAINLOOP)]

pa_threaded_mainloop_wait = DLL.pa_threaded_mainloop_wait
pa_threaded_mainloop_wait.restype = None
pa_threaded_mainloop_wait.argtypes = [C.POINTER(PA_THREADED_MAINLOOP)]

pa_threaded_mainloop_signal = DLL.pa_threaded_mainloop_signal
pa_threaded_mainloop_signal.restype = None
pa_threaded_mainloop_signal.argtypes = [C.POINTER(PA_THREADED_MAINLOOP), C.c_int]

pa_threaded_mainloop_get_api = DLL.pa_threaded_mainloop_get_api
pa_threaded_mainloop_get_api.restype = C.POINTER(PA_MAINLOOP_API)
pa_threaded_mainloop_get_api.argtypes = [C.POINTER(PA_THREADED_MAINLOOP)]

pa_context_errno = DLL.pa_context_errno
pa_context_errno.restype = C.c_int
pa_context_errno.argtypes = [C.POINTER(PA_CONTEXT)]

pa_context_new_with_proplist = DLL.pa_context_new_with_proplist
pa_context_new_with_proplist.restype = C.POINTER(PA_CONTEXT)
pa_context_new_with_proplist.argtypes = [C.POINTER(PA_MAINLOOP_API), C.c_char_p, C.POINTER(PA_PROPLIST)]

pa_context_unref = DLL.pa_context_unref
pa_context_unref.restype = None
pa_context_unref.argtypes = [C.POINTER(PA_CONTEXT)]

pa_context_set_state_callback = DLL.pa_context_set_state_callback
pa_context_set_state_callback.restype = None
pa_context_set_state_callback.argtypes = [C.POINTER(PA_CONTEXT), PA_STATE_CB_T, C.c_void_p]

pa_context_connect = DLL.pa_context_connect
pa_context_connect.restype = C.c_int
pa_context_connect.argtypes = [C.POINTER(PA_CONTEXT), C.c_char_p, C.c_int, C.POINTER(C.c_int)]

pa_context_get_state = DLL.pa_context_get_state
pa_context_get_state.restype = C.c_int
pa_context_get_state.argtypes = [C.POINTER(PA_CONTEXT)]

pa_context_disconnect = DLL.pa_context_disconnect
pa_context_disconnect.restype = C.c_int
pa_context_disconnect.argtypes = [C.POINTER(PA_CONTEXT)]

pa_operation_unref = DLL.pa_operation_unref
pa_operation_unref.restype = None
pa_operation_unref.argtypes = [C.POINTER(PA_OPERATION)]

pa_context_subscribe = DLL.pa_context_subscribe
pa_context_subscribe.restype = C.POINTER(PA_OPERATION)
pa_context_subscribe.argtypes = [C.POINTER(PA_CONTEXT), C.c_int, PA_CONTEXT_SUCCESS_CB_T, C.c_void_p]

pa_context_set_subscribe_callback = DLL.pa_context_set_subscribe_callback
pa_context_set_subscribe_callback.restype = None
pa_context_set_subscribe_callback.args = [C.POINTER(PA_CONTEXT), PA_CONTEXT_SUBSCRIBE_CB_T, C.c_void_p]

pa_proplist_new = DLL.pa_proplist_new
pa_proplist_new.restype = C.POINTER(PA_PROPLIST)

pa_proplist_sets = DLL.pa_proplist_sets
pa_proplist_sets.argtypes = [C.POINTER(PA_PROPLIST), C.c_char_p, C.c_char_p]

pa_proplist_gets = DLL.pa_proplist_gets
pa_proplist_gets.restype = C.c_char_p
pa_proplist_gets.argtypes = [C.POINTER(PA_PROPLIST), C.c_char_p]

pa_proplist_free = DLL.pa_proplist_free
pa_proplist_free.argtypes = [C.POINTER(PA_PROPLIST)]

pa_context_get_sink_input_info_list = DLL.pa_context_get_sink_input_info_list
pa_context_get_sink_input_info_list.restype = C.POINTER(PA_OPERATION)
pa_context_get_sink_input_info_list.argtypes = [C.POINTER(PA_CONTEXT), PA_SINK_INPUT_INFO_CB_T, C.c_void_p]

pa_context_get_sink_info_list = DLL.pa_context_get_sink_info_list
pa_context_get_sink_info_list.restype = C.POINTER(PA_OPERATION)
pa_context_get_sink_info_list.argtypes = [C.POINTER(PA_CONTEXT), PA_SINK_INFO_CB_T, C.c_void_p]

pa_context_set_sink_mute_by_index = DLL.pa_context_set_sink_mute_by_index
pa_context_set_sink_mute_by_index.restype = C.POINTER(PA_OPERATION)
pa_context_set_sink_mute_by_index.argtypes = [C.POINTER(PA_CONTEXT), C.c_uint32, C.c_int, PA_CONTEXT_SUCCESS_CB_T, C.c_void_p]

pa_context_suspend_sink_by_index = DLL.pa_context_suspend_sink_by_index
pa_context_suspend_sink_by_index.restype = C.POINTER(PA_OPERATION)
pa_context_suspend_sink_by_index.argtypes = [C.POINTER(PA_CONTEXT), C.c_uint32, C.c_int, PA_CONTEXT_SUCCESS_CB_T, C.c_void_p]

pa_context_set_sink_port_by_index = DLL.pa_context_set_sink_port_by_index
pa_context_set_sink_port_by_index.restype = C.POINTER(PA_OPERATION)
pa_context_set_sink_port_by_index.argtypes = [C.POINTER(PA_CONTEXT), C.c_uint32, C.c_char_p, PA_CONTEXT_SUCCESS_CB_T, C.c_void_p]

pa_context_set_sink_input_mute = DLL.pa_context_set_sink_input_mute
pa_context_set_sink_input_mute.restype = C.POINTER(PA_OPERATION)
pa_context_set_sink_input_mute.argtypes = [C.POINTER(PA_CONTEXT), C.c_uint32, C.c_int, PA_CONTEXT_SUCCESS_CB_T, C.c_void_p]

pa_context_set_sink_volume_by_index = DLL.pa_context_set_sink_volume_by_index
pa_context_set_sink_volume_by_index.restype = C.POINTER(PA_OPERATION)
pa_context_set_sink_volume_by_index.argtypes = [C.POINTER(PA_CONTEXT), C.c_uint32, C.POINTER(PA_CVOLUME), PA_CONTEXT_SUCCESS_CB_T, C.c_void_p]

pa_context_set_sink_input_volume = DLL.pa_context_set_sink_input_volume
pa_context_set_sink_input_volume.restype = C.POINTER(PA_OPERATION)
pa_context_set_sink_input_volume.argtypes = [C.POINTER(PA_CONTEXT), C.c_uint32, C.POINTER(PA_CVOLUME), PA_CONTEXT_SUCCESS_CB_T, C.c_void_p]

pa_context_move_sink_input_by_index = DLL.pa_context_move_sink_input_by_index
pa_context_move_sink_input_by_index.restype = C.POINTER(PA_OPERATION)
pa_context_move_sink_input_by_index.argtypes = [C.POINTER(PA_CONTEXT), C.c_uint32, C.c_uint32, PA_CONTEXT_SUCCESS_CB_T, C.c_void_p]

pa_context_set_default_sink = DLL.pa_context_set_default_sink
pa_context_set_default_sink.restype = C.POINTER(PA_OPERATION)
pa_context_set_default_sink.argtypes = [C.POINTER(PA_CONTEXT), C.c_char_p, PA_CONTEXT_SUCCESS_CB_T, C.c_void_p]

pa_context_kill_sink_input = DLL.pa_context_kill_sink_input
pa_context_kill_sink_input.restype = C.POINTER(PA_OPERATION)
pa_context_kill_sink_input.argtypes = [C.POINTER(PA_CONTEXT), C.c_uint32, PA_CONTEXT_SUCCESS_CB_T, C.c_void_p]

pa_context_kill_client = DLL.pa_context_kill_client
pa_context_kill_client.restype = C.POINTER(PA_OPERATION)
pa_context_kill_client.argtypes = [C.POINTER(PA_CONTEXT), C.c_uint32, PA_CONTEXT_SUCCESS_CB_T, C.c_void_p]

pa_context_get_source_output_info_list = DLL.pa_context_get_source_output_info_list
pa_context_get_source_output_info_list.restype = C.POINTER(PA_OPERATION)
pa_context_get_source_output_info_list.argtypes = [C.POINTER(PA_CONTEXT), PA_SOURCE_OUTPUT_INFO_CB_T, C.c_void_p]

pa_context_move_source_output_by_index = DLL.pa_context_move_source_output_by_index
pa_context_move_source_output_by_index.restype = C.POINTER(PA_OPERATION)
pa_context_move_source_output_by_index.argtypes = [C.POINTER(PA_CONTEXT), C.c_uint32, C.c_uint32, PA_CONTEXT_SUCCESS_CB_T, C.c_void_p]

pa_context_set_source_output_volume = DLL.pa_context_set_source_output_volume
pa_context_set_source_output_volume.restype = C.POINTER(PA_OPERATION)
pa_context_set_source_output_volume.argtypes = [C.POINTER(PA_CONTEXT), C.c_uint32, C.POINTER(PA_CVOLUME), PA_CONTEXT_SUCCESS_CB_T, C.c_void_p]

pa_context_set_source_output_mute = DLL.pa_context_set_source_output_mute
pa_context_set_source_output_mute.restype = C.POINTER(PA_OPERATION)
pa_context_set_source_output_mute.argtypes = [C.POINTER(PA_CONTEXT), C.c_uint32, C.c_int, PA_CONTEXT_SUCCESS_CB_T, C.c_void_p]

pa_context_get_source_info_list = DLL.pa_context_get_source_info_list
pa_context_get_source_info_list.restype = C.POINTER(PA_OPERATION)
pa_context_get_source_info_list.argtypes = [C.POINTER(PA_CONTEXT), PA_SOURCE_INFO_CB_T, C.c_void_p]

pa_context_set_source_volume_by_index = DLL.pa_context_set_source_volume_by_index
pa_context_set_source_volume_by_index.restype = C.POINTER(PA_OPERATION)
pa_context_set_source_volume_by_index.argtypes = [C.POINTER(PA_CONTEXT), C.c_uint32, C.POINTER(PA_CVOLUME), PA_CONTEXT_SUCCESS_CB_T, C.c_void_p]

pa_context_set_source_mute_by_index = DLL.pa_context_set_source_mute_by_index
pa_context_set_source_mute_by_index.restype = C.POINTER(PA_OPERATION)
pa_context_set_source_mute_by_index.argtypes = [C.POINTER(PA_CONTEXT), C.c_uint32, C.c_int, PA_CONTEXT_SUCCESS_CB_T, C.c_void_p]

pa_context_suspend_source_by_index = DLL.pa_context_suspend_source_by_index
pa_context_suspend_source_by_index.restype = C.POINTER(PA_OPERATION)
pa_context_suspend_source_by_index.argtypes = [C.POINTER(PA_CONTEXT), C.c_uint32, C.c_int, PA_CONTEXT_SUCCESS_CB_T, C.c_void_p]

pa_context_set_source_port_by_index = DLL.pa_context_set_source_port_by_index
pa_context_set_source_port_by_index.restype = C.POINTER(PA_OPERATION)
pa_context_set_source_port_by_index.argtypes = [C.POINTER(PA_CONTEXT), C.c_uint32, C.c_char_p, PA_CONTEXT_SUCCESS_CB_T, C.c_void_p]

pa_context_set_default_source = DLL.pa_context_set_default_source
pa_context_set_default_source.restype = C.POINTER(PA_OPERATION)
pa_context_set_default_source.argtypes = [C.POINTER(PA_CONTEXT), C.c_char_p, PA_CONTEXT_SUCCESS_CB_T, C.c_void_p]

pa_context_kill_source_output = DLL.pa_context_kill_source_output
pa_context_kill_source_output.restype = C.POINTER(PA_OPERATION)
pa_context_kill_source_output.argtypes = [C.POINTER(PA_CONTEXT), C.c_uint32, PA_CONTEXT_SUCCESS_CB_T, C.c_void_p]

pa_context_get_client_info_list = DLL.pa_context_get_client_info_list
pa_context_get_client_info_list.restype = C.POINTER(PA_OPERATION)
pa_context_get_client_info_list.argtypes = [C.POINTER(PA_CONTEXT), PA_CLIENT_INFO_CB_T, C.c_void_p]

pa_context_get_card_info_list = DLL.pa_context_get_card_info_list
pa_context_get_card_info_list.restype = C.POINTER(PA_OPERATION)
pa_context_get_card_info_list.argtypes = [C.POINTER(PA_CONTEXT), PA_CARD_INFO_CB_T, C.c_void_p]

pa_context_set_card_profile_by_index = DLL.pa_context_set_card_profile_by_index
pa_context_set_card_profile_by_index.restype = C.POINTER(PA_OPERATION)
pa_context_set_card_profile_by_index.argtypes = [C.POINTER(PA_CONTEXT), C.c_uint32, C.c_char_p, PA_CONTEXT_SUCCESS_CB_T, C.c_void_p]

pa_context_get_server_info = DLL.pa_context_get_server_info
pa_context_get_server_info.restype = C.POINTER(PA_OPERATION)
pa_context_get_server_info.argtypes = [C.POINTER(PA_CONTEXT), PA_SERVER_INFO_CB_T, C.c_void_p]

pa_get_library_version = DLL.pa_get_library_version
pa_get_library_version.restype = C.c_char_p
PA_MAJOR = int(pa_get_library_version().decode().split('.')[0])

# ^ bindings
#########################################################################################
# v lib


class DebugMixin():

    def debug(self):
        pprint(vars(self))


class PulsePort(DebugMixin):

    def __init__(self, pa_port):
        self.name = pa_port.name
        self.description = pa_port.description
        self.priority = pa_port.priority
        self.available = getattr(pa_port, "available", 0)
        if self.available == 1:  # 1 off, 0 n/a, 2 on
            self.description += b' / off'


class PulseServer(DebugMixin):

    def __init__(self, pa_server):
        self.default_sink_name = pa_server.default_sink_name
        self.default_source_name = pa_server.default_source_name
        self.server_version = pa_server.server_version


class PulseCardProfile(DebugMixin):

    def __init__(self, pa_profile):
        self.name = pa_profile.name
        self.description = pa_profile.description
        self.available = getattr(pa_profile, "available", 1)
        if not self.available:
            self.description += b' / off'


class PulseCard(DebugMixin):

    def __init__(self, pa_card):
        self.name = pa_card.name
        self.description = pa_proplist_gets(pa_card.proplist, b'device.description')
        self.index = pa_card.index
        self.driver = pa_card.driver
        self.owner_module = pa_card.owner_module
        self.n_profiles = pa_card.n_profiles
        if PA_MAJOR >= 5:
            self.profiles = [PulseCardProfile(pa_card.profiles2[n].contents) for n in range(self.n_profiles)]
            self.active_profile = PulseCardProfile(pa_card.active_profile2[0])
        else:  # fallback to legacy profile, for PA < 5.0 (March 2014)
            self.profiles = [PulseCardProfile(pa_card.profiles[n]) for n in range(self.n_profiles)]
            self.active_profile = PulseCardProfile(pa_card.active_profile[0])
        self.volume = type('volume', (object, ), {'channels': 1, 'values': [0, 0]})

    def __str__(self):
        return "Card-ID: {}, Name: {}".format(self.index, self.name.decode())


class PulseClient(DebugMixin):

    def __init__(self, pa_client):
        self.index = getattr(pa_client, "index", 0)
        self.name = getattr(pa_client, "name", pa_client)
        self.driver = getattr(pa_client, "driver", "default driver")
        self.owner_module = getattr(pa_client, "owner_module", -1)

    def __str__(self):
        return "Client-name: {}".format(self.name.decode())


class Pulse(DebugMixin):

    def __init__(self, client_name='libpulse', server_name=None, reconnect=False):
        self.error = None
        self.data = []
        self.operation = None
        self.connected = False
        self.client_name = client_name.encode()
        self.server_name = server_name

        self.pa_state_cb = PA_STATE_CB_T(self.state_cb)
        self.pa_subscribe_cb = self.pa_dc_cb = lambda: None
        self.pa_cbs = {'sink_input_list':    PA_SINK_INPUT_INFO_CB_T(self.sink_input_list_cb),
                       'source_output_list': PA_SOURCE_OUTPUT_INFO_CB_T(self.source_output_list_cb),
                       'sink_list':          PA_SINK_INFO_CB_T(self.sink_list_cb),
                       'source_list':        PA_SOURCE_INFO_CB_T(self.source_list_cb),
                       'server':             PA_SERVER_INFO_CB_T(self.server_cb),
                       'card_list':          PA_CARD_INFO_CB_T(self.card_list_cb),
                       'client_list':        PA_CLIENT_INFO_CB_T(self.client_list_cb),
                       'success':            PA_CONTEXT_SUCCESS_CB_T(self.context_success)}
        self.mainloop = pa_threaded_mainloop_new()
        self.mainloop_api = pa_threaded_mainloop_get_api(self.mainloop)

        proplist = pa_proplist_new()
        pa_proplist_sets(proplist, b'application.id', self.client_name)
        pa_proplist_sets(proplist, b'application.icon_name', b'audio-card')
        self.context = pa_context_new_with_proplist(self.mainloop_api, self.client_name, proplist)
        pa_context_set_state_callback(self.context, self.pa_state_cb, None)
        pa_proplist_free(proplist)

        if pa_context_connect(self.context, self.server_name, 0, None) < 0 or self.error:
            if not reconnect: sys.exit("Failed to connect to pulseaudio: Connection refused")
            else: return

        pa_threaded_mainloop_lock(self.mainloop)
        pa_threaded_mainloop_start(self.mainloop)
        if self.error and reconnect: return
        pa_threaded_mainloop_wait(self.mainloop) or pa_threaded_mainloop_unlock(self.mainloop)
        if self.error and reconnect: return
        elif self.error: sys.exit('Failed to connect to pulseaudio')
        self.connected = True

    def wait_and_unlock(self):
        pa_threaded_mainloop_wait(self.mainloop)
        pa_threaded_mainloop_unlock(self.mainloop)
        pa_operation_unref(self.operation)

    def reconnect(self):
        if self.context:
            pa_context_disconnect(self.context)
            pa_context_unref(self.context)
        if self.mainloop:
            pa_threaded_mainloop_stop(self.mainloop)
            pa_threaded_mainloop_free(self.mainloop)
        self.__init__(self.client_name.decode(), self.server_name, reconnect=True)

    def unmute_stream(self, obj):
        if type(obj) is PulseSinkInfo:
            self.sink_mute(obj.index, 0)
        elif type(obj) is PulseSinkInputInfo:
            self.sink_input_mute(obj.index, 0)
        elif type(obj) is PulseSourceInfo:
            self.source_mute(obj.index, 0)
        elif type(obj) is PulseSourceOutputInfo:
            self.source_output_mute(obj.index, 0)
        obj.mute = 0

    def mute_stream(self, obj):
        if type(obj) is PulseSinkInfo:
            self.sink_mute(obj.index, 1)
        elif type(obj) is PulseSinkInputInfo:
            self.sink_input_mute(obj.index, 1)
        elif type(obj) is PulseSourceInfo:
            self.source_mute(obj.index, 1)
        elif type(obj) is PulseSourceOutputInfo:
            self.source_output_mute(obj.index, 1)
        obj.mute = 1

    def set_volume(self, obj, volume):
        if type(obj) is PulseSinkInfo:
            self.set_sink_volume(obj.index, volume)
        elif type(obj) is PulseSinkInputInfo:
            self.set_sink_input_volume(obj.index, volume)
        elif type(obj) is PulseSourceInfo:
            self.set_source_volume(obj.index, volume)
        elif type(obj) is PulseSourceOutputInfo:
            self.set_source_output_volume(obj.index, volume)
        obj.volume = volume

    def change_volume_mono(self, obj, inc):
        obj.volume.values = [v + inc for v in obj.volume.values]
        self.set_volume(obj, obj.volume)

    def get_volume_mono(self, obj):
        return int(sum(obj.volume.values) / len(obj.volume.values))

    def fill_clients(self):
        if not self.data:
            return None
        data, self.data = self.data, []
        clist = self.client_list()
        for d in data:
            for c in clist:
                if c.index == d.client_id:
                    d.client = c
                    break
        return data

    def state_cb(self, c, b):
        state = pa_context_get_state(c)
        if state == PA_CONTEXT_READY:
            pa_threaded_mainloop_signal(self.mainloop, 0)
        elif state == PA_CONTEXT_FAILED:
            self.error = RuntimeError("Failed to complete action: {}, {}".format(state, pa_context_errno(c)))
            self.connected = False
            pa_threaded_mainloop_signal(self.mainloop, 0)
            self.pa_dc_cb()
        return 0

    def _eof_cb(func):
        def wrapper(self, c, info, eof, *args):
            if eof:
                pa_threaded_mainloop_signal(self.mainloop, 0)
                return 0
            func(self, c, info, eof, *args)
            return 0
        return wrapper

    def _action_sync(func):
        def wrapper(self, *args):
            if self.error: raise self.error
            pa_threaded_mainloop_lock(self.mainloop)
            try:
                func(self, *args)
            except Exception as e:
                pa_threaded_mainloop_unlock(self.mainloop)
                raise e
            self.wait_and_unlock()
            if func.__name__ in ('sink_input_list', 'source_output_list'):
                self.data = self.fill_clients()
            data, self.data = self.data, []
            return data or []
        return wrapper

    @_eof_cb
    def card_list_cb(self, c, card_info, eof, userdata):
        self.data.append(PulseCard(card_info[0]))

    @_eof_cb
    def client_list_cb(self, c, client_info, eof, userdata):
        self.data.append(PulseClient(client_info[0]))

    @_eof_cb
    def sink_input_list_cb(self, c, sink_input_info, eof, userdata):
        self.data.append(PulseSinkInputInfo(sink_input_info[0]))

    @_eof_cb
    def sink_list_cb(self, c, sink_info, eof, userdata):
        self.data.append(PulseSinkInfo(sink_info[0]))

    @_eof_cb
    def source_output_list_cb(self, c, source_output_info, eof, userdata):
        self.data.append(PulseSourceOutputInfo(source_output_info[0]))

    @_eof_cb
    def source_list_cb(self, c, source_info, eof, userdata):
        self.data.append(PulseSourceInfo(source_info[0]))

    def server_cb(self, c, server_info, userdata):
        self.data = PulseServer(server_info[0])
        pa_threaded_mainloop_signal(self.mainloop, 0)

    def context_success(self, *_):
        pa_threaded_mainloop_signal(self.mainloop, 0)

    def subscribe(self, cb):
        self.pa_subscribe_cb, self.pa_dc_cb = PA_CONTEXT_SUBSCRIBE_CB_T(cb), cb
        pa_context_set_subscribe_callback(self.context, self.pa_subscribe_cb, None)
        pa_threaded_mainloop_lock(self.mainloop)
        self.operation = pa_context_subscribe(self.context, PA_SUBSCRIPTION_MASK_ALL, self.pa_cbs['success'], None)
        self.wait_and_unlock()

    @_action_sync
    def sink_input_list(self):
        self.operation = pa_context_get_sink_input_info_list(self.context, self.pa_cbs['sink_input_list'], None)

    @_action_sync
    def source_output_list(self):
        self.operation = pa_context_get_source_output_info_list(self.context, self.pa_cbs['source_output_list'], None)

    @_action_sync
    def sink_list(self):
        self.operation = pa_context_get_sink_info_list(self.context, self.pa_cbs['sink_list'], None)

    @_action_sync
    def source_list(self):
        self.operation = pa_context_get_source_info_list(self.context, self.pa_cbs['source_list'], None)

    @_action_sync
    def get_server_info(self):
        self.operation = pa_context_get_server_info(self.context, self.pa_cbs['server'], None)

    @_action_sync
    def card_list(self):
        self.operation = pa_context_get_card_info_list(self.context, self.pa_cbs['card_list'], None)

    @_action_sync
    def client_list(self):
        self.operation = pa_context_get_client_info_list(self.context, self.pa_cbs['client_list'], None)

    @_action_sync
    def sink_input_mute(self, index, mute):
        self.operation = pa_context_set_sink_input_mute(self.context, index, mute, self.pa_cbs['success'], None)

    @_action_sync
    def sink_input_move(self, index, s_index):
        self.operation = pa_context_move_sink_input_by_index(self.context, index, s_index, self.pa_cbs['success'], None)

    @_action_sync
    def sink_mute(self, index, mute):
        self.operation = pa_context_set_sink_mute_by_index(self.context, index, mute, self.pa_cbs['success'], None)

    @_action_sync
    def set_sink_input_volume(self, index, vol):
        self.operation = pa_context_set_sink_input_volume(self.context, index, vol.to_c(), self.pa_cbs['success'], None)

    @_action_sync
    def set_sink_volume(self, index, vol):
        self.operation = pa_context_set_sink_volume_by_index(self.context, index, vol.to_c(), self.pa_cbs['success'], None)

    @_action_sync
    def sink_suspend(self, index, suspend):
        self.operation = pa_context_suspend_sink_by_index(self.context, index, suspend, self.pa_cbs['success'], None)

    @_action_sync
    def set_default_sink(self, name):
        self.operation = pa_context_set_default_sink(self.context, name, self.pa_cbs['success'], None)

    @_action_sync
    def kill_sink(self, index):
        self.operation = pa_context_kill_sink_input(self.context, index, self.pa_cbs['success'], None)

    @_action_sync
    def kill_client(self, index):
        self.operation = pa_context_kill_client(self.context, index, self.pa_cbs['success'], None)

    @_action_sync
    def set_sink_port(self, index, port):
        self.operation = pa_context_set_sink_port_by_index(self.context, index, port, self.pa_cbs['success'], None)

    @_action_sync
    def set_source_output_volume(self, index, vol):
        self.operation = pa_context_set_source_output_volume(self.context, index, vol.to_c(), self.pa_cbs['success'], None)

    @_action_sync
    def set_source_volume(self, index, vol):
        self.operation = pa_context_set_source_volume_by_index(self.context, index, vol.to_c(), self.pa_cbs['success'], None)

    @_action_sync
    def source_suspend(self, index, suspend):
        self.operation = pa_context_suspend_source_by_index(self.context, index, suspend, self.pa_cbs['success'], None)

    @_action_sync
    def set_default_source(self, name):
        self.operation = pa_context_set_default_source(self.context, name, self.pa_cbs['success'], None)

    @_action_sync
    def kill_source(self, index):
        self.operation = pa_context_kill_source_output(self.context, index, self.pa_cbs['success'], None)

    @_action_sync
    def set_source_port(self, index, port):
        self.operation = pa_context_set_source_port_by_index(self.context, index, port, self.pa_cbs['success'], None)

    @_action_sync
    def source_output_mute(self, index, mute):
        self.operation = pa_context_set_source_output_mute(self.context, index, mute, self.pa_cbs['success'], None)

    @_action_sync
    def source_mute(self, index, mute):
        self.operation = pa_context_set_source_mute_by_index(self.context, index, mute, self.pa_cbs['success'], None)

    @_action_sync
    def source_output_move(self, index, s_index):
        self.operation = pa_context_move_source_output_by_index(self.context, index, s_index, self.pa_cbs['success'], None)

    @_action_sync
    def set_card_profile(self, index, p_index):
        self.operation = pa_context_set_card_profile_by_index(self.context, index, p_index, self.pa_cbs['success'], None)


class PulseSink(DebugMixin):

    def __init__(self, sink_info):
        self.index = sink_info.index
        self.name = sink_info.name
        self.mute = sink_info.mute
        self.volume = PulseVolume(sink_info.volume)


class PulseSinkInfo(PulseSink):

    def __init__(self, pa_sink_info):
        PulseSink.__init__(self, pa_sink_info)
        self.description = pa_sink_info.description
        self.owner_module = pa_sink_info.owner_module
        self.driver = pa_sink_info.driver
        self.monitor_source = pa_sink_info.monitor_source
        self.monitor_source_name = pa_sink_info.monitor_source_name
        self.n_ports = pa_sink_info.n_ports
        self.ports = [PulsePort(pa_sink_info.ports[i].contents) for i in range(self.n_ports)]
        self.active_port = None
        if self.n_ports:
            self.active_port = PulsePort(pa_sink_info.active_port.contents)

    def __str__(self):
        return "ID: sink-{}, Name: {}, Mute: {}, {}".format(self.index, self.description.decode(), self.mute, self.volume)


class PulseSinkInputInfo(PulseSink):

    def __init__(self, pa_sink_input_info):
        PulseSink.__init__(self, pa_sink_input_info)
        self.owner_module = pa_sink_input_info.owner_module
        self.client = PulseClient(pa_sink_input_info.name)
        self.client_id = pa_sink_input_info.client
        self.sink = self.owner = pa_sink_input_info.sink
        self.driver = pa_sink_input_info.driver
        self.media_name = pa_proplist_gets(pa_sink_input_info.proplist, b'media.name')

    def __str__(self):
        if self.client:
            return "ID: sink-input-{}, Name: {}, Mute: {}, {}".format(self.index, self.client.name.decode(), self.mute, self.volume)
        return "ID: sink-input-{}, Name: {}, Mute: {}".format(self.index, self.name.decode(), self.mute)


class PulseSource(DebugMixin):

    def __init__(self, source_info):
        self.index = source_info.index
        self.name = source_info.name
        self.mute = source_info.mute
        self.volume = PulseVolume(source_info.volume)


class PulseSourceInfo(PulseSource):

    def __init__(self, pa_source_info):
        PulseSource.__init__(self, pa_source_info)
        self.description = pa_source_info.description
        self.owner_module = pa_source_info.owner_module
        self.monitor_of_sink = pa_source_info.monitor_of_sink
        self.monitor_of_sink_name = pa_source_info.monitor_of_sink_name
        self.driver = pa_source_info.driver
        self.n_ports = pa_source_info.n_ports
        self.ports = [PulsePort(pa_source_info.ports[i].contents) for i in range(self.n_ports)]
        self.active_port = None
        if self.n_ports:
            self.active_port = PulsePort(pa_source_info.active_port.contents)

    def __str__(self):
        return "ID: source-{}, Name: {}, Mute: {}, {}".format(self.index, self.description.decode(), self.mute, self.volume)


class PulseSourceOutputInfo(PulseSource):

    def __init__(self, pa_source_output_info):
        PulseSource.__init__(self, pa_source_output_info)
        self.owner_module = pa_source_output_info.owner_module
        self.client = PulseClient(pa_source_output_info.name)
        self.client_id = pa_source_output_info.client
        self.source = self.owner = pa_source_output_info.source
        self.driver = pa_source_output_info.driver
        self.application_id = pa_proplist_gets(pa_source_output_info.proplist, b'application.id')

    def __str__(self):
        if self.client:
            return "ID: source-output-{}, Name: {}, Mute: {}, {}".format(self.index, self.client.name.decode(), self.mute, self.volume)
        return "ID: source-output-{}, Name: {}, Mute: {}".format(self.index, self.name.decode(), self.mute)


class PulseVolume(DebugMixin):

    def __init__(self, cvolume):
        self.channels = cvolume.channels
        self.values = [(round(x * 100 / PA_VOLUME_NORM)) for x in cvolume.values[:self.channels]]
        self.cvolume = PA_CVOLUME()
        self.cvolume.channels = self.channels

    def to_c(self):
        self.values = list(map(lambda x: max(min(x, 150), 0), self.values))
        for x in range(self.channels):
            self.cvolume.values[x] = round((self.values[x] * PA_VOLUME_NORM) / 100)
        return self.cvolume

    def __str__(self):
        return "Channels: {}, Volumes: {}".format(self.channels, [str(x) + "%" for x in self.values])


# ^ lib
#########################################################################################
# v main


class Bar():
    # should be in correct order
    LEFT, RIGHT, RLEFT, RRIGHT, CENTER, SUB, SLEFT, SRIGHT, NONE = range(9)

    def __init__(self, pa):
        if type(pa) is str:
            self.name = pa
            return
        if type(pa) in (PulseSinkInfo, PulseSourceInfo, PulseCard):
            self.fullname = pa.description.decode()
        else:
            self.fullname = pa.client.name.decode()
        self.name = re.sub(r'^ALSA plug-in \[|\]$', '', self.fullname.replace('|', ' '))
        for key in CFG.renames:
            if key.match(self.name):
                self.name = CFG.renames[key]
                break
        self.index = pa.index
        self.owner = -1
        self.stream_index = -1
        self.media_name, self.media_name_wide, self.media_name_widths = '', False, []
        self.poll_data(pa, 0, 0)
        self.maxsize = 150
        self.locked = True

    def poll_data(self, pa, owned, stream_index):
        self.channels = pa.volume.channels
        self.muted = getattr(pa, 'mute', False)
        self.owned = owned
        self.stream_index = stream_index
        self.volume = pa.volume.values
        if hasattr(pa, 'media_name'):
            media_fullname = pa.media_name.decode().replace('\n', ' ')
            media_name = ': {}'.format(media_fullname.replace('|', ' '))
            if media_fullname != self.fullname and media_name != self.media_name:
                self.media_name, self.media_name_wide = media_name, False
                if len(media_fullname) != len(pa.media_name):  # contains multi-byte chars which might be wide
                    self.media_name_widths = [int(east_asian_width(c) == 'W') + 1 for c in media_name]
                    self.media_name_wide = 2 in self.media_name_widths
        else:
            self.media_name, self.media_name_wide = '', False
        if type(pa) in (PulseSinkInputInfo, PulseSourceOutputInfo):
            self.owner = pa.owner
        self.pa = pa

    def mute_toggle(self):
        PULSE.unmute_stream(self.pa) if self.muted else PULSE.mute_stream(self.pa)

    def lock_toggle(self):
        self.locked = not self.locked

    def set(self, n, side):
        vol = self.pa.volume
        if self.locked:
            for i, _ in enumerate(vol.values):
                vol.values[i] = n
        else:
            vol.values[side] = n
        PULSE.set_volume(self.pa, vol)

    def move(self, n, side):
        vol = self.pa.volume
        if self.locked:
            for i, _ in enumerate(vol.values):
                vol.values[i] += n
        else:
            vol.values[side] += n
        PULSE.set_volume(self.pa, vol)

def printFlush(*a, **b):
    print(*a, **b)
    sys.stdout.flush()

sque = None
def subscribeCB(*a, **b):
    if sque is not None:
        sque.put((a, b))

def queuSleep():
    if sque is not None:
        sque.get()

def main():
    global sque
    sque = Queue()
    pulse = Pulse()
    pulse.subscribe(subscribeCB)
    images = [
            "%{T2}" + chr(0xe09f) + "%{T-} I", #computer
            "%{T2}" + chr(0xe0fd) + "%{T-} H", #headset
            "%{T4}" + chr(0x1F3A4) + "%{T-} P"
            ]
    ports_names = {
                "analog-input-internal-mic": "%{T2}" + chr(0xe09f) + "%{T-} I", #computer
                "analog-input-headset-mic": "%{T2}" + chr(0xe0fd) + "%{T-} H",
                "analog-input-headphone-mic": "%{T4}" + chr(0x1F3A4) + "%{T-} P"
            }
    while True:
        try:
            defSourceName = pulse.get_server_info().default_source_name
            source = [y for y in pulse.source_list() if y.name == defSourceName]
            if len(source) == 0:
                queuSleep()
                printFlush("")
                continue
            source = source[0]
            mute = source.mute
            vol = source.volume.values
            vol = sum(vol)/len(vol)
            vol = min(vol, 100)
#             active_port = source.active_port
#             if active_port is None:
#                 printFlush("")
#                 continue
            port = source.active_port.description
#             print(source.active_port.__dict__)
            pname = source.active_port.name.decode()
            foreground = "%{F#f00}" if mute else "%{F#0f0}"
            ppos = ['─'] * 11
            ppos[int((vol+5)/10)] = '|%{F-}'
            ppos = "".join(ppos)
            text = chr(0xe04c)
            if mute:
                ppos = foreground + ppos
            elif vol < 80:
                ppos = "%{F#55aa55}" + ppos
            elif vol < 90:
                ppos = "%{F#f5a70a}" + ppos
            else:
                ppos = "%{F#ff5555}" + ppos
            ppos = "%{F-}" + ppos
            #text += " %02d%%"%(vol)
            ptext = ports_names.get(pname, port.decode())
            printFlush(foreground + text, ptext, "%{T2}" + ppos + "%{T-}")
        except RuntimeError:
            pulse.reconnect()
            continue
        except AttributeError:
            printFlush("Error")
#             time.sleep(1)
#             continue
        queuSleep()


if __name__ == '__main__':
    main()
