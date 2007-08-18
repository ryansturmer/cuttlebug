import wx
import wx.stc as stc
import controls
import view

class BuildPortalControl(stc.StyledTextCtrl):
    pass

class BuildView(wx.Panel):

    def __init__(self, parent, controller):
        super(BuildView, self).__init__(parent, -1, style=wx.BORDER_STATIC, size=(800,150))
        self.txt = controls.BuildPortalControl(self, -1, style=wx.BORDER_NONE)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.txt, 1, wx.EXPAND)
        self.SetSizer(sizer)


    def update(self, new_text):
        self.txt.AddText(new_text)

    def clear(self):
        self.txt.SetText('')


if __name__ == "__main__":
    import test
    test.test_view(BuildView)
