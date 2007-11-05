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

    def add_logger(self, logger, format=None, icon=None, on_input=None):
        pane = LogPane(self, logger, format=format, on_input=on_input)
        self.notebook.AddPage(pane, logger.name)
        if icon:
            idx = self.notebook.GetPageIndex(pane)
            self.notebook.SetPageBitmap(idx, util.get_icon(icon))

class LogPane(wx.Panel):

    def __init__(self, parent, logger, format=None, on_input=None):
        super(LogPane, self).__init__(parent, -1, style=wx.BORDER_STATIC, size=(800,150))
        self.txt = wx.TextCtrl(self, -1, style=wx.TE_MULTILINE|wx.TE_READONLY|wx.TE_RICH2|wx.BORDER_SUNKEN)
        self.__input_handler = None
        font = self.txt.GetFont()
        font.SetFaceName("Courier New")
        self.txt.SetFont(font)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.txt, 1, wx.EXPAND)
        if on_input:
            self.input_txt = wx.TextCtrl(self)
            font = self.input_txt.GetFont()
            font.SetFaceName("Courier New")
            self.input_txt.SetFont(font)
            sizer.Add(self.input_txt, 0, wx.EXPAND)
            self.__input_handler = on_input
            self.input_txt.Bind(wx.EVT_TEXT_ENTER, self.input_handler)
            
        self.SetSizer(sizer)
        self.logger = logger
        self.handler = log.LogHandler(format=format)
        self.logger.addHandler(self.handler)
        self.handler.register(self.listener)

    def input_handler(self, evt):
        if self.__input_handler:
            txt = self.input_txt.GetValue()
            try:
                self.__input_handler(txt)
            finally:
                self.input_txt.ChangeValue('')
                
    def listener(self, handler, message):
        #if not message.endswith("\n"): message += "\n"        
        line = handler.format(message)
        wx.CallAfter(self.txt.AppendText, "%s" % line)

    # TODO hook these up
    def on_hide(self, evt):
        self.handler.unregister(self.listener)
        event.Skip()

    def on_show(self, evt):
        self.handler.register(self.listener)
        evt.Skip()

