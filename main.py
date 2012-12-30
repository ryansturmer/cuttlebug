import cuttlebug.settings as settings
import wx

def set_path():
    import os
    import dummy
    _file = dummy.__file__
    _file = os.path.abspath(_file)
    while file and not os.path.isdir(_file):
        _file, ext = os.path.split(_file)
    os.chdir(_file)
    
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
    import cuttlebug.util as util
    util.load_templates()
    activate_psyco()
    
    settings.load_session()
    app = wx.PySimpleApp()
    splash = show_splash()
    import cuttlebug.ui.frame as frame
    main_window = frame.Frame()
    app.SetTopWindow(main_window)
    app.frame = main_window
    main_window.Show()
    app.MainLoop()

if __name__ == "__main__":
    run()

