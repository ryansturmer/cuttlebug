import wx
import wx.aui as aui
import wx.stc as stc
import view, util, log, styles
import logging, re


class BuildPane(stc.StyledTextCtrl):
    def __init__(self, *args, **kwargs):
        self.controller = kwargs.pop('controller')
        super(BuildPane, self).__init__(*args, **kwargs)
        self.name = "Build"
        self.manager = self.controller.style_manager
        self.SetLexer(stc.STC_LEX_CONTAINER)
        self.apply_styles(self.manager.build_styles)
        self.SetReadOnly(False)
        self.SetCaretPeriod(0)
        self.SetCaretForeground(self.GetBackgroundColour())
        self.SetWrapMode(stc.STC_WRAP_WORD)
        self.SetUseHorizontalScrollBar(False)
        self.styler = BuildStyler()
        self.Bind(wx.EVT_LEFT_DOWN, self.on_click)
        
    def apply_styles(self, styles):
        for style in styles:
            self.apply_style(style)

    def apply_style(self, style):
        s = style
        id = s.number
        self.StyleSetFontAttr(id, s.size, s.font, s.bold, s.italic, s.underline)
        self.StyleSetBackground(id, s.create_background())
        self.StyleSetForeground(id, s.create_foreground())        

    def update(self, text):
        self.SetReadOnly(False)
        self.AddStyledText(self.styler.style(text))
        self.SetReadOnly(True)
        
    def clear(self):
        self.styler.reset()
        self.SetReadOnly(False)
        self.ClearAll()
        self.SetReadOnly(True)
        
    def on_click(self, event):
        point=event.GetPosition()
        pos = self.PositionFromPoint(point)
        location = self.styler.hit_test(pos)
        if location:
            self.controller.goto(*location)
        event.Skip()
        
class BuildStyler(object):
    
    def __init__(self):
        self.re_warning = re.compile('.*\swarning\:.*')
        self.re_error = re.compile('.*\serror\:.*')
        self.re_link = re.compile('\A(.*)\:([0-9]+)')
        self.reset()
        
    def reset(self):
        self.idx = 0
        self.link_ranges = {}
        
    def __add_style_bytes(self, txt, byte):
        string = []
        style_char = chr(byte)
        for char in txt:
            string.append(char)
            string.append(style_char)
        return string
    
    def __update_style_bytes(self, txt, byte, start, end):
        for i in range(start, end):
            txt[i*2 + 1] = chr(byte)
        return txt
    
    def __search(self, regexp, text):
        i = regexp.finditer(text)
        return [(match.start(), match.end()) for match in i]
            
    def hit_test(self, pos):
        link_ranges = self.link_ranges
        for (a,b), location in link_ranges.iteritems():
            if pos >= a and pos <= b:
                return location
        return None
    
    def style(self, txt):
        # Style ranges to be applied, in order
        s = []
        # Classify the whole line as either a warning, an error, or neither
        if self.re_warning.match(txt):
            s.append((styles.STYLE_BUILD_WARNING, self.__search(self.re_warning, txt)))
        elif self.re_error.match(txt):
            s.append((styles.STYLE_BUILD_ERROR, self.__search(self.re_error, txt)))

        # Find links
        matches = self.re_link.finditer(txt)
        idx = self.idx
        link_ranges = []
        hittest_ranges = self.link_ranges
        for match in matches:
            a,b = match.start(), match.end()
            link_ranges.append((a, b))
            hittest_ranges[(a+idx, b+idx)] = (match.group(1), int(match.group(2)))
            
        s.append((styles.STYLE_BUILD_LINK, link_ranges))
        
        exp_txt = self.__add_style_bytes(txt, styles.STYLE_BUILD_DEFAULT)
        for byte, ranges in s:
            for range in ranges:
                exp_txt = self.__update_style_bytes(exp_txt, byte, *range)
        self.idx += len(txt)
        return ''.join(exp_txt)
    
    
class LogView(view.View):
    
    def __init__(self, parent, controller):
        super(LogView, self).__init__(parent, -1, style=wx.BORDER_STATIC, size=(800,150), controller=controller)
        self.notebook = aui.AuiNotebook(self, -1, style=wx.BORDER_NONE | aui.AUI_NB_TAB_MOVE | aui.AUI_NB_TAB_SPLIT)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.notebook,1, wx.EXPAND)
        self.controller = controller
        self.SetSizer(sizer)
        self.__setup()

    def __setup(self):
        self.add_logger(logging.getLogger('stdout'), icon="application_osx_terminal.png", format="%(message)s")
        self.add_logger(logging.getLogger('gdb.mi'), icon="gnu.png")
        self.add_logger(logging.getLogger('gdb.stream'), icon="gnu.png")
        self.add_logger(logging.getLogger('errors'), icon="stop.png")
        self.build_pane = BuildPane(self, controller=self.controller)
        self.add_pane(self.build_pane, icon="brick.png")
        log.redirect_stdout('stdout')

    def clear_build(self):
        self.build_pane.clear()
    
    def update_build(self, text):
        self.build_pane.update(text)
        
    def get_pane(self, idx=None):
        if idx is None: idx = self.notebook.GetSelection()
        return self.notebook.GetPage(idx) if idx >= 0 else None

    def get_panes(self):
        n = self.notebook.GetPageCount()
        return [self.get_pane(i) for i in range(n)]
        
    def show_pane(self, name):
        n = self.notebook.GetPageCount()
        for i in range(n):
            pane = self.notebook.GetPage(i)
            if pane.name == name:
                self.notebook.SetSelection(i)
                return 
        raise KeyError("No such page: %s" % name)

    def add_pane(self, pane, icon=None):
        self.notebook.AddPage(pane, pane.name)
        if icon:
            idx = self.notebook.GetPageIndex(pane)
            self.notebook.SetPageBitmap(idx, util.get_icon(icon))
            
    def add_logger(self, logger, format=None, icon=None, on_input=None):
        pane = LogPane(self, logger, format=format, on_input=on_input)
        self.add_pane(pane, icon=icon)
        
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
            self.input_txt = wx.TextCtrl(self, style=wx.TE_PROCESS_ENTER)
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

    @property
    def name(self):
        return self.logger.name
