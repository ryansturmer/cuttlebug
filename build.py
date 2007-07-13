import threading, subprocess
import wx
import app
import prefs
import os
from subprocess import *

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

class BuildSubProcess(object):
    def __init__(self, cmd, working_directory=os.curdir, notify=None):
        self.cmd = cmd
        self.working_directory = working_directory
        self.notify = notify
        self.process = None

    def post_update(self, text):
        if self.notify:
            wx.PostEvent(self.notify, BuildEvent(EVT_BUILD_UPDATE, self, data=text))

    def start(self):
        try:
            self.process = Popen(cmd, stdout=PIPE, shell=True)
            if self.notify:
                wx.PostEvent(self.notify, BuildEvent(EVT_BUILD_STARTED, self))
        except Exception,e:
            if self.notify:
                wx.PostEvent(self.notify, BuildEvent(EVT_BUILD_CATASTROPHE, self, data=e))
            raise


    def finish(self):
        if self.notify:
            wx.PostEvent(self.notify, BuildEvent(EVT_BUILD_FINISHED, self))

class BuildProcess(wx.Process):

    def __init__(self, cmd, working_directory=os.curdir, notify=None):
        wx.Process.__init__(self, notify)
        self.Redirect()
        self.cmd = "%s" % (cmd,)
        self.pid = None
        self.timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.on_timer)
    
    def start(self):
        wx.PostEvent(self, BuildEvent(EVT_BUILD_STARTED, self))
        try:
            self.pid = wx.Execute(self.cmd, wx.EXEC_ASYNC, self)
        except Exception, e:
            print e
            return
        self.timer.Start(100)

    def on_timer(self, evt):
        stream = self.GetInputStream()
        if stream.CanRead():
            text = stream.read()
            wx.PostEvent(self, BuildEvent(EVT_BUILD_UPDATE, self, data=text))


    def OnTerminate(self, *args, **kwargs):
        stream = self.GetInputStream()
        if stream.CanRead():
            text = stream.read()
            wx.PostEvent(self, BuildEvent(EVT_BUILD_UPDATE, self, data=text))
        if self.timer:
            self.timer.Stop()
        wx.PostEvent(self, BuildEvent(EVT_BUILD_FINISHED, self))
