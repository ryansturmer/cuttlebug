import wx, log
import frame

class Splash(wx.Frame):
    def __init__(self, parent, image_file):
        wx.Frame.__init__(self, parent, -1, "Splash",
                         style =
                           wx.FRAME_SHAPED
                         | wx.SIMPLE_BORDER
                         | wx.FRAME_NO_TASKBAR
                         | wx.STAY_ON_TOP
                         )

        self.hasShape = False
        self.delta = (0,0)


        self.bmp = wx.Bitmap(image_file)
        w, h = self.bmp.GetWidth(), self.bmp.GetHeight()
        self.SetClientSize( (w, h) )

        if wx.Platform == "__WXGTK__":
            # wxGTK requires that the window be created before you can
            # set its shape, so delay the call to SetWindowShape until
            # this event.
            self.Bind(wx.EVT_WINDOW_CREATE, self.SetWindowShape)
        else:
            # On wxMSW and wxMac the window has already been created, so go for it.
            self.SetWindowShape()

        dc = wx.ClientDC(self)
        dc.DrawBitmap(self.bmp, 0,0, True)

    def SetWindowShape(self, *evt):
        # Use the bitmap's mask to determine the region
        r = wx.RegionFromBitmap(self.bmp)
        self.hasShape = self.SetShape(r)

def run():
    app = wx.PySimpleApp()
    import frame
    main_window = frame.Frame()
    app.SetTopWindow(main_window)
    main_window.Show()
    app.MainLoop()

if __name__ == "__main__":
    run()

