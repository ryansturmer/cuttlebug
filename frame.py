import wx
import wx.aui as aui
import wx.stc as stc
import util, build, app, notebook, controls, views
import prefs

# TODO Application icon
class Frame(wx.Frame):

        def __init__(self, parent=None, title="Debugger"):
            super(Frame, self).__init__(parent, -1, title, size=(800,600))
            self.manager = aui.AuiManager(self)
            #self.Bind(wx.EVT_CLOSE, self.on_exit)
            self.create_menu_bar()
            self.create_status_bar()
            self.create_notebook()
            
            # Create views
            self.create_build_view()
            self.create_log_view()
            self.create_memory_view()
            #self.create_register_view()

            self.manager.Update()

            self.controller = app.Controller(self)            

        def create_menu_bar(self):
            menubar = wx.MenuBar()
            
            # FILE
            file = wx.Menu()
            util.menu_item(self, file, '&Open...\tCtrl+O', self.on_open)
            file.AppendSeparator()
            util.menu_item(self, file, '&Exit\tAlt+F4', self.on_exit,icon="door_out.png")
            menubar.Append(file, '&File')

            # BUILD
            build = wx.Menu()
            util.menu_item(self, build, '&Build\tF7', self.on_build, icon="brick.png")
            util.menu_item(self, build, '&Clean\tF8', self.on_clean)
            util.menu_item(self, build, '&Rebuild\tF10', self.on_rebuild)
            menubar.Append(build, '&Build')
           
            # DEBUG
            debug = wx.Menu()
            util.menu_item(self, debug, '&Run\tF5', self.on_run, icon="control_play_blue.png")
            util.menu_item(self, debug, '&Halt\tShift+F5', self.on_halt, icon="control_stop_blue.png")
            debug.AppendSeparator()
            util.menu_item(self, debug, '&Attach', self.on_attach, icon="connect.png")
            util.menu_item(self, debug, '&Detach', self.on_detach, icon="disconnect.png")
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

            self.SetMenuBar(menubar)

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
            view = views.MemoryView(self)
            self.memory_view = view
            info = aui.AuiPaneInfo()
            info.Caption('Memory')
            info.Right()
            info.Dockable(True)
            info.MinSize(view.GetSize())
            info.BestSize(view.GetSize())
            info.FloatingSize(view.GetSize())
            self.manager.AddPane(view, info)
            self.memory_view.info = info
            self.memory_view.Bind(wx.grid.EVT_GRID_LABEL_LEFT_DCLICK, self.on_label_dclick)
        
        def on_label_dclick(self, evt):
            if self.controller.state == app.ATTACHED:
                self.controller.gdb.read_memory(0, 20)

        def create_register_view(self):
            view = views.RegisterView(self)
            self.register_view = view
            info = aui.AuiPaneInfo()
            info.Caption('Registers')
            info.Right()
            info.Dockable(True)
            info.MinSize(view.GetSize())
            info.BestSize(view.GetSize())
            info.FloatingSize(view.GetSize())
            self.manager.AddPane(view, info)
            self.register_view.info = info
            self.register_view.Bind(wx.grid.EVT_GRID_LABEL_LEFT_DCLICK, self.on_label_dclick)
        
        def create_build_view(self):
            view = views.BuildView(self)
            self.build_view = view
            info = aui.AuiPaneInfo()
            info.Caption('Build')
            info.Bottom()
            info.Dockable(True)
            info.MinSize(view.GetSize())
            info.BestSize(view.GetSize())
            info.FloatingSize(view.GetSize())
            self.manager.AddPane(view, info)
            self.build_view.info = info
        
        def create_log_view(self):
            view = views.LogView(self)
            self.log_view = view
            info = aui.AuiPaneInfo()
            info.Caption('Log')
            info.Bottom()
            info.Dockable(True)
            info.MinSize(view.GetSize())
            info.BestSize(view.GetSize())
            info.FloatingSize(view.GetSize())
            self.manager.AddPane(view, info)
            self.log_view.info = info

        def create_notebook(self):
            n = notebook.Notebook(self)
            self.notebook = n
            info = aui.AuiPaneInfo()
            info.CentrePane()
            info.PaneBorder(False)
            self.manager.AddPane(n, info)

        def open_file(self, path):
            self.notebook.create_file_tab(path)


        # Event Handlers
        def on_open(self, evt):
            dialog = wx.FileDialog(self, 'Open', style=wx.FD_OPEN|wx.FD_FILE_MUST_EXIST)
            result = dialog.ShowModal()
            if result == wx.ID_OK:
                paths = dialog.GetPaths()
                for path in paths:
                    self.open_file(path)

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

        def on_halt(self, evt):
            self.controller.halt()
