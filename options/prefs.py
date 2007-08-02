import wx
import util

if __name__ == "__main__":
    app = wx.App()
    frame = wx.Frame(None)
    opt = OptionsDialog(frame)
    page = OptionsDialog(opt)
    page.add("Test Widgets", "Test1", TextWidget)
    page.add("Test Widgets", "Test2", TextWidget, label_on_right=True)
    page.add("More Test Widgets", "Test3", TextWidget)
    page.add("More Test Widgets", "Test3", TextWidget)
    opt.add_panel(page)
    opt.ShowModal()
