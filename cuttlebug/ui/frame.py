import wx
import wx.aui as aui
#import wx.stc as stc
import cuttlebug.util as util
import cuttlebug.app as app
#import cuttlebug.build as build
import cuttlebug.project as project
import cuttlebug.settings as settings

import notebook, controls, views, menu
import styles, style_dialog
#TODO implement custom build targets
class Frame(util.PersistedFrame):

        def __init__(self, parent=None, title="Cuttlebug"):
            super(Frame, self).__init__(parent, -1, title, size=(1024,768), style=wx.DEFAULT_FRAME_STYLE & ~wx.TAB_TRAVERSAL)
            self.SetIcon(wx.Icon('icons/cuttlebug.png', wx.BITMAP_TYPE_PNG))
            self.controller = app.Controller(self)            
            self.editor_maximized = False
            self.saved_perspective = ''
            self.Bind(wx.EVT_CLOSE, self.on_close)

            # Create frame UI (menus, status, etc)
            self.create_menu_bar()
            self.create_status_bar()
            
            # Create views
            self.manager = aui.AuiManager(self)

            self.create_views()
            
            self.controller.setup_logs()
            self.controller.load_session()
            self.controller.setup_gdb()
            
            self.manager.Update()

           
            print "Welcome to Cuttlebug!"

            
        def create_menu_bar(self):
            menubar = menu.manager.menu_bar(self)

            # FILE
            file = menubar.menu("&File")
            file.item('&New...\tCtrl+N', self.on_new, icon="page_white_text.png")
            file.item('&Open...\tCtrl+O', self.on_open, icon="folder_page.png")
            file.item('&Close\tCtrl+W', self.on_close_file, icon="ex.png")
            file.item('&Save\tCtrl+S', self.on_save, icon="disk.png")
            file.item('Save As...\tCtrl+Shift+S', self.on_save_as, icon="save_as.png")
            file.item('Save All\tCtrl+Alt+Shift+S', self.on_save_all, icon="disk_cascade.png")
            file.separator()
            file.item('&Exit\tAlt+F4', self.on_exit,icon="door_out.png")
            
            # EDIT
            edit = menubar.menu("&Edit")
            edit.item('&Undo\tCtrl+Z', self.on_undo, icon='edit-undo.png')
            edit.item('&Redo\tCtrl+Y', self.on_redo, icon='edit-redo.png')
            edit.separator()
            edit.separator()
            edit.item('Cu&t\tCtrl+X', self.on_cut, icon='cut.png')
            edit.item('&Copy\tCtrl+C', self.on_copy, icon='page_copy.png')
            edit.item('&Paste\tCtrl+V', self.on_paste, icon='paste_plain.png')  
            edit.item('&Find...\tCtrl+F', self.on_find, icon='find.png')          
            edit.separator()
            edit.item('&Fonts and Colors...', self.on_styles, icon="style.png")
            edit.item('&Options...', self.on_settings, icon='cog_edit.png')

            # Project Menu
            project = menubar.menu("&Project")
            project.item('&New Project...', self.on_new_project, icon="package.png")
            project.item('&Open Project...', self.on_open_project, icon="package_add.png")
            project.item('&Close Project', self.on_close_project, icon='package_delete.png', enable=menu.PROJECT_OPEN, disable=menu.PROJECT_CLOSE)
            project.item('&Save Project', self.on_save_project, icon="package_save.png", enable=menu.PROJECT_OPEN, disable=menu.PROJECT_CLOSE)
            project.separator()
            project.item('Project Options...', self.on_project_options, icon='cog_edit.png', enable=menu.PROJECT_OPEN, disable=menu.PROJECT_CLOSE)
            
            # BUILD
            build = menubar.menu("&Build")
            build.item('&Build\tF7', self.on_build, icon="brick.png",enable=[menu.PROJECT_OPEN, menu.BUILD_FINISHED], disable=[menu.PROJECT_CLOSE, menu.BUILD_STARTED])
            build.item('&Rebuild\tF10', self.on_rebuild, icon="rebuild.png", enable=[menu.PROJECT_OPEN, menu.BUILD_FINISHED], disable=[menu.PROJECT_CLOSE, menu.BUILD_STARTED])
            build.item('&Clean\tF8', self.on_clean, icon="edit-clear.png", enable=[menu.PROJECT_OPEN, menu.BUILD_FINISHED], disable=[menu.PROJECT_CLOSE, menu.BUILD_STARTED])
            build.separator()
            #build.item('New Custom Build &Target...', self.on_new_build_target, icon="brick.png",enable=[menu.PROJECT_OPEN, menu.BUILD_FINISHED], disable=[menu.PROJECT_CLOSE, menu.BUILD_STARTED])
            # DEBUG (Disabled till a project is opened)
            debug = menubar.menu("&Debug")
            debug.item('&Run\tF5', self.on_run, icon="run.png", enable=menu.TARGET_ATTACHED, disable=[menu.TARGET_RUNNING, menu.TARGET_DETACHED])
            debug.item('&Step\tF6', self.on_step, icon="step.png", enable=menu.TARGET_ATTACHED, disable=[menu.TARGET_RUNNING, menu.TARGET_DETACHED])
            debug.item('&Step Over\tCtrl+F6', self.on_step_over, icon="step.png", enable=menu.TARGET_ATTACHED, disable=[menu.TARGET_RUNNING, menu.TARGET_DETACHED])
            debug.item('&Step Out\tShift+F6', self.on_step_out, icon="step-out.png", enable=menu.TARGET_ATTACHED, disable=[menu.TARGET_RUNNING, menu.TARGET_DETACHED])

            debug.item('&Step Instruction\tCtrl+F6', self.on_step_instruction, icon="step-instruction.png", enable=menu.TARGET_ATTACHED, disable=[menu.TARGET_RUNNING, menu.TARGET_DETACHED])
            debug.item('&Halt\tShift+F5', self.on_halt, icon="halt.png", enable=menu.TARGET_RUNNING, disable=[menu.TARGET_HALTED, menu.TARGET_DETACHED])
            debug.separator()
            debug.item('&Attach', self.on_attach, icon="connect.png", show=[menu.PROJECT_OPEN, menu.TARGET_DETACHED], hide=[menu.TARGET_ATTACHED], disable=menu.PROJECT_CLOSE, enable=[menu.PROJECT_OPEN, menu.TARGET_DETACHED])
            debug.item('&Detach', self.on_detach, icon="disconnect.png", show=menu.TARGET_ATTACHED, hide=menu.TARGET_DETACHED)
            debug.separator()
            debug.item("Reset", self.on_reset, icon="chip.png", enable=menu.TARGET_ATTACHED, disable=[menu.TARGET_RUNNING, menu.TARGET_DETACHED])
            debug.item("Download", self.on_download, icon="application_put.png", enable=menu.TARGET_ATTACHED, disable=menu.TARGET_DETACHED)
            
            # VIEW
            view = menubar.menu("&View")
            view.item('&Project\tAlt+P', self.on_toggle_project_view, icon="package.png")
            view.item('&Runtime\tAlt+R', self.on_toggle_runtime_view, icon="computer.png")
            view.item('&Logs\tAlt+L', self.on_toggle_log_view, icon="application_view_list.png")
            #view.item('&Debug\tAlt+D', self.on_toggle_debug_view, icon="bug.png")
            view.item('&Disassembly\tAlt+A', self.on_toggle_disassembly_view, icon="chip.png")
            view.item('&Memory\tAlt+M', self.on_toggle_memory_view, icon="chip.png")
        
            menu.manager.publish(menu.TARGET_DETACHED)
            menu.manager.publish(menu.PROJECT_CLOSE)
            
        def save_perspective(self):
            self.saved_perspective = self.manager.SavePerspective()
            return self.saved_perspective
        
        def restore_perspective(self, perspective=None):
            perspective = perspective or self.saved_perspective
            self.manager.LoadPerspective(perspective)
        
        def maximize_editor(self):
            self.editor_maximized = True
            self.saved_perspective = self.manager.SavePerspective()
            self.hide_views(*[view for view in self.views if view != self.editor_view])
            
        def restore_editor(self):
            self.editor_maximized = False
            self.manager.LoadPerspective(self.saved_perspective)
            self.restore_perspective()
        
        def toggle_editor_maximize(self):
            if self.editor_maximized:
                self.restore_editor()
            else:
                self.maximize_editor()
                
        def start_busy_frame(self):
            self.busy_frame = controls.BusyFrame(self, 'Downloading to target...', util.get_icon('download_static.png'))
            self.busy_frame.CenterOnParent()
            self.busy_frame.Show()
            
        def stop_busy_frame(self):
            if self.busy_frame:
                self.busy_frame.Close()
                self.busy_frame = None
                
        def start_busy(self, message=''):
            self.statusbar.message = message
            self.statusbar.working = True
            
        def stop_busy(self):
            self.statusbar.message = ''
            self.statusbar.working = False
            
        def on_cut(self, evt):
            self.editor_view.cut()
        
        def on_copy(self,evt):
            self.editor_view.copy()
        
        def on_paste(self,evt):
            self.editor_view.paste()
        
        def on_undo(self,evt):
            self.editor_view.undo()
        
        def on_redo(self,evt):
            self.editor_view.redo()
        
        def on_find(self, evt):
            self.editor_view.find()
            
        def error_msg(self, message, caption="Error"):
            wx.CallAfter(self._error_msg, message, caption)
            
        def _error_msg(self, message, caption):
            dialog = wx.MessageDialog(self, message = message, caption=caption, style=wx.ICON_ERROR | wx.OK)
            return dialog.ShowModal()
            
        def confirm(self, message, caption="Confirmation"):
            dialog = wx.MessageDialog(self, message=message, caption=caption, style=wx.ICON_QUESTION | wx.YES_NO | wx.CANCEL)
            response = dialog.ShowModal()
            if response == wx.ID_CANCEL: return None
            return True if response == wx.ID_YES else False
        
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
            dlg = wx.MessageDialog(self, message=str(message), style=wx.ICON_ERROR)
            dlg.ShowModal()

        def on_project_options(self, evt):
            project.ProjectOptionsDialog.show(self, project=self.controller.project)
            self.project_view.update()

        def on_read_memory(self, evt):
            if self.controller.state is app.ATTACHED:
                self.controller.gdb.read_memory(0,100)

        def add_view(self, view):
            self.manager.AddPane(view, view.info)
            
        def create_views(self):
            
            self.log_view = views.LogView(self, controller = self.controller)
            self.log_view.info = aui.AuiPaneInfo().Caption('Logs').Bottom().Name('LogView') 
            self.manager.AddPane(self.log_view, self.log_view.info)

            self.editor_view = views.EditorView(self, controller=self.controller)
            self.editor_view.info = aui.AuiPaneInfo().CentrePane().PaneBorder(False).Name('EditorView')
            self.manager.AddPane(self.editor_view, self.editor_view.info)

            self.project_view = views.ProjectView(self, controller=self.controller)
            self.project_view.Bind(views.EVT_PROJECT_DCLICK_FILE, self.on_project_dclick_file)
            self.project_view.info = aui.AuiPaneInfo().Caption('Project').Left().Name('ProjectView') 
            self.manager.AddPane(self.project_view, self.project_view.info)
    
            self.runtime_view = views.RuntimeView(self, style=0, controller=self.controller)
            self.runtime_view.info = aui.AuiPaneInfo().Caption('Runtime').Right().Name('RuntimeView').MinSize((250,50))
            self.manager.AddPane(self.runtime_view, self.runtime_view.info)

            #self.debug_view = views.GDBDebugView(self, controller=self.controller)
            #self.debug_view.info = aui.AuiPaneInfo().Caption('Debug').Right().Name('DebugView').MinSize((250,50))
            #self.manager.AddPane(self.debug_view, self.debug_view.info)

            self.disassembly_view = views.DisassemblyView(self, controller=self.controller)
            self.disassembly_view.info = aui.AuiPaneInfo().Caption('Disassembly').Right().Name('DisassemblyView').MinSize((250,50))
            self.manager.AddPane(self.disassembly_view, self.disassembly_view.info)

            self.memory_view = views.MemoryView(self, controller=self.controller)
            self.memory_view.info = aui.AuiPaneInfo().Caption('Memory').Right().Name('MemoryView').MinSize((250,50))
            self.manager.AddPane(self.memory_view, self.memory_view.info)
    
            self.views = [self.log_view, self.editor_view, self.project_view, self.runtime_view, self.disassembly_view]
            
        def create_status_bar(self):
            self.statusbar = controls.StatusBar(self)
            self.statusbar.set_icon(self.statusbar.DISCONNECTED)
            self.SetStatusBar(self.statusbar)        
        
        def open_file(self, path):
            self.editor_view.notebook.open(path)

        def on_project_dclick_file(self, evt):
            self.open_file(evt.data)

        # Event Handlers
        def on_open(self, evt):
            dialog = wx.FileDialog(self, 'Open', style=wx.FD_OPEN|wx.FD_FILE_MUST_EXIST|wx.FD_MULTIPLE)
            dialog.CenterOnParent()
            dialog.Center()
            dialog.CenterOnScreen()
            result = dialog.ShowModal()
            if result == wx.ID_OK:
                paths = dialog.GetPaths()
                for path in paths:
                    self.open_file(path)

        def on_open_project(self, evt):
            dialog = wx.FileDialog(self, 'Open Project', style=wx.FD_OPEN|wx.FD_FILE_MUST_EXIST)
            #dialog.CenterOnParent()
            result = dialog.ShowModal()
            if result == wx.ID_OK:
                path = dialog.GetPaths()[0]
                if self.controller.project:
                    for file in self.editor_view.open_files:
                        self.editor_view.close(file)

                self.controller.load_project(path)

        def on_close_project(self, evt):
            project = self.controller.project
            if project:
                if project.modified:
                    save_confirm = self.confirm("Save project '%s' before closing?" % project.general.project_name)
                    if save_confirm:
                        project.save()
                    else:
                        evt.Veto()
                        return
                    for file in self.editor_view.open_files:
                        self.editor_view.close(file)
                self.controller.unload_project()
        
        def on_new_project(self, evt):
            if self.controller.project:
                pass
            path = self.browse_for_file(style=wx.FD_SAVE)
            self.controller.new_project(path)
        def on_new_build_target(self, evt):
            print "TODO: Add functionality for this in the projects"
            
        def on_save_project(self, evt):
            self.controller.save_project()

        def on_save(self, evt):
            try:
                self.editor_view.save()
            except Exception, e:
                self.error_msg(str(e), "Problem saving file!")
                
        def on_save_as(self, evt):
            self.editor_view.save_as()
        
        def on_save_all(self, evt):
            self.editor_view.save_all()
            
        def on_close_file(self, evt):
            self.editor_view.close()

        def on_styles(self, evt):
            dialog = style_dialog.StyleDialog(self, self.controller.style_manager, on_apply=self.controller.update_styles)
            dialog.CentreOnParent()
            dialog.ShowModal() 
        
        def on_new(self, evt):
            self.editor_view.new()

        def on_exit(self, evt):
            self.Close()
        
        def on_close(self, evt):
            project = self.controller.project
            if project:
                if project.modified:
                    save_confirm = self.confirm("Save project '%s' before quitting?" % project.general.project_name)
                    if save_confirm:
                        project.save()
                    elif save_confirm == None:
                        evt.Veto()
                        return
            if self.editor_view.has_unsaved_files:
                save_confirm = self.confirm("Save modified files before quitting?")
                if save_confirm:
                    try:
                        self.editor_view.save_all()
                    except Exception, e:
                        self.error_msg(str(e), "Problem saving file!")
                        evt.Veto()
                        return
                        
                elif save_confirm == None:
                    evt.Veto()
                    return
                    
            self.controller.save_session()
            self.controller.detach()
            evt.Skip()

        def on_attach(self, evt):
            self.controller.attach()
        
        def on_detach(self, evt):
            self.controller.detach()

        def on_toggle_log_view(self, evt):
            self.toggle_view(self.log_view)
        def on_toggle_breakpoint_view(self, evt):
            self.toggle_view(self.breakpoint_view)
        def on_toggle_memory_view(self, evt):
            self.toggle_view(self.memory_view)
        def on_toggle_project_view(self, evt):
            self.toggle_view(self.project_view)
        def on_toggle_runtime_view(self, evt):
            self.toggle_view(self.runtime_view)
        def on_toggle_debug_view(self, evt):
            self.toggle_view(self.debug_view)
        def on_toggle_disassembly_view(self, evt):
            self.toggle_view(self.disassembly_view)
            
        def toggle_view(self, view):
            info = self.manager.GetPane(view)
            info.Show(not info.IsShown())
            self.manager.Update()
            
        def hide_views(self, *v):
            for view in v:
                info = self.manager.GetPane(view)
                info.Show(False)
            self.manager.Update()
            
        def on_settings(self, evt):
            settings.SettingsDialog.show(self, self.controller.settings, on_apply=self.controller.update_settings)

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

        def on_step_instruction(self, evt):
            self.controller.step_instruction()
            
        def on_step_out(self, evt):
            self.controller.step_out()

        def on_step_over(self, evt):
            self.controller.step_over()

        def on_halt(self, evt):
            self.controller.halt()

        def on_download(self, evt):
            self.controller.download()

        def on_reset(self, evt):
            self.controller.reset()
