import wx
import wx.stc as stc
import util
import os

class EditorControl(stc.StyledTextCtrl):

    def get_name(self):
        if self.file_path:
            root, name = os.path.split(self.file_path)
            return name
        else:
            return 'Untitled'

    def open_file(self, path):
        file = None
        try:
            file = open(path, 'r')
            text = file.read()
            self.SetText(text)
            self.EmptyUndoBuffer()
            self.edited = False
            self.file_path = path
        except IOError:
            self.SetText('')
        finally:
            if file:
                file.close()

class StatusBar(wx.StatusBar):

    def __init__(self, *args, **kwargs):
        super(StatusBar, self).__init__(*args, **kwargs)
        self.SetFieldsCount(3)
        self.SetStatusWidths([18, -4,-1])
        self.text = ""
        self.gauge = wx.Gauge(self)
        self.timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.on_timer)
        self.Bind(wx.EVT_SIZE, self.on_size)
        self.Bind(wx.EVT_IDLE, self.on_idle)
        self.icon = None

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

    def __set_text(self, text):
        self.SetStatusText(str(text), 1)
    def __get_text(self):
        return str(self.GetStatusText())
    text = property(__get_text, __set_text)

    def __set_working(self, working):
        self.__working = bool(working)
        if self.__working: 
            self.gauge.Pulse()
            self.timer.Start(100)
        else:
            self.timer.Stop()
            self.gauge.SetValue(0)
    def __get_working(self):
        return self.__working
    working = property(__get_working, __set_working)

    def on_timer(self, evt):
        if self.__working:
            self.gauge.Pulse()
   
    def on_idle(self, evt):
        if self.size_changed:
            self.Reposition()

    def on_size(self, evt):
        self.Reposition()
        self.size_changed = True

    def Reposition(self):
        # Gauge
        rect = self.GetFieldRect(2)
        self.gauge.SetPosition((rect.x+2, rect.y+2))
        self.gauge.SetSize((rect.width-4, rect.height-4))
        
        # Icon
        rect = self.GetFieldRect(0)
        self.staticbmp.SetPosition((rect.x+2, rect.y+2))
        self.size_changed = False
