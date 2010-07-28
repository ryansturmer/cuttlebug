import wx, log

def set_path():
    import os
    import dummy
    file = dummy.__file__
    file = os.path.abspath(file)
    while file and not os.path.isdir(file):
        file, ext = os.path.split(file)
    os.chdir(file)
    
def activate_psyco():
    try:
        import psyco
        psyco.full()
    except:
        pass
    
def show_splash():
    splash = wx.SplashScreen(wx.Bitmap('./icons/splash.png'), wx.SPLASH_CENTRE_ON_SCREEN|wx.SPLASH_TIMEOUT, 1500, None, -1)
    splash.Show()
    return splash

def run():
    set_path()
    import util
    util.load_templates()
    activate_psyco()
    import settings
    settings.load_session()
    app = wx.PySimpleApp()
    splash = show_splash()
    import frame
    main_window = frame.Frame()
    app.SetTopWindow(main_window)
    app.frame = main_window
    main_window.Show()
    app.MainLoop()

if __name__ == "__main__":
    run()

