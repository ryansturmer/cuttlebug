import wx, log
import frame
def show_splash():
    splash = wx.SplashScreen(wx.Bitmap('./icons/splash.png'), wx.SPLASH_CENTRE_ON_SCREEN|wx.SPLASH_TIMEOUT, 1500, None, -1)
    splash.Show()
    return splash

def run():
    app = wx.PySimpleApp()
    splash = show_splash()
    import frame
    main_window = frame.Frame()
    app.SetTopWindow(main_window)
    main_window.Show()
    app.MainLoop()

if __name__ == "__main__":
    run()

