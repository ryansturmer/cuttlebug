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
            self._bind(app.EVT_APP_PROJECT_CLOSED, "on_project_close")
            self._bind(app.EVT_APP_PROJECT_OPENED, "on_project_open")
            self._bind(app.EVT_APP_TARGET_CONNECTED, "on_target_connected")
            self._bind(app.EVT_APP_TARGET_DISCONNECTED, "on_target_disconnected")
            self._bind(app.EVT_APP_TARGET_RUNNING, "on_target_running")
            self._bind(app.EVT_APP_TARGET_HALTED, "on_target_halted")

    def _bind(self, event, function_name):
        if hasattr(self, function_name) and self.controller:
            handler = getattr(self, "_%s" % function_name)
            self.controller.Bind(event, handler)
            
    def _on_project_open(self, evt):
        self.on_project_open(evt.data)
        evt.Skip()
    
    def _on_project_close(self, evt):
        self.on_project_close(evt.data)    

    def _on_target_connected(self, evt):
        self.on_target_connected()
        evt.Skip()
    def _on_target_disconnected(self, evt):
        self.on_target_disconnected()
        evt.Skip()    
    
    def _on_target_running(self, evt):
        self.on_target_running()
        evt.Skip()

    def _on_target_halted(self, evt):
        self.on_target_halted(evt.data[0], evt.data[1])
        evt.Skip() 
    
    