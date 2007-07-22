from __future__ import with_statement
import wx.aui as aui
import wx.stc as stc
import os
import wx
import view

class EditorView(view.View):

    def __init__(self,*args, **kwargs):
        super(EditorView,self).__init__(*args, **kwargs)
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.notebook = Notebook(self)
        sizer.Add(self.notebook, 1, wx.EXPAND)
        self.SetSizer(sizer)
        self.files = {}

    def goto(self, file, line):
        widget = self.notebook.create_file_tab(file)
        if not widget:
            return
        widget.SetFocus()
        widget.GotoLine(line)


    def save(self):
        self.notebook.save()

    def new(self):
        self.notebook.create_file_tab()

class EditorControl(stc.StyledTextCtrl):

    def __init__(self, *args, **kwargs):
        super(EditorControl, self).__init__(*args, **kwargs)

    def get_name(self):
        if self.file_path:
            root, name = os.path.split(self.file_path)
            return name
        else:
            return 'Untitled'

    def set_lexer_language(self, language=None):
        languages = {'.c':'cpp', '.C':'cpp', '.h':'cpp', '.H':'cpp'}
        if not language:
            try:
                path, filename = os.path.split(self.file_path)
                shortname, ext = os.path.splitext(filename)
                self.SetLexerLanguage(languages[ext])
            except Exception, e:
                print e

    def save(self):
        if self.file_path:
            try:
                fp = open(self.file_path, 'w')
                try:
                    fp.write(self.GetText())
                except:
                    pass
                finally:
                    fp.close()
            except:
                pass

    def open_file(self, path):
        file = None
        try:
            file = open(path, 'r')
            text = file.read()
            self.SetText(text)
            self.EmptyUndoBuffer()
            self.edited = False
            self.file_path = path
        except IOError:
            self.SetText('')
        finally:
            if file:
                file.close()

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

    def save(self):
        window = self.get_window()
        if window:
            window.save()
           

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
                    return window
            if not os.path.exists(path):
                return None
        self.Freeze()
        #if path:
        #    self.close_untitled_tab()
        
        widget = EditorControl(self, -1, style=wx.BORDER_NONE)
        
        if path:
            widget.open_file(path)
        self.AddPage(widget, widget.get_name(), True)
        widget.SetFocus()
        self.Thaw()
        return widget

