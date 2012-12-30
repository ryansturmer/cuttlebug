import wx

def test_view(view_class, *args, **kwargs):
    app = wx.PySimpleApp()
    frame = wx.Frame(parent=None, title="View")
    view = view_class(frame, *args, **kwargs)
    app.SetTopWindow(frame)
    frame.Show()
    app.MainLoop()
