import wx
import wx.stc as stc
import util
import os

class BusyMenuBar(wx.MenuBar):
    pass

class StatusBar(wx.StatusBar):
    ICON = 0
    TEXT = 1
    LINE = 2
    STATE = 3
    GAUGE = 4
    def __init__(self, *args, **kwargs):
        super(StatusBar, self).__init__(*args, **kwargs)
        self.SetFieldsCount(5)
        self.SetStatusWidths([18, -12,-1,-2,-4])


        # Progress Bar
        self.gauge = wx.Gauge(self)
        self.work_timer = wx.Timer(self, id=1)

        # State (text that is blinking
        self.state_timer = wx.Timer(self, id=2)
        self.state_on = True
        self._state = ""

        self.Bind(wx.EVT_TIMER, self.on_work_timer, id=1)
        self.Bind(wx.EVT_TIMER, self.on_state_timer, id=2)
        
        self.Bind(wx.EVT_SIZE, self.on_size)
        self.Bind(wx.EVT_IDLE, self.on_idle)
        self.icon = None

    def __set_line(self, line=0):
        if line:
            self._line = int(line)
            self.SetStatusText(str(line), self.LINE)
        else:
            self._line = 0
            self.SetStatusText('', self.LINE)
            
    def __get_line(self): return self._line
    line = property(__get_line, __set_line)
    
    def __set_icon(self, icon):
        if icon:
            self.__icon = util.get_icon(icon)
        else:    
            self.__icon = util.get_icon('blank.png')
        self.staticbmp = wx.StaticBitmap(self, -1, self.__icon)
        self.Reposition()

    def __get_icon(self):
        return self.icon
    icon = property(__get_icon, __set_icon)

    def set_state(self, text, blink=False):
        self._state = text
        if text and blink:
            self.state_timer.Start(500)
        else:
            self.state_timer.Stop()
        self.SetStatusText(text, self.STATE)
    def get_state(self): return self._state
    
    def __set_text(self, text):
        self.SetStatusText(str(text), self.TEXT)
    def __get_text(self):
        return str(self.GetStatusText())
    text = property(__get_text, __set_text)

    def __set_working(self, working):
        self.__working = bool(working)
        if self.__working: 
            self.gauge.Pulse()
            self.work_timer.Start(100)
        else:
            self.work_timer.Stop()
            self.gauge.SetValue(0)
    def __get_working(self):
        return self.__working
    working = property(__get_working, __set_working)

    def on_work_timer(self, evt):
        if self.__working:
            self.gauge.Pulse()
    def on_state_timer(self, evt):
        if self.state_on:
            self.state_on = False
            self.SetStatusText(self._state, self.STATE)
        else:
            self.state_on = True
            self.SetStatusText("", self.STATE)
            
    def on_idle(self, evt):
        if self.size_changed:
            self.Reposition()

    def on_size(self, evt):
        self.Reposition()
        self.size_changed = True

    def Reposition(self):
        # Gauge
        rect = self.GetFieldRect(self.GAUGE)
        self.gauge.SetPosition((rect.x+2, rect.y+2))
        self.gauge.SetSize((rect.width-4, rect.height-4))
        
        # Icon
        rect = self.GetFieldRect(self.ICON)
        self.staticbmp.SetPosition((rect.x+2, rect.y+2))
        self.size_changed = False
