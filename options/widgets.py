import wx
from options import OptionsEvent, EVT_OPTION_CHANGED
import wx.lib.colourselect as csel

class OptionsWidget(object):
    def __init__(self):
        pass

    def get_value(self):
        raise NotImplementedError

    def set_value(self, value):
        raise NotImplementedError

    def on_change(self, evt):
        evt = OptionsEvent(EVT_OPTION_CHANGED, self)
        wx.PostEvent(self, evt)

    def validate(self):
        return True

class TextWidget(OptionsWidget, wx.TextCtrl):

    def __init__(self, parent, id=-1):
        OptionsWidget.__init__(self)
        wx.TextCtrl.__init__(self, parent=parent, id=id)
        self.Bind(wx.EVT_TEXT, self.on_change)

    def get_value(self):
        return self.GetValue()

    def set_value(self, value):
        self.SetValue(str(value))

class CheckboxWidget(OptionsWidget, wx.CheckBox):

    def __init__(self, parent, id=-1):
        OptionsWidget.__init__(self)
        wx.CheckBox.__init__(self, parent=parent, id=id)
        self.Bind(wx.EVT_CHECKBOX, self.on_change)

    def get_value(self):
        return bool(self.GetValue())

    def set_value(self, value):
        self.SetValue(bool(value))

class SpinWidget(OptionsWidget, wx.SpinCtrl):

    def __init__(self, parent, id=-1, range=(1,100)):
        OptionsWidget.__init__(self)
        wx.SpinCtrl.__init__(self, parent, -1, "")
        self.SetRange(1,100)
        self.SetValue(1)
        self.Bind(wx.EVT_SPIN, self.on_change)

    def get_value(self):
        return self.GetValue()

    def set_value(self, value):
        self.SetValue(int(value))

class ColorWidget(OptionsWidget, csel.ColourSelect):

    def __init__(self, parent, id=-1):
        OptionsWidget.__init__(self)
        csel.ColourSelect.__init__(self, parent, -1, "", (0,0,0))
        self.Bind(csel.EVT_COLOURSELECT, self.on_change)

    def get_value(self):
        return self.GetColour()

    def set_value(self, value):
        self.SetColour(value)
