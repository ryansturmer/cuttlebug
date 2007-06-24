import wx, log
import frame

def run():
    app = wx.PySimpleApp()
    import frame
    main_window = frame.Frame()
    app.SetTopWindow(main_window)
    main_window.Show()
    app.MainLoop()

if __name__ == "__main__":
    run()

