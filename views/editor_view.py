from __future__ import with_statement
import wx.aui as aui
import wx.stc as stc
import os
import wx
import view, menu, icons, util, app

class EditorView(view.View):

    def __init__(self,*args, **kwargs):
        super(EditorView,self).__init__(*args, **kwargs)
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.notebook = Notebook(self)
        sizer.Add(self.notebook, 1, wx.EXPAND)
        self.SetSizer(sizer)
        self.files = {}

    def __get_current_editor(self):
        return self.notebook.get_window()
    current_editor = property(__get_current_editor)
    
    def __get_open_files(self):
        retval = []
        for widget in self.notebook:
            retval.append(widget.file_path)
        return retval
    open_files = property(__get_open_files)
    
    def on_target_halted(self, file, line):
        goto = self.controller.settings.debug.jump_to_exec_location
        self.set_exec_location(file, line, goto=goto)
        self.update_breakpoints()
        
    def goto(self, file, line):
        widget = self.notebook.create_file_tab(file)
        if not widget:
            return
        widget.SetFocus()
        widget.GotoLine(line-1)

    def close(self, filename=None):
        if not filename:
            self.notebook.close_tab()
        else:
            self.notebook.close_file(filename)
    def cut(self):
        window = self.current_editor.Cut()

    def copy(self):
        window = self.current_editor.Copy()

    def paste(self):
        window = self.current_editor.Paste()

    def undo(self):
        window = self.current_editor.Undo()

    def redo(self):
        window = self.current_editor.Redo()
        
        
    def set_exec_location(self, file, line, goto = False):
        widget = self.notebook.create_file_tab(file)
        for window in self.notebook:
            window.remove_exec_marker()
        if not widget:
            return
        widget.set_exec_marker(line)
        if goto:
            self.goto(file, line)
            
            
    def set_breakpoint_marker(self, file, line, disabled=False):
        file = os.path.normcase(file)
        editor = self.notebook.get_file_tab(file)
        if editor:
            editor.set_breakpoint_marker(line, disabled=disabled)
    
    def set_breakpoint_markers(self, breakpoints):
        for bkpt in breakpoints:
            self.set_breakpoint_marker(bkpt.fullname, bkpt.line, not bkpt.enabled)

    def remove_breakpoint_markers(self):
        for editor in self.notebook:
            editor.remove_breakpoint_markers()
    
    def update_breakpoints(self):
        self.Freeze()
        self.remove_breakpoint_markers()
        self.set_breakpoint_markers(self.controller.gdb.breakpoints)
        self.Thaw()
        
    def update_settings(self):
        for editor in self.notebook:
            editor.apply_settings()
            editor.apply_folding_settings()

    def __get_has_unsaved_files(self):
        for window in self.notebook:
            if window.GetModify():
                return True
        return False
    has_unsaved_files = property(__get_has_unsaved_files)
    
    def save(self):
        self.notebook.save()

    def save_as(self):
        self.notebook.save_as()

    def save_all(self):
        self.notebook.save_all()
        
    def new(self):
        self.notebook.create_file_tab()

class EditorControl(stc.StyledTextCtrl):
    LINE_MARGIN = 0
    SYMBOL_MARGIN = 1
    FOLDING_MARGIN = 2

    EXECUTION_MARKER = 1
    BREAKPOINT_MARKER = 2
    DISABLED_BREAKPOINT_MARKER = 3
    
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
        self.SetMarginType(1, stc.STC_MARGIN_SYMBOL)
        self.SetMarginWidth(1, 16)
        self.click_pos = None
        #self.SetMarginMask(1, 1<<31)
        self.define_markers()
        self.create_popup_menu()
        self.SetModEventMask(stc.STC_MOD_INSERTTEXT | stc.STC_MOD_DELETETEXT | stc.STC_PERFORMED_UNDO | stc.STC_PERFORMED_REDO)
        self.Bind(wx.EVT_RIGHT_DOWN, self.on_context_menu)
        self.Bind(stc.EVT_STC_UPDATEUI, self.on_update_ui)
        self.Bind(wx.EVT_MOTION, self.on_mouse_motion)
        
    def on_mouse_motion(self, evt):
        evt.Skip()
        #point = evt.GetPosition()
        #loc = self.PositionFromPoint(point)
        
  
    def define_markers(self):
        # Execution Marker (for showing current program location)
        self.MarkerDefine(self.EXECUTION_MARKER, stc.STC_MARK_ARROW)
        self.MarkerSetBackground(self.EXECUTION_MARKER, "yellow") 
        
        # Breakpoint Marker (for showing user-selected breakpoints)
        self.MarkerDefine(self.BREAKPOINT_MARKER, stc.STC_MARK_CIRCLE)
        self.MarkerSetBackground(self.BREAKPOINT_MARKER, "red") 

        # Disabled Breakpoint Marker (for breakpoints that aren't currently active)
        self.MarkerDefine(self.DISABLED_BREAKPOINT_MARKER, stc.STC_MARK_CIRCLE)
        self.MarkerSetBackground(self.DISABLED_BREAKPOINT_MARKER, "grey") 
        
    def on_update_ui(self, evt):
        self.controller.frame.statusbar.line = self.current_line()+1
    
    def on_modified(self, evt):
        evt.Skip()
    
    def on_undo(self, evt):
        self.Undo()
    
    def on_redo(self, evt):
        self.Redo()
        
    def on_cut(self, evt):
        self.Cut()

    def on_copy(self, evt):
        self.Copy()

    def on_paste(self, evt):
        self.Paste()

    def confirm_close(self):
        return self.controller.frame.confirm(message="Save changes before closing %s?" % self.shortname )

    def __get_shortname(self):
        return os.path.basename(self.file_path)
    shortname = property(__get_shortname)

    def __get_project_rel_file_path(self):
        if self.controller and self.controller.project:
            return self.controller.project.relative_path(self.file_path)
        else:
            return self.file_path
    project_rel_file_path = property(__get_project_rel_file_path)

    def create_popup_menu(self):
        m = menu.manager.menu()
        self.mnu_undo = m.item("Undo\tCtrl+Z", func=self.on_undo, icon="edit-undo.png")
        self.mnu_redo = m.item("Redo\tCtrl+Y", func=self.on_undo, icon="edit-redo.png")
        m.separator()
        self.mnu_cut = m.item("Cut\tCtrl+X", func=self.on_cut, icon='cut.png')
        self.mnu_copy = m.item("Copy\tCtrl+C", func=self.on_copy, icon='page_copy.png')
        self.mnu_paste = m.item("Paste\tCtrl+V", func=self.on_paste, icon='paste_plain.png')
        m.separator()
        self.mnu_runtohere = m.item("Run to here...", func=self.on_run_to_here, icon="breakpoint.png", hide=[menu.TARGET_RUNNING, menu.TARGET_DETACHED], 
                                                                                  show=[menu.TARGET_HALTED,menu.TARGET_ATTACHED])
        self.mnu_runtohere.hide()
        
        self.mnu_jumptopc = m.item("Go to exec location...", func=self.on_go_to_pc, icon="pc_marker.png", hide=[menu.TARGET_RUNNING, menu.TARGET_DETACHED], 
                                                                                  show=[menu.TARGET_HALTED,menu.TARGET_ATTACHED])
        self.mnu_jumptopc.hide()
        
        self.mnu_set_bp = m.item("Set breakpoint", func=self.on_breakpoint_here, icon="stop.png", hide=[menu.TARGET_RUNNING, menu.TARGET_DETACHED], 
                                                                                show=[menu.TARGET_HALTED, menu.TARGET_ATTACHED])
        self.mnu_clear_bp = m.item("Clear breakpoint", func=self.on_clear_breakpoint, icon="stop_disabled.png", hide=[menu.TARGET_RUNNING, menu.TARGET_DETACHED], 
                                                                                show=[menu.TARGET_HALTED, menu.TARGET_ATTACHED])
        self.popup_menu = m

    def on_go_to_pc(self, evt):
        evt.Skip()

    def on_run_to_here(self, evt):
        line = self.line_from_point(self.click_pos)+1
        self.controller.run_to(self.file_path, line)

    def on_breakpoint_here(self, evt):
        line = self.line_from_point(self.click_pos)+1
        self.controller.set_breakpoint(self.file_path, line)
        
    def on_clear_breakpoint(self, evt):
        line = self.line_from_point(self.click_pos)+1        
        self.controller.clear_breakpoint_byfile(self.file_path, line)
        
    def line_from_point(self, point):
        return self.LineFromPosition(self.PositionFromPoint(point))

    def current_line(self):
        return self.LineFromPosition(self.GetCurrentPos())
    
    def breakpoint_on_line(self, line):
        markers = self.MarkerGet(line)
        if(markers & (1 << self.BREAKPOINT_MARKER)):
            return True
        return False
    
    def on_context_menu(self, evt):
        self.click_pos = evt.GetPosition()
        start, end = self.GetSelection()
        line = self.line_from_point(self.click_pos)
        if start == end:
            self.mnu_cut.hide()
            self.mnu_copy.hide()
        else:
            self.mnu_cut.show()
            self.mnu_copy.show()
            
        if self.controller.state == app.ATTACHED:
            if self.breakpoint_on_line(line):
                self.mnu_clear_bp.show()
                self.mnu_set_bp.hide()
            else:
                self.mnu_clear_bp.hide()
                self.mnu_set_bp.show()
        else:
            self.mnu_clear_bp.hide()
            self.mnu_set_bp.hide()
            
        self.PopupMenu(self.popup_menu.build(self)) 

    def get_name(self):
        if self.file_path:
            root, name = os.path.split(self.file_path)
        else:
            name = 'Untitled'
        
        return ("*" + name) if self.GetModify() else name 
    name = property(get_name)
    
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
        self.MarkerDeleteAll(self.EXECUTION_MARKER)

    def set_exec_marker(self, line):
        if line != None:
            if self.MarkerGet(line-1) & (1 << self.EXECUTION_MARKER):
                pass
            else:
                self.MarkerAdd(line-1, self.EXECUTION_MARKER)

    def remove_breakpoint_markers(self):
        self.MarkerDeleteAll(self.BREAKPOINT_MARKER)

    def set_breakpoint_marker(self, line, disabled=False):
        marker = self.DISABLED_BREAKPOINT_MARKER if disabled else self.BREAKPOINT_MARKER
        current_marker = self.MarkerGet(line-1)
        if current_marker & (1 << marker):
            return
        
        if disabled:
            if current_marker & (1 << self.BREAKPOINT_MARKER):
                self.MarkerDelete(line-1, self.BREAKPOINT_MARKER)
            self.MarkerAdd(line-1, marker)
        else:
            if current_marker & (1 << self.DISABLED_BREAKPOINT_MARKER): 
                self.MarkerDelete(line-1, self.DISABLED_BREAKPOINT_MARKER)
            self.MarkerAdd(line-1, marker)

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
    
    def style_line(self, line, style):
        start = self.PositionFromLine(line)
        end = self.GetLineEndPosition(line)
        print start
        print end
        self.StartStyling(start, 0x1f)
        self.SetStyling(wx.stc.STC_STYLE_BRACEBAD, end-start)

    def save(self):
        if self.file_path:
            try:
                fp = open(self.file_path, 'w')
                try:
                    fp.write(self.GetText())
                    self.SetSavePoint()
                except:
                    pass
                finally:
                    fp.close()
            except:
                pass

    def open_file(self, path):
        path = os.path.normpath(path)
        file = None
        try:
            file = open(path, 'r')
            text = file.read()
            self.SetText(text)
            self.EmptyUndoBuffer()
            self.SetSavePoint()
            self.file_path = path
        except IOError:
            self.SetText('')
        finally:
            if file:
                file.close()
        self.detect_language()
        self.style_line(5, 38)

    def apply_folding_settings(self):
        if self.controller and self.controller.settings.editor.fold:
            self.SetProperty("fold", "1")
            self.SetMarginType(self.FOLDING_MARGIN, stc.STC_MARGIN_SYMBOL)
            self.SetMarginMask(self.FOLDING_MARGIN, stc.STC_MASK_FOLDERS)
            self.SetMarginSensitive(self.FOLDING_MARGIN, True)
            self.SetMarginWidth(self.FOLDING_MARGIN, self.controller.settings.editor.fold_margin_size)
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
        style |= aui.AUI_NB_CLOSE_BUTTON
        
        super(Notebook, self).__init__(parent, -1, style=style)
        self.Bind(aui.EVT_AUINOTEBOOK_PAGE_CLOSE, self.on_page_close)
        self.Bind(aui.EVT_AUINOTEBOOK_PAGE_CHANGED, self.on_page_changed)
        self.controller = parent.controller
        
    def on_page_close(self, event):
        event.Veto()
        index = event.GetSelection()
        self.close_tab(index)
        
    def __iter__(self):
        return iter(self.get_windows())
    
    def on_page_changed(self, evt):
        window = self.get_window()
        if window:
            self.controller.frame.statusbar.line = window.current_line()+1

#    def update_names(self):
#        self.Freeze()
#        for window in self:
#            idx = self.GetPageIndex()
#            print self.window.name
#            self.SetPageText(idx, window.name)
#        self.Thaw()

    def on_modified(self, evt):
        widget = evt.GetEventObject()
        if widget:
            idx = self.GetPageIndex(widget)
            self.SetPageText(idx, widget.name)
            
    def get_window(self, index=None):
        if index is None: index = self.GetSelection()
        return self.GetPage(index) if index >= 0 else None

    def get_windows(self):
        n = self.GetPageCount()
        return [self.get_window(i) for i in range(n)]

    def save(self):
        window = self.get_window()
        if window:
            if not window.file_path:
                self.save_as()
            window.save()
            idx = self.GetPageIndex(window)
            self.SetPageText(idx, window.name)
            
    def save_as(self):
        window = self.get_window()
        if window:
            frame = self.controller.frame
            project = self.controller.project
            dir = project.directory if project else ""
            file = frame.browse_for_file(message="Save...", dir=dir, style=wx.FD_SAVE)
            window.file_path = file
            window.save()
            idx = self.GetPageIndex(window)
            self.SetPageText(idx, window.name)
                    
    def save_all(self):
        for window in self:
            if window.GetModify():
                window.save()
                
    def close_file(self, filename):
        widget = self.get_file_tab(filename)
        idx = self.GetPageIndex(widget)
        self.close_tab(index=idx)
        
    def close_tab(self, index=None):
        self.Freeze()
        if index is None: index = self.GetSelection()
        if index >= 0:
            window = self.get_window(index)
            save = window.confirm_close() if window.GetModify() else False
            if save == True:
                #self.recent_path(window.file_path)
                window.save()
                self.DeletePage(index)
                #wx.PostEvent(self, NotebookEvent(EVT_NOTEBOOK_TAB_CLOSED, self))
            elif save == False:
                self.DeletePage(index)
                #wx.PostEvent(self, NotebookEvent(EVT_NOTEBOOK_TAB_CLOSED, self))
            else:
                pass # save == None, user cancelled
        self.Thaw()
        
        
    def get_file_tab(self, path):
        path = os.path.abspath(path)
        for window in self:
            if not window.file_path: continue
            p1 = os.path.normcase(path)
            p2 = os.path.normcase(window.file_path)
            if p1 == p2:
                return window
        return None

    def create_file_tab(self, path=None):
        if path:
            path = self.controller.project.absolute_path(path)
            window = self.get_file_tab(path)

            if window:
                window.SetFocus()
                self.controller.frame.statusbar.line = window.current_line()+1
                return window

            if not os.path.exists(path):
                return None
        
        self.Freeze()
        #if path:
        #    self.close_untitled_tab()
        
        widget = EditorControl(self, -1, style=wx.BORDER_NONE, controller=self.controller)
        
        if path:
            widget.open_file(path)
        self.AddPage(widget, widget.get_name(), True)
        idx = self.GetPageIndex(widget)
        if idx >= 0:
            self.SetPageBitmap(idx, util.get_icon(icons.get_file_icon(path)))
        widget.SetFocus()
        self.controller.frame.statusbar.line = widget.current_line()+1
        widget.Bind(stc.EVT_STC_MODIFIED, self.on_modified)
        self.Thaw()
        return widget

