import wx
import wx.stc as stc
import controls, styles
import view
import re


    
class BuildView(wx.Panel):

    def __init__(self, parent, controller):
        super(BuildView, self).__init__(parent, -1, style=wx.BORDER_STATIC, size=(800,150))
        self.controller = controller
        self.txt = BuildPortalControl(self, -1, controller=self.controller)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.txt, 1, wx.EXPAND)
        self.SetSizer(sizer)
        
    def update(self, new_text):
        self.txt.update(new_text)
    
    def clear(self):
        self.txt.clear()


if __name__ == "__main__":
    import test
    test.test_view(BuildView)
