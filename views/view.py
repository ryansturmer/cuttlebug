import wx
import log
import app

class ViewEvent(wx.PyEvent):
    def __init__(self, type, object=None, data=None):
        super(ViewEvent, self).__init__()
        self.SetEventType(type.typeId)
        self.SetEventObject(object)
        self.data = data


EVT_VIEW_REQUEST_UPDATE = wx.PyEventBinder(wx.NewEventType())
EVT_VIEW_POST_UPDATE = wx.PyEventBinder(wx.NewEventType())

class View(wx.Panel):
    
    def __init__(self, *args, **kwargs):
        self.controller = kwargs.pop('controller', None)
        super(View, self).__init__(*args, **kwargs)
        if self.controller:
            self.controller.Bind(app.EVT_APP_PROJECT_CLOSED, self._on_project_close)
            self.controller.Bind(app.EVT_APP_PROJECT_OPENED, self._on_project_open)
            self.controller.Bind(app.EVT_APP_TARGET_CONNECTED, self._target_connected)
            self.controller.Bind(app.EVT_APP_TARGET_DISCONNECTED, self._on_target_disconnected)
            self.controller.Bind(app.EVT_APP_TARGET_RUNNING, self._target_running)
            self.controller.Bind(app.EVT_APP_TARGET_HALTED, self._on_target_halted)

    def _on_project_open(self, evt):
        self.on_project_open(evt.data)
    def on_project_open(self, project):
        pass
    
    def _on_project_close(self, evt):
        self.on_project_close(evt.data)    
    def on_project_close(self, project):
        pass

    def _on_target_connected(self, evt):
        self.on_target_connected()
    def on_target_connected(self):
        pass
    def _on_target_disconnected(self, evt):
        self.on_target_disconnected()    
    def on_target_disconnected(self):
        pass
    
    def _on_target_running(self, evt):
        self.on_target_running()
    def on_target_running(self):
        pass

    def _on_target_halted(self, evt):
        self.on_target_halted(evt.data[0], evt.data[1])    
    def on_target_halted(self, filename, line):
        pass
    
    