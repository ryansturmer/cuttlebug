import threading, subprocess
import wx
import app
import prefs
import os
from subprocess import *
import util

class BuildEvent(wx.PyEvent):
    def __init__(self, type, object=None, data=None):
        super(BuildEvent, self).__init__()
        self.SetEventType(type.typeId)
        self.SetEventObject(object)
        self.data = data

EVT_BUILD_STARTED = wx.PyEventBinder(wx.NewEventType())
EVT_BUILD_FINISHED = wx.PyEventBinder(wx.NewEventType())
EVT_BUILD_UPDATE = wx.PyEventBinder(wx.NewEventType())
EVT_BUILD_CATASTROPHE = wx.PyEventBinder(wx.NewEventType())

class BuildProcess(util.Process):

    def __init__(self, cmd, cwd=os.curdir, notify=None):
        self.cmd = str(cmd)
        self.notify = notify
        super(BuildProcess, self).__init__(cmd, start=self.on_start, stdout=self.on_stdout, stderr=self.on_stderr, end=self.on_end, cwd=cwd) 

    def post_event(self, evt):
        if self.notify:
            wx.PostEvent(self.notify, evt)

    def on_start(self):
        self.post_event(BuildEvent(EVT_BUILD_STARTED, self.notify))

    def on_stdout(self, data):
        self.post_event(BuildEvent(EVT_BUILD_UPDATE, self.notify, data=data))
        
    def on_stderr(self, data):
        self.post_event(BuildEvent(EVT_BUILD_UPDATE, self.notify, data=data))

    def on_end(self):
        self.post_event(BuildEvent(EVT_BUILD_FINISHED, self.notify))
