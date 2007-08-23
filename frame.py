import wx
import wx.aui as aui
import wx.stc as stc
import util, build, app, notebook, controls, views, project, settings, menu
import styles, style_dialog
# TODO Application icon
class Frame(wx.Frame):

        def __init__(self, parent=None, title="Cuttlebug"):
            super(Frame, self).__init__(parent, -1, title, size=(1024,768))

            self.controller = app.Controller(self)            

            self.Bind(wx.EVT_CLOSE, self.on_close)

            # Create frame UI (menus, status, etc)
            self.create_menu_bar()
            self.create_status_bar()
            
            # Create views
            self.manager = aui.AuiManager(self)
            self.create_build_view()
            self.create_log_view()
            self.create_memory_view()
            self.create_locals_view()
            self.create_breakpoint_view()
            self.create_register_view()
            self.create_project_view()
            self.create_editor_view()
            
            self.controller.setup_logs()
            self.controller.load_session()
            self.manager.Update()
            
        def create_menu_bar(self):
            menubar = menu.manager.menu_bar(self)

            # FILE
            file = menubar.menu("&File")
            file.item('&New...\tCtrl+N', self.on_new, icon="page_white_text.png")
            file.item('&Open...\tCtrl+O', self.on_open)
            file.item('&Close\tCtrl+W', self.on_close)
            file.item('&Save\tCtrl+S', self.on_save, icon="disk.png")
            file.item('&Save As...\tCtrl+Shift+S', self.on_save_as, icon="save_as.png")
            file.separator()
            file.item('&Exit\tAlt+F4', self.on_exit,icon="door_out.png")
            
            # EDIT
            edit = menubar.menu("&Edit")
            edit.item('&Undo\tCtrl+Z', self.on_undo)
            edit.item('&Redo\tCtrl+Y', self.on_redo)
            edit.separator()
            edit.item('Cu&t\tCtrl+X', self.on_cut, icon='cut.png')
            edit.item('&Copy\tCtrl+C', self.on_copy, icon='page_copy.png')
            edit.item('&Paste\tCtrl+V', self.on_paste, icon='paste_plain.png')            
            edit.separator()
            edit.item('&Styles...', self.on_styles, icon="style.png")
            edit.item('&Options...', self.on_settings, icon='cog_edit.png')

            # Project Menu
            project = menubar.menu("&Project")
            project.item('&New Project...', self.on_new_project, icon="package.png")
            project.item('&Open Project...', self.on_open_project)
            project.item('&Save Project\tCtrl+S', self.on_save_project, icon="disk.png", enable=menu.PROJECT_OPEN, disable=menu.PROJECT_CLOSE)
            project.separator()
            project.item('Project Options...', self.on_project_options, icon='cog_edit.png', enable=menu.PROJECT_OPEN, disable=menu.PROJECT_CLOSE)
            
            # BUILD
            build = menubar.menu("&Build")
            build.item('&Build\tF7', self.on_build, icon="brick.png",enable=menu.PROJECT_OPEN, disable=menu.PROJECT_CLOSE)
            build.item('&Clean\tF8', self.on_clean,enable=menu.PROJECT_OPEN, disable=menu.PROJECT_CLOSE)
            build.item('&Rebuild\tF10', self.on_rebuild,enable=menu.PROJECT_OPEN, disable=menu.PROJECT_CLOSE)
           
            # DEBUG (Disabled till a project is opened)
            debug = menubar.menu("&Debug")
            debug.item('&Run\tF5', self.on_run, icon="control_play_blue.png", enable=menu.TARGET_ATTACHED, disable=[menu.TARGET_RUNNING, menu.TARGET_DETACHED])
            debug.item('&Step\tF6', self.on_step, icon="control_play_blue.png", enable=menu.TARGET_ATTACHED, disable=[menu.TARGET_RUNNING, menu.TARGET_DETACHED])
            debug.item('&Step Out\tShift+F6', self.on_step_out, icon="control_play_blue.png", enable=menu.TARGET_ATTACHED, disable=[menu.TARGET_RUNNING, menu.TARGET_DETACHED])
            debug.item('&Halt\tShift+F5', self.on_halt, icon="control_stop_blue.png", enable=menu.TARGET_RUNNING, disable=[menu.TARGET_HALTED, menu.TARGET_DETACHED])
            debug.separator()
            debug.item("Download", self.on_download, icon="application_put.png", enable=menu.TARGET_ATTACHED)
            debug.separator()
            debug.item('&Attach', self.on_attach, icon="connect.png", show=[menu.PROJECT_OPEN, menu.TARGET_DETACHED], hide=[menu.TARGET_ATTACHED, menu.PROJECT_CLOSE])
            debug.item('&Detach', self.on_detach, icon="disconnect.png", show=menu.TARGET_ATTACHED, hide=menu.TARGET_DETACHED)

            # VIEW
            view = menubar.menu("&View")
            view.item('&Build Log\tAlt+B', self.on_toggle_build_view, icon="application_view_list.png")

            # DEVELOPMENT (Remove for production)
            devel = menubar.menu("&Devel")
            devel.item( 'Development Stuff Goes Here', lambda x : None)
            devel.item( 'Read Memory', self.on_read_memory)
            devel.item('&GDB Command...', self.on_gdb_command)

            menu.manager.publish(menu.PROJECT_CLOSE)
            menu.manager.publish(menu.TARGET_DETACHED)
        
        
        def on_cut(self, evt):
            pass
        
        def on_copy(self,evt):
            pass
        
        def on_paste(self,evt):
            pass
        
        def on_undo(self,evt):
            pass
        
        def on_redo(self,evt):
            pass
        
        def browse_for_file(self, message='', dir='', file='', style=wx.FD_OPEN, wildcard=""):
            dlg = wx.FileDialog(self, message=message, defaultDir=dir, defaultFile=file, wildcard=wildcard, style=style)
            if dlg.ShowModal() == wx.ID_OK:
                if style & wx.FD_MULTIPLE:
                    return dlg.GetPaths()
                else:
                    return dlg.GetPaths()[0]
            else:
                return None

        def error(self, message="Unspecified Error."):
            dlg = wx.MessageDialog(self, message=message, style=wx.ICON_ERROR)
            dlg.ShowModal()

        def on_project_options(self, evt):
            project.ProjectOptionsDialog.show(self, project=self.controller.project)
            self.project_view.update()

        def on_read_memory(self, evt):
            if self.controller.state is app.ATTACHED:
                self.controller.gdb.read_memory(0,100)

        def on_gdb_command(self, evt):
            if self.controller.state is app.ATTACHED or self.controller.state is app.RUNNING:
                dlg = wx.TextEntryDialog(self, "Enter GDB Command:")
                btn = dlg.ShowModal()
                if btn == wx.ID_OK:
                    self.controller.gdb.command(dlg.GetValue())
            else:
                print "GDB Session not attached"

        def create_status_bar(self):
            self.statusbar = controls.StatusBar(self)
            self.statusbar.icon = "disconnect.png"
            self.SetStatusBar(self.statusbar)

        def create_memory_view(self):
            self.memory_view = views.MemoryView(self, controller=self.controller)
            self.memory_view.info = aui.AuiPaneInfo().Caption('Memory').Right() 
            self.manager.AddPane(self.memory_view, self.memory_view.info)
        
        def create_breakpoint_view(self):
            self.breakpoint_view = views.BreakpointView(self, controller=self.controller)
            self.breakpoint_view.info = aui.AuiPaneInfo().Caption('Breakpoints').Right() 
            self.manager.AddPane(self.breakpoint_view, self.breakpoint_view.info)

        def create_locals_view(self):
            self.locals_view = views.LocalsView(self, controller=self.controller)
            self.locals_view.info = aui.AuiPaneInfo().Caption('Locals').Right() 
            self.manager.AddPane(self.locals_view, self.locals_view.info)
        
        def create_register_view(self):
            pass

        def create_build_view(self):
            self.build_view = views.BuildView(self, controller=self.controller)
            self.build_view.info = aui.AuiPaneInfo().Caption('Build').Bottom() 
            self.manager.AddPane(self.build_view, self.build_view.info)
        
        def create_log_view(self):
            self.log_view = views.LogView(self, controller = self.controller)
            self.log_view.info = aui.AuiPaneInfo().Caption('Logs').Bottom() 
            self.manager.AddPane(self.log_view, self.log_view.info)

        def create_editor_view(self):
            self.editor_view = views.EditorView(self, controller=self.controller)
            self.editor_view.info = aui.AuiPaneInfo().CentrePane().PaneBorder(False)
            self.manager.AddPane(self.editor_view, self.editor_view.info)

        def create_project_view(self):
            self.project_view = views.ProjectView(self, controller=self.controller)
            self.project_view.Bind(views.EVT_PROJECT_DCLICK_FILE, self.on_project_dclick_file)

            self.project_view.info = aui.AuiPaneInfo().Caption('Project').Left() 
            self.manager.AddPane(self.project_view, self.project_view.info)
        
        def open_file(self, path):
            self.editor_view.notebook.create_file_tab(path)

        def on_project_dclick_file(self, evt):
            self.open_file(evt.data)

        # Event Handlers
        def on_open(self, evt):
            dialog = wx.FileDialog(self, 'Open', style=wx.FD_OPEN|wx.FD_FILE_MUST_EXIST|wx.FD_MULTIPLE)
            result = dialog.ShowModal()
            if result == wx.ID_OK:
                paths = dialog.GetPaths()
                for path in paths:
                    self.open_file(path)

        def on_open_project(self, evt):
            dialog = wx.FileDialog(self, 'Open Project', style=wx.FD_OPEN|wx.FD_FILE_MUST_EXIST)
            result = dialog.ShowModal()
            if result == wx.ID_OK:
                path = dialog.GetPaths()[0]
                self.controller.load_project(path)

        def on_new_project(self, evt):
            if self.controller.project:
                pass
            path = self.browse_for_file(style=wx.FD_SAVE)
            self.controller.new_project(path)
        
        def on_save_project(self, evt):
            self.controller.save_project()

        def on_save(self, evt):
            self.editor_view.save()

        def on_save_as(self, evt):
            pass

        def on_close(self, evt):
            pass

        def on_styles(self, evt):
            dialog = style_dialog.StyleDialog(None, self.controller.style_manager)
            dialog.Centre()
            dialog.ShowModal() 
        
        def on_new(self, evt):
            self.editor_view.new()

        def on_exit(self, evt):
            self.Close()
        
        def on_close(self, evt):
            self.controller.save_session()
            evt.Skip()

        def on_attach(self, evt):
            self.controller.attach()
        
        def on_detach(self, evt):
            self.controller.detach()

        def on_toggle_build_view(self, evt):
            self.build_view.info.Show(not self.build_view.info.IsShown())
            self.manager.Update()

        def on_toggle_log_view(self, evt):
            self.log_view.info.Show(not self.log_view.info.IsShown())
            self.manager.Update()

        def on_settings(self, evt):
            settings.SettingsDialog.show(self, self.controller.settings)
            self.controller.settings.save()
            self.controller.update_settings()

        # Events that manage the build process
        def on_clean(self, evt):
            wx.CallAfter(self.controller.clean)

        def on_rebuild(self, evt):
            wx.CallAfter(self.controller.rebuild)

        def on_build(self, evt):
            wx.CallAfter(self.controller.build)

        def on_run(self, evt):
            self.controller.run()

        def on_step(self, evt):
            self.controller.step()

        def on_step_out(self, evt):
            self.controller.step_out()

        def on_halt(self, evt):
            print "halt handler called"
            self.controller.halt()

        def on_download(self, evt):
            self.controller.download()
