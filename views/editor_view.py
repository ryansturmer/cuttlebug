from __future__ import with_statement
import wx.aui as aui
import wx.stc as stc
import os
import wx
import view, menu, icons, util, app, gdb 

#TODO fix code folding
#TODO fix updating the colorization settings so you don't have to close and reopen existing tabs
FOUND_COLOR = wx.WHITE
NOTFOUND_COLOR = wx.Colour(255,102,102)

class QuickFindBar(wx.Panel):
    
    def __init__(self, parent, editor):
        super(QuickFindBar, self).__init__(parent, -1)
        self.editor = editor
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        btn = util.plate_button(self, func=self.on_close, icon='ex.png')
        lbl = wx.StaticText(self, -1, "Find:")
        match_case = util.checkbox(self, label="Match Case")
        whole_word = util.checkbox(self, label="Whole Word")
        prev = util.plate_button(self, icon='go-up.png', label="Previous", id=wx.ID_UP, func=self.on_prev)
        next = util.plate_button(self, icon='go-down.png', label="Next", id=wx.ID_DOWN, func=self.on_next)
        txt = wx.TextCtrl(self, -1, style=wx.TE_PROCESS_ENTER)
        
        sizer.Add(util.padded(btn, 3),0,wx.CENTER)
        sizer.Add(lbl,0, wx.CENTER)
        sizer.AddSpacer(4)
        sizer.Add(txt,0, wx.CENTER)
        sizer.AddSpacer(4)
        sizer.Add(prev, 0, wx.CENTER)
        sizer.AddSpacer(4)
        sizer.Add(next, 0, wx.CENTER)
        sizer.AddSpacer(4)
        sizer.Add(match_case, 0, wx.CENTER)
        sizer.AddSpacer(4)
        sizer.Add(whole_word, 0, wx.CENTER)

        self.SetSizer(sizer)
        txt.Bind(wx.EVT_TEXT_ENTER, self.on_enter)
        txt.Bind(wx.EVT_TEXT, self.on_text)
        txt.Bind(wx.EVT_KEY_DOWN, self.on_key)
        self.Bind(wx.EVT_KEY_DOWN, self.on_key)
        self.textctrl = txt
        self.match_case = match_case
        self.whole_word = whole_word

    def show_and_focus(self):
      #  self.GetParent().Freeze()
        self.Show()
        self.GetParent().Layout()
        self.textctrl.SetFocus()
     #   self.GetParent().Thaw()

    def on_next(self, evt):
        self.find_next(self.textctrl.GetValue())

    def on_prev(self, evt):
        print "Previous?"
        
    def find_next(self, text):
        flags = 0
        if self.match_case.GetValue(): flags |= stc.STC_FIND_MATCHCASE
        if self.whole_word.GetValue(): flags |= stc.STC_FIND_WHOLEWORD        
        if not text:
            self.set_color(FOUND_COLOR)
            return
        next_anchor = self.editor.GetSelectionEnd()
        for loc in (next_anchor, 0):
            self.editor.SetAnchor(loc)
            self.editor.SetCurrentPos(loc)
            self.editor.SearchAnchor()
            idx = self.editor.SearchNext(flags, text)
            if idx == -1:
                continue
            else:
                self.editor.SetSelection(*self.editor.GetSelection())
                #self.editor.GotoPos(idx)
                self.set_color(FOUND_COLOR)
                return
        self.set_color(NOTFOUND_COLOR)
        
    def set_color(self, color):
        style = self.textctrl.GetDefaultStyle()
        style.SetBackgroundColour(color)
        self.textctrl.SetStyle(0, len(self.textctrl.GetValue()), style)
        self.textctrl.SetBackgroundColour(color)
        
    def on_enter(self, evt):
        self.find_next(self.textctrl.GetValue())
        evt.Skip()
        
    def on_key(self, evt):
        if evt.GetKeyCode() == wx.WXK_ESCAPE and evt.GetModifiers() == 0:
            self.hide()
        evt.Skip()
            
    def on_text(self, evt):
        self.find_next(self.textctrl.GetValue())
        
    def hide(self):
        parent = self.GetParent()
        parent.Freeze()
        self.Hide()
        parent.Layout()
        parent.Thaw()

    def show(self):
        parent = self.GetParent()
        parent.Freeze()
        self.Show()
        parent.Layout()
        parent.Thaw()
    
    def on_close(self,event):
        self.hide()
        
class EditorView(view.View):

    def __init__(self,*args, **kwargs):
        super(EditorView,self).__init__(*args, **kwargs)
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.notebook = Notebook(self)
        sizer.Add(self.notebook, 1, wx.EXPAND)
        self.SetSizer(sizer)
        self.files = {}
        self.controller.Bind(app.EVT_APP_TARGET_HALTED, self.on_target_halted)
        self.controller.Bind(app.EVT_APP_TARGET_RUNNING, self.on_target_running)
              
    def set_model(self, model):
        self.model = model
        self.model.Bind(gdb.EVT_GDB_UPDATE_BREAKPOINTS, self.on_breakpoint_update)
        self.model.Bind(gdb.EVT_GDB_FINISHED, self.on_gdb_finished)
        
    def on_gdb_finished(self, evt):
        self.remove_markers()
        evt.Skip()
        
    @property
    def current_editor(self):
        return self.notebook.get_window()
    
    @property
    def open_files(self):
        retval = []
        for widget in self.notebook:
            retval.append(widget.file_path)
        return retval
    
    def on_target_halted(self, evt):
        file, line = evt.data[0], evt.data[1]
        if file:
            goto = self.controller.settings.debug.jump_to_exec_location
            self.set_exec_location(file, line, goto=goto)
        evt.Skip()
        
    def on_target_running(self):
        self.remove_exec_marker()
        evt.Skip()
        
    def find(self):
        self.notebook.find()
        
    def goto(self, file, line):
#        print "Going to %s, %s" % (file, line)
        widget = self.notebook.create_file_tab(file)
        if not widget:
            print "Couldn't goto line %d in file '%s' because I couldn't create a new tab for that file." % (line, file)
            return
        widget.SetFocus()
        widget.GotoLine(line-1)
        return widget
    
    def show_error(self, file, line):
        widget = self.goto(file, line)
        if widget:
            widget.set_error_marker(line)
            
    def close(self, filename=None):
        if not filename:
            self.notebook.close_tab()
        else:
            self.notebook.close_file(filename)
            
    def cut(self):
        self.current_editor.Cut()

    def copy(self):
        self.current_editor.Copy()

    def paste(self):
        self.current_editor.Paste()

    def undo(self):
        self.current_editor.Undo()

    def redo(self):
        self.current_editor.Redo()
        
    def remove_markers(self):
        self.remove_breakpoint_markers()
        self.remove_exec_marker()
        
    def set_exec_location(self, file, line, goto = False):
        #print "Setting exec loc %s, %s"  % (file, line)
        widget = self.notebook.open(file)
        for window in self.notebook:
            window.remove_exec_marker()
        if not widget:
            print "Couldn't set exec location to line %d in file '%s' because I couldn't create a new tab for that file." % (line, file)
            return
        widget.set_exec_marker(line)
        if goto:
            self.goto(file, line)
    
    def remove_exec_marker(self):
        for widget in self.notebook:
            widget.remove_exec_marker()
        
            
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
            
    def on_breakpoint_update(self, evt):
        self.remove_breakpoint_markers()
        self.set_breakpoint_markers(self.model.breakpoints)
        evt.Skip()
        
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
        return self.notebook.create_file_tab()

    def open(self, path):
        self.notebook.open(path)


class EditorControl(stc.StyledTextCtrl):
    LINE_MARGIN = 0
    SYMBOL_MARGIN = 1
    FOLDING_MARGIN = 2

    ERROR_BKGND_MARKER = 8
    EXECUTION_BKGND_MARKER = 4
    EXECUTION_MARKER = 3
    BREAKPOINT_MARKER = 2
    DISABLED_BREAKPOINT_MARKER = 1
    
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
        self.create_popup_menu()
        self.SetEOLMode(stc.STC_EOL_LF)
        self.SetModEventMask(stc.STC_MOD_INSERTTEXT | stc.STC_MOD_DELETETEXT | stc.STC_PERFORMED_UNDO | stc.STC_PERFORMED_REDO | stc.STC_PERFORMED_USER)
        self.Bind(wx.EVT_RIGHT_DOWN, self.on_context_menu)
        self.Bind(stc.EVT_STC_UPDATEUI, self.on_update_ui)
        self.Bind(wx.EVT_MOTION, self.on_mouse_motion)
        self.Bind(wx.EVT_KEY_DOWN, self.on_key)
        self.error_redness = 0
        
    def on_key(self, evt):
        if evt.GetKeyCode() == wx.WXK_ESCAPE and evt.GetModifiers() == 0:
            self.GetParent().find_bar.hide()
        #print self.GetCurrentPos()
        
        evt.Skip()
        
    def on_mouse_motion(self, evt):
        evt.Skip()
        #point = evt.GetPosition()
        #loc = self.PositionFromPoint(point)
        
  
    def define_markers(self):
        # Execution Marker (for showing current program location)
        self.MarkerDefine(self.EXECUTION_MARKER, stc.STC_MARK_ARROW)
        self.MarkerSetBackground(self.EXECUTION_MARKER, wx.Colour(*self.controller.settings.editor.exec_marker_color))         
        self.MarkerDefine(self.EXECUTION_BKGND_MARKER, stc.STC_MARK_BACKGROUND)
        self.MarkerSetBackground(self.EXECUTION_BKGND_MARKER, wx.Colour(*self.controller.settings.editor.exec_marker_color))
        
        # Breakpoint Marker (for showing user-selected breakpoints)
        self.MarkerDefine(self.BREAKPOINT_MARKER, stc.STC_MARK_CIRCLE)
        self.MarkerSetBackground(self.BREAKPOINT_MARKER, "red") 
        #self.MarkerSetForeground(self.BREAKPOINT_MARKER, "darkgrey") 

        # Disabled Breakpoint Marker (for breakpoints that aren't currently active)
        self.MarkerDefine(self.DISABLED_BREAKPOINT_MARKER, stc.STC_MARK_CIRCLE)
        self.MarkerSetBackground(self.DISABLED_BREAKPOINT_MARKER, "grey") 
        #self.MarkerSetForeground(self.DISABLED_BREAKPOINT_MARKER, "darkgrey") 

        self.MarkerDefine(self.ERROR_BKGND_MARKER, stc.STC_MARK_BACKGROUND)
        self.MarkerSetBackground(self.ERROR_BKGND_MARKER, wx.Colour(255,0,0))
        
                
    def on_update_ui(self, evt):
        self.controller.frame.statusbar.line = self.current_line()+1
        self.update_line_numbers()
        evt.Skip()
        
    #def on_modified(self, evt):
    #    evt.Skip()
    
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
        self.mnu_runtohere = m.item("Run to Here...", func=self.on_run_to_here, icon="breakpoint.png", hide=[menu.TARGET_RUNNING, menu.TARGET_DETACHED], 
                                                                                  show=[menu.TARGET_HALTED,menu.TARGET_ATTACHED])
        self.mnu_runtohere.hide()
        
        self.mnu_jumptopc = m.item("Show Exec Location", func=self.on_go_to_pc, icon="pc_marker.png", hide=[menu.TARGET_RUNNING, menu.TARGET_DETACHED], 
                                                                                  show=[menu.TARGET_HALTED,menu.TARGET_ATTACHED])
        self.mnu_jumptopc.hide()
        
        self.mnu_set_bp = m.item("Set Breakpoint", func=self.on_breakpoint_here, icon="stop.png", hide=[menu.TARGET_RUNNING, menu.TARGET_DETACHED], 
                                                                                show=[menu.TARGET_HALTED, menu.TARGET_ATTACHED])

        self.mnu_enable_bp = m.item("Enable Breakpoint", func=self.on_enable_breakpoint, icon="stop.png", hide=[menu.TARGET_RUNNING, menu.TARGET_DETACHED], 
                                                                                show=[menu.TARGET_HALTED, menu.TARGET_ATTACHED])

        self.mnu_disable_bp = m.item("Disable Breakpoint", func=self.on_disable_breakpoint, icon="stop_disabled.png", hide=[menu.TARGET_RUNNING, menu.TARGET_DETACHED], 
                                                                                show=[menu.TARGET_HALTED, menu.TARGET_ATTACHED])

        self.mnu_clear_bp = m.item("Clear Breakpoint", func=self.on_clear_breakpoint, icon="ex.png", hide=[menu.TARGET_RUNNING, menu.TARGET_DETACHED], 
                                                                                show=[menu.TARGET_HALTED, menu.TARGET_ATTACHED])
        self.mnu_enable_bp.hide()
        self.mnu_disable_bp.hide()
        self.mnu_clear_bp.hide()
        
        self.mnu_add_watch = m.item("Add Watch", func=self.on_add_watch, icon="magnifier_zoom_in.png", hide=[menu.TARGET_RUNNING, menu.TARGET_DETACHED], show=[menu.TARGET_HALTED, menu.TARGET_ATTACHED])
        self.mnu_add_watch.hide()
        
        self.popup_menu = m

    def on_go_to_pc(self, evt):
        evt.Skip()

    def on_run_to_here(self, evt):
        line = self.line_from_point(self.click_pos)+1
        self.controller.run_to(self.file_path, line)

    def on_breakpoint_here(self, evt):
        line = self.line_from_point(self.click_pos)+1
        print self.project_rel_file_path, line
        self.controller.set_breakpoint(self.project_rel_file_path, line)
        
    def on_clear_breakpoint(self, evt):
        line = self.line_from_point(self.click_pos)+1        
        self.controller.clear_breakpoint_byfile(self.project_rel_file_path, line)

    def on_enable_breakpoint(self, evt):
        line = self.line_from_point(self.click_pos)+1        
        self.controller.enable_breakpoint_byfile(self.project_rel_file_path, line)

    def on_add_watch(self, evt):
        watch_str = self.GetSelectedText().strip()        
        self.controller.add_watch(watch_str)
        
    def on_disable_breakpoint(self, evt):
        line = self.line_from_point(self.click_pos)+1        
        self.controller.disable_breakpoint_byfile(self.project_rel_file_path, line)
        
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
            self.mnu_add_watch.hide()
        else:
            self.mnu_cut.show()
            self.mnu_copy.show()
            
        if self.controller.state == app.ATTACHED:
            if self.breakpoint_on_line(line):
                self.mnu_clear_bp.show()
                self.mnu_set_bp.hide()
                self.mnu_disable_bp.show()
                self.mnu_enable_bp.hide()
            else:
                self.mnu_clear_bp.hide()
                self.mnu_set_bp.show()
                self.mnu_disable_bp.hide()
                self.mnu_enable_bp.hide()

        else:
            self.mnu_clear_bp.hide()
            self.mnu_set_bp.hide()
            
        self.PopupMenu(self.popup_menu.build(self)) 
        evt.Skip()
        
    @property
    def name(self):
        if self.file_path:
            root, name = os.path.split(self.file_path)
        else:
            name = 'Untitled'
        
        return ("*" + name) if self.GetModify() else name 
    
    def apply_settings(self):
        settings = self.controller.settings.editor
        self.IndicatorSetStyle(1, stc.STC_INDIC_ROUNDBOX)
        self.IndicatorSetForeground(1, wx.RED)
        self.IndicatorSetStyle(2, stc.STC_INDIC_ROUNDBOX)
        self.IndicatorSetForeground(2, wx.BLUE)
        
        self.IndicatorSetStyle(0, 40)
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
        self.define_markers()
        self.apply_folding_settings()
        self.show_line_numbers()
        self.detect_language()

    def show_line_numbers(self):
        self.SetMarginType(self.LINE_MARGIN, stc.STC_MARGIN_NUMBER)
        self.update_line_numbers()

    def remove_exec_marker(self):
        self.MarkerDeleteAll(self.EXECUTION_MARKER)
        self.MarkerDeleteAll(self.EXECUTION_BKGND_MARKER)
        self.Refresh()
        
    def remove_error_marker(self):
        self.MarkerDeleteAll(self.ERROR_BKGND_MARKER)
        self.Refresh()

    def set_error_marker(self, line):
        self.MarkerAdd(line-1, self.ERROR_BKGND_MARKER)
        wx.CallLater(10, self.error_pulse, 128)
        self.Refresh()
        
    def error_pulse(self, amt):
        print "Error pulse: %s" % amt
        if amt >= 255:
            self.remove_error_marker()
            self.Refresh()
            return
        self.MarkerSetBackground(self.ERROR_BKGND_MARKER, wx.Colour(255, amt, amt))
        wx.CallLater(10, self.error_pulse, amt+10)                         

    def set_exec_marker(self, line):
        self.MarkerAdd(line-1, self.EXECUTION_MARKER)
        self.MarkerAdd(line-1, self.EXECUTION_BKGND_MARKER)
        self.Refresh()

    def remove_breakpoint_markers(self):
        self.MarkerDeleteAll(self.BREAKPOINT_MARKER)
        self.MarkerDeleteAll(self.DISABLED_BREAKPOINT_MARKER)
        self.Refresh()

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
        self.Refresh()

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
        else:
            self.SetMarginWidth(self.LINE_MARGIN, 0)
        self.Refresh()

    def detect_language(self):
        if self.controller:
            path = self.file_path
            manager = self.controller.style_manager
            if path:
                dir, filename = os.path.split(path)
                pre, ext = os.path.splitext(filename)
                language = manager.get_language(ext or pre)
            else:
                language = None
            self.apply_language(manager, language)

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
        self.StyleSetEOLFilled(id, s.eol_filled)
        self.Refresh()
       
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
        self.file_path = path

        file = None
        try:
            file = open(path, 'r')
            text = unicode(file.read(), 'utf-8', errors='replace')
            try:
                self.SetText(text)
            except:
                raise
                print "FIX THIS, HANDLE BINARY FILES GRACEFULLY!"
                
            self.EmptyUndoBuffer()
            self.SetSavePoint()
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
        self.Refresh()

class Notebook(aui.AuiNotebook):

    def __init__(self, parent):
        style = wx.BORDER_NONE
        style |= aui.AUI_NB_TAB_MOVE
        style |= aui.AUI_NB_TAB_SPLIT
        style |= aui.AUI_NB_CLOSE_BUTTON
        style |= aui.AUI_NB_WINDOWLIST_BUTTON
        
        super(Notebook, self).__init__(parent, -1, style=style)
        self.Bind(aui.EVT_AUINOTEBOOK_PAGE_CLOSE, self.on_page_close)
        self.Bind(aui.EVT_AUINOTEBOOK_PAGE_CHANGED, self.on_page_changed)
        self.controller = parent.controller
        self.create_popup_menu()
        self._tab_controls = {}
        self._right_up_position = (0,0)
        self._current_index = 0
      
    def create_popup_menu(self):
        m = menu.manager.menu()
        m.item('Close', icon='ex.png', func=self.on_close_tab)
        m.item('Close All', func=self.on_close_all_tabs)        
        m.item('Close Others', func=self.on_close_other_tabs)
        self.popup_menu = m
        
    def on_close_tab(self, evt):
        self.close_tab(self._current_index)
    
    def on_close_other_tabs(self, evt):
        for i in range(self._current_index):
            self.close_tab(i)
        i+=1
        while self.PageCount > 1:
            self.close_tab(1)
        # TODO FINISH
        pass
    
    def on_close_all_tabs(self, evt):
        while self.PageCount > 0:
            self.close_tab(0)
            
    def on_page_close(self, event):
        event.Veto()
        index = event.GetSelection()
        self.close_tab(index)
        
    def __iter__(self):
        return iter(self.get_windows())
    
    def on_page_changed(self, evt):
        try:
            window = self.get_window()
            if window:
                self.controller.frame.SetTitle("%s - Cuttlebug IDE" % window.name)
                self.controller.frame.statusbar.line = window.current_line()+1
        except Exception, e:
            print "Got a page changed event, but there was an exception!"
            print e
            
        evt.Skip()
        
    def on_tab_right_down(self, evt):
        order = self._tab_controls[evt.GetEventObject()]
        index = order[evt.GetSelection()]
        self._current_index = index
        self.SetSelection(index)
        evt.Skip()
        
    def on_right_up(self, evt):
        self._right_up_position = evt.GetPosition()
        evt.Skip()
    
    def on_tab_right_up(self, evt):
        order = self._tab_controls[evt.GetEventObject()]
        index = order[evt.GetSelection()]
        if index == self.GetSelection():
            frame = self.GetParent()
            evt.GetEventObject().PopupMenu(self.popup_menu.build(frame), self._right_up_position)
        evt.Skip()
        
    def on_tab_dclick(self, evt):
        order = self._tab_controls[evt.GetEventObject()]
#        index = order[evt.GetSelection()]
#        if index == self.GetSelection():
        frame = self.GetParent().GetParent()
        frame.toggle_editor_maximize()
            
#            evt.GetEventObject().PopupMenu(self.popup_menu.build(frame), self._right_up_position)

    def check_tabs(self):
        result = []
        for control in self._tab_controls.keys():
            if not control:
                del self._tab_controls[control]
                continue
            tab_order = []
            count = control.GetPageCount()
            for i in range(count):
                window = control.GetPage(i).window
                index = self.GetPageIndex(window)
                tab_order.append(index)
            self._tab_controls[control] = tab_order
            result.extend(tab_order)
        self._tab_order = result

    def bind_tab_events(self):
        for child in self.GetChildren():
            if child in self._tab_controls:
                continue
            if isinstance(child, aui.AuiTabCtrl):
                child.Bind(wx.EVT_RIGHT_UP, self.on_right_up)
                child.Bind(wx.EVT_LEFT_DCLICK, self.on_tab_dclick)
                child.Bind(aui.EVT_AUINOTEBOOK_TAB_RIGHT_UP, self.on_tab_right_up)
                child.Bind(aui.EVT_AUINOTEBOOK_TAB_RIGHT_DOWN, self.on_tab_right_down)
                self._tab_controls[child] = []
                
#    def update_names(self):
#        self.Freeze()
#        for window in self:
#            idx = self.GetPageIndex()
#            print self.window.name
#            self.SetPageText(idx, window.name)
#        self.Thaw()

    def on_modified(self, evt):
        editor = evt.GetEventObject()
        page = editor.GetParent()
        if page:
            idx = self.GetPageIndex(page)
            self.SetPageText(idx, editor.name)
        evt.Skip()
        
    def get_window(self, index=None):
        if index is None: index = self.GetSelection()
        return self.GetPage(index).editor if index >= 0 else None

    def get_windows(self):
        n = self.GetPageCount()
        return [self.get_window(i) for i in range(n)]

    def find(self):
        pane = self.get_window()
        if pane:
            pane.GetParent().find_bar.show_and_focus()
            
    def save(self):
        window = self.get_window()
        if window:
            if not window.file_path:
                self.save_as()
            window.save()
            idx = self.GetPageIndex(window.GetParent())
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
        idx = self.GetPageIndex(widget.GetParent())
        self.close_tab(index=idx)
        
    def close_tab(self, index=None):
        #self.Freeze()
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
        #self.Thaw()
        
        
    def get_file_tab(self, path):
        try:
            path = self.project.absolute_path(path)
        except:
            path = os.path.abspath(path)
        for window in self:
            if not window.file_path: continue
            p1 = os.path.normcase(path)
            p2 = os.path.normcase(window.file_path)
            if p1 == p2:
                return window
        return None

    def open(self, path):
        if os.path.exists(path):
            return self.create_file_tab(path)
        else:
            return None
        
    def create_file_tab(self, path=None):
        if path:
            if self.controller.project:
                path = self.controller.project.absolute_path(path)
            window = self.get_file_tab(path)

            if window:
                window.SetFocus()
                self.controller.frame.statusbar.line = window.current_line()+1
                return window
#            else:
#                print "No window for file %s" % repr(path)
                
            if not os.path.isfile(path): 
                return None
        
        #self.Freeze()
        panel = wx.Panel(self)
        edit_widget = EditorControl(panel, -1, style=wx.BORDER_NONE, controller=self.controller)
        quick_find_bar = QuickFindBar(panel, edit_widget)
        panel.editor = edit_widget
        panel.find_bar = quick_find_bar
        quick_find_bar.hide()
        
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(edit_widget, 1, wx.EXPAND)
        sizer.Add(quick_find_bar, 0)
        panel.SetSizer(sizer)
        if path:
            edit_widget.open_file(path)
        
        self.AddPage(panel, edit_widget.name, True)
        idx = self.GetPageIndex(panel)
        if idx >= 0:
            self.SetPageBitmap(idx, util.get_icon(icons.get_file_icon(path)))


        edit_widget.SetFocus()
        self.controller.frame.statusbar.line = edit_widget.current_line()+1
        #edit_widget.Bind(stc.EVT_STC_MODIFIED, self.on_modified)
        self.bind_tab_events()
        self.check_tabs()
        #self.Thaw()
        return edit_widget

