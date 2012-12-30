import wx.aui as aui
import wx.stc as stc
import os
import wx
import controls


class Notebook(aui.AuiNotebook):

    def __init__(self, parent):
        style = wx.BORDER_NONE
        style |= aui.AUI_NB_TAB_MOVE
        style |= aui.AUI_NB_TAB_SPLIT

        super(Notebook, self).__init__(parent, -1, style=style)

    def get_window(self, index=None):
        if index is None: index = self.GetSelection()
        return self.GetPage(index) if index >= 0 else None

    def get_windows(self):
        n = self.GetPageCount()
        return [self.get_window(i) for i in range(n)]

    def open(self, path):
        if not os.path.exists(path):
            return None
        else:
            return self.create_file_tab(path)
            
    def create_file_tab(self, path=None):
        if path:
            path = os.path.abspath(path)
            for window in self.get_windows():
                if not window.file_path:
                    continue
                p1 = os.path.normcase(path)
                p2 = os.path.normcase(window.file_path)
                if p1 == p2:
                    window.SetFocus()
                    return
            if not os.path.exists(path):
                return
        #self.Freeze()
        
        widget = controls.EditorControl(self, -1, style=wx.BORDER_NONE)
        
        if path:
            widget.open_file(path)
        self.AddPage(widget, widget.get_name(), True)
        widget.SetFocus()
        #self.Thaw()
        
        return widget
