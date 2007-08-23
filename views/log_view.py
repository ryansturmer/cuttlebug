import wx
import wx.aui as aui
import view, util, log


class LogView(view.View):
    
    def __init__(self, parent, controller):
        super(LogView, self).__init__(parent, -1, style=wx.BORDER_STATIC, size=(800,150), controller=controller)
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

    def add_logger(self, logger, format=None, icon=None):
        pane = LogPane(self, logger, format=format)
        self.notebook.AddPage(pane, logger.name)
        if icon:
            idx = self.notebook.GetPageIndex(pane)
            self.notebook.SetPageBitmap(idx, util.get_icon(icon))

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
        if not line.endswith("\n"): line += "\n"
        wx.CallAfter(self.txt.AppendText, "%s" % line)

    # TODO hook these up
    def on_hide(self, evt):
        self.handler.unregister(self.listener)
        event.Skip()

    def on_show(self, evt):
        self.handler.register(self.listener)
        evt.Skip()

