import wx
import wx.stc as stc
import wx.aui as aui
import controls
import log
import wx.grid as grid
import util

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

class RegisterView(View):
    
    def __init__(self, parent):
        super(RegisterView, self).__init__(parent, -1, style=wx.BORDER_STATIC, size=(800,150))
        self.list = controls.RegisterListControl(self, -1, style=wx.BORDER_NONE)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.list, 1, wx.EXPAND)
        self.SetSizer(sizer)

class BuildView(View):

    def __init__(self, parent):
        super(BuildView, self).__init__(parent, -1, style=wx.BORDER_STATIC, size=(800,150))
        self.txt = controls.BuildPortalControl(self, -1, style=wx.BORDER_NONE)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.txt, 1, wx.EXPAND)
        self.SetSizer(sizer)


    def update(self, new_text):
        self.txt.AddText(new_text)

    def clear(self):
        self.txt.SetText('')

class MemoryView(View):

    def __init__(self, parent, size=1048576, stride=4):
        super(MemoryView, self).__init__(parent, -1, style=wx.BORDER_STATIC, size=(300, 800))
        self.grid = controls.MemoryGridControl(self, -1, style=wx.BORDER_NONE, stride=stride, update_callable=self.on_cell_update)
        self.grid.Bind(wx.EVT_SCROLLWIN, self.on_scrolled) 
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.toolbar = wx.ToolBar(self, style=wx.TB_HORIZONTAL | wx.NO_BORDER)
        util.tool_item(self, self.toolbar, "Menu", func=None, icon="resultset_next.png")
        sizer.Add(self.toolbar,0, wx.EXPAND)
        sizer.Add(self.grid,1, wx.EXPAND)
        self.SetSizer(sizer)
    
    def __get_stride(self):
        return self.grid.stride

    def __set_stride(self, stride):
        self.grid.stride = stride

    stride = property(__get_stride, __set_stride)

    def update(self, base_addr, values):
        self.grid.update(base_addr, values)
    def request_update(self, range):
        evt = ViewEvent(EVT_VIEW_REQUEST_UPDATE, self, data=range)
        wx.PostEvent(self, evt)
        
    def on_cell_update(self, addr, value):
        print hex(addr) + "=" + str(value)

    def on_scrolled(self, evt):
        self.request_update(self.grid.visible_address_range())
        evt.Skip()

    def on_label_dclick(self, evt):
        print "Got label doubleclick"

    def update(self, base_addr, values):
        self.grid.update(base_addr, values)

class LogView(View):
    
    def __init__(self, parent):
        super(LogView, self).__init__(parent, -1, style=wx.BORDER_STATIC, size=(800,150))
        self.notebook = aui.AuiNotebook(self, -1, style=wx.BORDER_NONE | aui.AUI_NB_TAB_MOVE | aui.AUI_NB_TAB_SPLIT)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.notebook,1, wx.EXPAND)
        self.SetSizer(sizer)

    def get_pane(self, idx=None):
        if idx is None: idx = self.notebook.GetSelection()
        return self.notebook.GetPage(idx) if idx >= 0 else None

    def get_panes(self):
        n = self.notebook.GetPageCount()
        return [self.get_pane(i) for i in range(n)]

    def add_logger(self, logger, format=None):
        pane = LogPane(self, logger, format=format)
        self.notebook.AddPage(pane, logger.name)

class LogPane(wx.Panel):

    def __init__(self, parent, logger, format=None):
        super(LogPane, self).__init__(parent, -1, style=wx.BORDER_STATIC, size=(800,150))
        self.txt = wx.TextCtrl(self, -1, style=wx.TE_MULTILINE|wx.TE_READONLY|wx.TE_RICH2|wx.BORDER_SUNKEN)
        font = self.txt.GetFont()
        font.SetFaceName("Courier New")
        self.txt.SetFont(font)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.txt, 1, wx.EXPAND)
        self.SetSizer(sizer)
        self.logger = logger
        self.handler = log.LogHandler(format=format)
        self.logger.addHandler(self.handler)
        self.handler.register(self.listener)

    def listener(self, handler, message):
        line = handler.format(message)
        wx.CallAfter(self.txt.AppendText, "%s" % line)

    # TODO hook these up
    def on_hide(self, evt):
        self.handler.unregister(self.listener)
        event.Skip()

    def on_show(self, evt):
        self.handler.register(self.listener)
        evt.Skip()

if __name__ == "__main__":
    import test
    #test.test_view(BuildView)
    test.test_view(MemoryView, stride=2)
