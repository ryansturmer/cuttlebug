import wx
import log

class ViewEvent(wx.PyEvent):
    def __init__(self, type, object=None, data=None):
        super(ViewEvent, self).__init__()
        self.SetEventType(type.typeId)
        self.SetEventObject(object)
        self.data = data


EVT_VIEW_REQUEST_UPDATE = wx.PyEventBinder(wx.NewEventType())
EVT_VIEW_POST_UPDATE = wx.PyEventBinder(wx.NewEventType())

class View(wx.Panel):
    pass
