import wx
import log
import app
import gdb


class View(wx.Panel):
    
    def __init__(self, *args, **kwargs):
        self.controller = kwargs.pop('controller', None)
        super(View, self).__init__(*args, **kwargs)
        self.model = None
        '''
        if self.controller:
            self._bind(app.EVT_APP_PROJECT_CLOSED, "on_project_close")
            self._bind(app.EVT_APP_PROJECT_OPENED, "on_project_open")
            self._bind(app.EVT_APP_TARGET_CONNECTED, "on_target_connected")
            self._bind(app.EVT_APP_TARGET_DISCONNECTED, "on_target_disconnected")
            self._bind(app.EVT_APP_TARGET_RUNNING, "on_target_running")
            self._bind(app.EVT_APP_TARGET_HALTED, "on_target_halted")
            
#            self._bind(gdb.EVT_GDB_UPDATE_BREAKPOINTS, "on_breakpoint_update")
#            self._bind(gdb.EVT_GDB_UPDATE_LOCALS, "on_locals_update")
        '''
    def set_model(self, model):
        self.model = model
        
    def _bind(self, event, function_name):
        if hasattr(self, function_name) and self.controller:
            handler = getattr(self, "_%s" % function_name)
            self.controller.Bind(event, handler)

    def _on_breakpoint_update(self, evt):
        self.on_breakpoint_update(evt.data)
        evt.Skip()

    def _on_locals_update(self, evt):
        self.on_locals_update(evt.data)
        evt.Skip()
            
    def _on_project_open(self, evt):
        self.on_project_open(evt.data)
        evt.Skip()
    
    def _on_project_close(self, evt):
        self.on_project_close(evt.data)    
        evt.Skip()
        
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
    
    