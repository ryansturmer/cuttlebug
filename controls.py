import wx
import wx.stc as stc
import util
import os
import wx.lib.mixins.listctrl as listmix
from odict import OrderedDict

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
        self.SetStatusWidths([18, -24,-2,-8,-8])


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

    def set_state(self, text, blink=False, color=wx.BLACK):
        #TODO Put COLOR support in here
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
        else:
            self.gauge.SetValue(0)
            
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

class DictListCtrl(wx.ListCtrl, listmix.ListCtrlAutoWidthMixin, listmix.TextEditMixin):
    
    def __init__(self, parent):
        wx.ListCtrl.__init__(self, parent, -1, style=wx.LC_REPORT | wx.LC_VIRTUAL | wx.LC_HRULES)
        listmix.ListCtrlAutoWidthMixin.__init__(self)
        listmix.TextEditMixin.__init__(self)

        self.InsertColumn(0, "Name")
        self.InsertColumn(1, "Value")
        self.SetColumnWidth(0, wx.LIST_AUTOSIZE_USEHEADER)
        self.SetColumnWidth(2, wx.LIST_AUTOSIZE_USEHEADER)

        self.SetItemCount(0)
        self.__items = OrderedDict()
        self.__changed = {}

        # Attributes (for changing list item colors)
        self.redattr = wx.ListItemAttr()
        self.redattr.SetTextColour("red")
        self.blackattr = wx.ListItemAttr()
        self.blackattr.SetTextColour("black")

    def OnGetItemText(self, item, col):
        if col == 0:
            return self.__items.keys()[item]
        else:
            return self.__items.values()[item]

    def OnGetItemAttr(self, item):
        key = self.__items.keys()[item]
        if key in self.__changed and self.__changed[key]:
            return self.redattr
        else:
            return self.blackattr

    def __contains__(self, key):
        return key in self.__items

    def __setitem__(self, key, value):
        changed = False
        try:
            old_value = self.__items[key]
            if value != old_value:
                changed = True
        except:
            changed = True
        if changed:
            self.__changed[key] = True
        else:
            self.__changed[key] = False

        self.__items[key] = value
        self.SetItemCount(len(self.__items))
        self.Refresh()
        
    def __getitem__(self, key):
        return self.__items[key]

    def __iter__(self):
        return iter(self.__items.keys()[:])

    def remove_item(self, key):
        try:
            self.__items.pop(key)
            self.__changed.pop(key)
        except:
            pass
        self.SetItemCount(len(self.__items))
        self.Refresh()
        
    def update(self, items):
        for key in items:
            self[key] = items[key]
        for key in self:
            if key not in items:
                self.remove_item(key)
        self.Refresh()
