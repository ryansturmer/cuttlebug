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

    def set_exec_location(self, file, line):
        for window in self.notebook:
            window.remove_exec_marker()

        self.goto(file, line)
        widget = self.notebook.create_file_tab(file)
        if not widget:
            return
        widget.set_exec_marker(line)

    def update_settings(self):
        for editor in self.notebook:
            editor.apply_settings()
            editor.apply_folding_settings()
    def save(self):
        self.notebook.save()

    def new(self):
        self.notebook.create_file_tab()

class EditorControl(stc.StyledTextCtrl):
    LINE_MARGIN = 0
    SYMBOL_MARGIN = 1
    FOLDING_MARGIN = 2

    EXECUTION_MARKER = 1
    def __init__(self, *args, **kwargs):
        if 'controller' in kwargs:
            self.controller = kwargs.pop('controller')
        else:
            self.controller = None
        super(EditorControl, self).__init__(*args, **kwargs)
        self._line_count = -1
        self.file_path = ''
        self.apply_folding_settings()
        self.apply_settings()
        self.MarkerDefine(self.EXECUTION_MARKER, stc.STC_MARK_ARROW)
        self.MarkerSetBackground(self.EXECUTION_MARKER, "yellow") 
        self.SetMarginType(1, stc.STC_MARGIN_SYMBOL)
        self.SetMarginWidth(1, 16)
        #self.SetMarginMask(1, 1<<31)

    def get_name(self):
        if self.file_path:
            root, name = os.path.split(self.file_path)
            return name
        else:
            return 'Untitled'

    def apply_settings(self):
        settings = self.controller.settings.editor
        self.IndicatorSetStyle(1, stc.STC_INDIC_ROUNDBOX)
        self.IndicatorSetForeground(1, wx.RED)
        self.IndicatorSetStyle(2, stc.STC_INDIC_ROUNDBOX)
        self.IndicatorSetForeground(2, wx.BLUE)
        
        self.SetCaretForeground(settings.cursor.foreground_color)
        self.SetCaretLineVisible(settings.line_visible)
        self.SetCaretLineBack(settings.cursor.background_color)
        self.SetCaretPeriod(settings.cursor.period)
        self.SetCaretWidth(settings.cursor.width)
        
        self.SetWrapMode(stc.STC_WRAP_WORD if settings.page.wrap else stc.STC_WRAP_NONE)
        #self.SetSelBackground(bool(settings.cursor.selection_foreground_color), settings.cursor.selection_background_color)
        #self.SetSelForeground(bool(settings.cursor.selection_foreground_color), settings.cursor.selection_foreground_color)
        self.SetUseHorizontalScrollBar(settings.page.horizontal_scrollbar)
        self.SetBackSpaceUnIndents(settings.indent.backspace_unindents)
        self.SetEdgeColumn(settings.page.edge_column)
        self.SetEdgeMode(settings.page.edge_mode)
        self.SetEndAtLastLine(settings.page.end_at_last_line)
        self.SetIndentationGuides(settings.indent.indentation_guides)
        self.SetTabIndents(settings.indent.tab_indents)
        self.SetTabWidth(settings.indent.tab_width)
        self.SetUseTabs(settings.indent.use_tabs)
        self.SetViewWhiteSpace(settings.view_whitespace)
        self.SetMargins(settings.page.margin_left, settings.page.margin_right)
        
        #self.apply_bookmark_settings()
        self.apply_folding_settings()
        self.show_line_numbers()
        self.detect_language()

    def show_line_numbers(self):
        self.SetMarginType(self.LINE_MARGIN, stc.STC_MARGIN_NUMBER)
        self.SetMarginWidth(self.LINE_MARGIN, 0)
        self.update_line_numbers()

    def remove_exec_marker(self):
        self.MarkerDeleteAll(1 << self.EXECUTION_MARKER)

    def set_exec_marker(self, line):
        if line != None:
            if self.MarkerGet(line) & (1 << self.EXECUTION_MARKER):
                pass
            else:
                self.MarkerAdd(line, self.EXECUTION_MARKER)

    def update_line_numbers(self):
        if self.controller and self.controller.settings.editor.page.show_line_numbers:
            lines = self.GetLineCount()
            if lines != self._line_count:
                self._line_count = lines
                text = '%d ' % lines
                n = len(text)
                if n < 4: text += ' ' * (4-n)
                width = self.TextWidth(stc.STC_STYLE_LINENUMBER, text)
                self.SetMarginWidth(self.LINE_MARGIN, width)
    def detect_language(self):
        if self.controller:
            path = self.file_path
            manager = self.controller.style_manager
            if path:
                pre, ext = os.path.splitext(path)
                language = manager.get_language(ext)
            else:
                language = None
            self.apply_language(manager, language)

    def set_lexer_language(self, language=None):
        languages = {'.c':'cpp', '.C':'cpp', '.h':'cpp', '.H':'cpp'}
        if not language:
            try:
                path, filename = os.path.split(self.file_path)
                shortname, ext = os.path.splitext(filename)
                self.SetLexerLanguage(languages[ext])
            except Exception, e:
                print e

    def apply_language(self, manager, language):
        self.language = language
        self.ClearDocumentStyle()
        self.SetKeyWords(0, '')
        self.SetLexer(stc.STC_LEX_NULL)
        self.StyleResetDefault()
        self.apply_style(manager.base_style)
        self.StyleClearAll()
        self.apply_styles(manager.app_styles)
        if language:
            self.SetLexer(language.lexer)
            self.SetKeyWords(0, ' '.join(language.keywords.split()))
            for n in range(2, 8):
                attr = 'keywords%d' % n
                if not hasattr(language, attr):
                    continue
                keywords = getattr(language, attr)
                self.SetKeyWords(n-1, ' '.join(keywords.split()))
            self.apply_styles(language.styles)
        self.Colourise(0, self.GetLength())

    def apply_styles(self, styles):
        for style in styles:
            self.apply_style(style)

    def apply_style(self, style):
        s = style
        id = s.number
        self.StyleSetFontAttr(id, s.size, s.font, s.bold, s.italic, s.underline)
        self.StyleSetBackground(id, s.create_background())
        self.StyleSetForeground(id, s.create_foreground())
    
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
        self.detect_language()

    def apply_folding_settings(self):
        if self.controller and self.controller.settings.editor.fold:
            self.SetProperty("fold", "1")
            self.SetMarginType(self.FOLDING_MARGIN, stc.STC_MARGIN_SYMBOL)
            self.SetMarginMask(self.FOLDING_MARGIN, stc.STC_MASK_FOLDERS)
            self.SetMarginSensitive(self.FOLDING_MARGIN, True)
            self.SetMarginWidth(self.FOLDING_MARGIN, self.controller.settings.editor.folding_margin_size)
            self.MarkerDefine(stc.STC_MARKNUM_FOLDEREND, stc.STC_MARK_BOXPLUSCONNECTED, "white", "#666666")
            self.MarkerDefine(stc.STC_MARKNUM_FOLDEROPENMID, stc.STC_MARK_BOXMINUSCONNECTED, "white", "#666666")
            self.MarkerDefine(stc.STC_MARKNUM_FOLDERMIDTAIL, stc.STC_MARK_TCORNER, "white", "#666666")
            self.MarkerDefine(stc.STC_MARKNUM_FOLDERTAIL, stc.STC_MARK_LCORNER, "white", "#666666")
            self.MarkerDefine(stc.STC_MARKNUM_FOLDERSUB, stc.STC_MARK_VLINE, "white", "#666666")
            self.MarkerDefine(stc.STC_MARKNUM_FOLDER, stc.STC_MARK_BOXPLUS, "white", "#666666")
            self.MarkerDefine(stc.STC_MARKNUM_FOLDEROPEN, stc.STC_MARK_BOXMINUS, "white", "#666666")
        else:
            self.SetProperty("fold", "0")
            self.SetMarginSensitive(self.FOLDING_MARGIN, False)
            self.SetMarginWidth(self.FOLDING_MARGIN, 0)

class Notebook(aui.AuiNotebook):

    def __init__(self, parent):
        style = wx.BORDER_NONE
        style |= aui.AUI_NB_TAB_MOVE
        style |= aui.AUI_NB_TAB_SPLIT
        super(Notebook, self).__init__(parent, -1, style=style)

    def __iter__(self):
        return iter(self.get_windows())
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
        
        widget = EditorControl(self, -1, style=wx.BORDER_NONE, controller=wx.GetApp().GetTopWindow().controller)
        
        if path:
            widget.open_file(path)
        self.AddPage(widget, widget.get_name(), True)
        widget.SetFocus()
        self.Thaw()
        return widget

