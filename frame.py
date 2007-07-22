import wx
import wx.aui as aui
import wx.stc as stc
import util, build, app, notebook, controls, views
import prefs
import styles, style_dialog
# TODO Application icon
class Frame(wx.Frame):

        def __init__(self, parent=None, title="Debugger"):
            super(Frame, self).__init__(parent, -1, title, size=(1024,768))
            self.menu_registry = {}
            self.manager = aui.AuiManager(self)

            self.Bind(wx.EVT_CLOSE, self.on_exit)
            self.create_menu_bar()
            self.create_status_bar()
            
            # Create views
            self.create_build_view()
            self.create_log_view()
            self.create_memory_view()
            self.create_locals_view()
            self.create_register_view()
            self.create_project_view()
            self.create_editor_view()
            self.manager.Update()

            self.controller = app.Controller(self)            
        
        def create_menu_bar(self):
            self.menu_registry['project_open'] = project_open =[]
            self.menu_registry['target_running'] = target_running = []
            self.menu_registry['target_attached'] = target_attached = []

            menubar = controls.BusyMenuBar()
            
            # FILE
            file = wx.Menu()
            util.menu_item(self, file, '&New...\tCtrl+N', self.on_new, icon="page_white_text.png")
            util.menu_item(self, file, '&Open...\tCtrl+O', self.on_open)
            util.menu_item(self, file, '&Close\tCtrl+W', self.on_close)
            util.menu_item(self, file, '&Save\tCtrl+S', self.on_save, icon="disk.png")
            util.menu_item(self, file, '&Save As...\tCtrl+Shift+S', self.on_save_as, icon="save_as.png")

            file.AppendSeparator()
            util.menu_item(self, file, '&Exit\tAlt+F4', self.on_exit,icon="door_out.png")
            menubar.Append(file, '&File')
            
            # EDIT
            edit = wx.Menu()
            menubar.Append(edit, '&Edit')
            util.menu_item(self, edit, '&Styles...', self.on_styles)

            # Project Menu
            project = wx.Menu()
            util.menu_item(self, project, '&New Project...', self.on_new_project, icon="package.png")
            util.menu_item(self, project, '&Open Project...', self.on_open_project)
            util.menu_item(self, project, '&Save Project...\tCtrl+S', self.on_save_project, icon="disk.png", registries=[self.menu_registry['project_open']])
            project.AppendSeparator()
            util.menu_item(self, project, 'Project Options...', self.on_project_options, icon='cog_edit.png', registries=[self.menu_registry['project_open']])
            menubar.Append(project, '&Project')
            # BUILD
            build = wx.Menu()
            util.menu_item(self, build, '&Build\tF7', self.on_build, icon="brick.png",registries=[self.menu_registry['project_open']])
            util.menu_item(self, build, '&Clean\tF8', self.on_clean,registries=[self.menu_registry['project_open']])
            util.menu_item(self, build, '&Rebuild\tF10', self.on_rebuild,registries=[self.menu_registry['project_open']])
            menubar.Append(build, '&Build')
           
            # DEBUG (Disabled till a project is opened)
            debug = wx.Menu()
            util.menu_item(self, debug, '&Run\tF5', self.on_run, icon="control_play_blue.png", registries=[target_attached])
            util.menu_item(self, debug, '&Step\tF6', self.on_step, icon="control_play_blue.png", registries=[target_attached])
            util.menu_item(self, debug, '&Step Out\tShift+F6', self.on_step_out, icon="control_play_blue.png", registries=[target_attached])
            util.menu_item(self, debug, '&Halt\tShift+F5', self.on_halt, icon="control_stop_blue.png", registries=[target_running])
            debug.AppendSeparator()
            util.menu_item(self, debug, "Download", self.on_download, icon="application_put.png", registries=[target_attached])
            debug.AppendSeparator()
            util.menu_item(self, debug, '&Attach', self.on_attach, icon="connect.png", registries=[project_open])
            util.menu_item(self, debug, '&Detach', self.on_detach, icon="disconnect.png", registries=[project_open])
            menubar.Append(debug, '&Debug')

            # VIEW
            view = wx.Menu()
            util.menu_item(self, view, '&Build Log\tAlt+B', self.on_toggle_build_view, icon="application_view_list.png")
            menubar.Append(view, '&View')

            # DEVELOPMENT (Remove for production)
            devel = wx.Menu()
            util.menu_item(self, devel, '&Development Stuff Goes Here', lambda x : None)
            util.menu_item(self, devel, '&Read Memory', self.on_read_memory)
            util.menu_item(self, devel, '&GDB Command...', self.on_gdb_command)
            menubar.Append(devel, '&Devel')

            self.disable_menuitems('project_open')
            self.disable_menuitems('target_attached')
            self.disable_menuitems('target_running')

            self.SetMenuBar(menubar)
        
        def browse_for_file(self, message='', dir='', file='', style=wx.FD_OPEN, wildcard=""):
            dlg = wx.FileDialog(self, message=message, defaultDir=dir, defaultFile=file, wildcard=wildcard, style=style)
            if dlg.ShowModal() == wx.ID_OK:
                if style & wx.FD_MULTIPLE:
                    return dlg.GetPaths()
                else:
                    return dlg.GetPaths()[0]
            else:
                return None

        def disable_menuitems(self, entry):
            for item in self.menu_registry[entry]:
                item.Enable(False)

        def enable_menuitems(self, entry):
            for item in self.menu_registry[entry]:
                item.Enable()

        def error(self, message="Unspecified Error."):
            dlg = wx.MessageDialog(self, message=message, style=wx.ICON_ERROR)
            dlg.ShowModal()

        def on_project_options(self, evt):
            prefs.ProjectOptionsDialog.show(self, project=self.controller.project)

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
            self.memory_view = views.MemoryView(self)
            self.memory_view.info = aui.AuiPaneInfo().Caption('Memory').Right() 
            self.manager.AddPane(self.memory_view, self.memory_view.info)
        
        def create_locals_view(self):
            self.locals_view = views.LocalsView(self)
            self.locals_view.info = aui.AuiPaneInfo().Caption('Locals').Right() 
            self.manager.AddPane(self.locals_view, self.locals_view.info)
        
        def create_register_view(self):
            pass

        def create_build_view(self):
            self.build_view = views.BuildView(self)
            self.build_view.info = aui.AuiPaneInfo().Caption('Build').Bottom() 
            self.manager.AddPane(self.build_view, self.build_view.info)
        
        def create_log_view(self):
            self.log_view = views.LogView(self)
            self.log_view.info = aui.AuiPaneInfo().Caption('Logs').Bottom() 
            self.manager.AddPane(self.log_view, self.log_view.info)

        def create_editor_view(self):
            self.editor_view = views.EditorView(self)
            self.editor_view.info = aui.AuiPaneInfo().CentrePane().PaneBorder(False)
            self.manager.AddPane(self.editor_view, self.editor_view.info)

        def create_project_view(self):
            self.project_view = views.ProjectView(self)
            self.project_view.info = aui.AuiPaneInfo().Caption('Project').Left() 
            self.manager.AddPane(self.project_view, self.project_view.info)
        
        def open_file(self, path):
            self.editor_view.notebook.create_file_tab(path)


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
            self.controller.save_session()
            evt.Skip()
            self.Close()

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
            self.controller.halt()

        def on_download(self, evt):
            self.controller.download()
