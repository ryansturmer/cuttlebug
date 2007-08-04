import build, views, gdb, project, log, styles, settings, util, menu
import logging, os
import wx

IDLE = 0
BUILDING = 1
ATTACHED = 2
CONNECTED = 3
RUNNING = 4

class Controller(wx.EvtHandler):

    def __init__(self, frame=None):
        super(Controller, self).__init__()

        self.style_manager = styles.StyleManager()
        self.state = IDLE
        self.gdb = None
        self.frame = frame
        self.project = None
        try:
            self.settings = settings.Settings.load(".settings")
        except Exception, e:
            print e
            self.settings = settings.Settings.create(".settings")
        
        # Build events
        self.Bind(build.EVT_BUILD_FINISHED, self.on_build_finished)
        self.Bind(build.EVT_BUILD_STARTED, self.on_build_started)
        self.Bind(build.EVT_BUILD_UPDATE, self.on_build_update)
        
        # GDB events 
        self.Bind(gdb.EVT_GDB_STARTED, self.on_gdb_started)
        self.Bind(gdb.EVT_GDB_FINISHED, self.on_gdb_finished)
        self.Bind(gdb.EVT_GDB_UPDATE, self.on_gdb_update)
        self.Bind(gdb.EVT_GDB_ERROR, self.on_gdb_error)
        self.Bind(gdb.EVT_GDB_STOPPED, self.on_gdb_stopped)
        self.Bind(gdb.EVT_GDB_RUNNING, self.on_gdb_running)
        
        # Views
        #   Build
        self.build_view = frame.build_view

        #   Memory
        self.memory_view = frame.memory_view
        self.memory_view.Bind(views.EVT_VIEW_REQUEST_UPDATE, self.on_update_memory_view)

        self.locals_view = frame.locals_view
        self.locals_view.Bind(views.EVT_VIEW_REQUEST_UPDATE, self.on_update_locals_view)
 
        #   Project
        self.project_view = frame.project_view
        self.project_view.Bind(views.EVT_PROJECT_DCLICK_FILE, self.on_project_dclick_file)

        #   Editor
        self.editor_view = frame.editor_view

        # Logs
        self.log_view = frame.log_view
        self.log_view.add_logger(logging.getLogger('stdout'))
        
        self.mi_logger = logging.getLogger('gdb.mi')
        self.log_view.add_logger(self.mi_logger)

        self.gdb_logger = logging.getLogger('gdb.stream')
        self.log_view.add_logger(self.gdb_logger, format="%(message)s")
       
        self.error_logger = logging.getLogger('errors')
        self.log_view.add_logger(self.error_logger)

        self.build_logger = logging.getLogger("Build")
        self.log_view.add_logger(self.build_logger, format="%(message)s")
        
        log.redirect_stdout('stdout')
      
        # Session
        self.load_session()
    
    def on_project_dclick_file(self, evt):
        self.frame.open_file(evt.data)

    def load_session(self):
        try:
            self.session = util.unpickle_file('.session')
            #self.frame.manager.LoadPerspective(self.session.perspective)
            #self.frame.manager.Update()
            if self.session.project_filename:
                print "trying to load project: %s" % self.session.project_filename
                try:
                    self.load_project(self.session.project_filename)
                except Exception,  e:
                    print e
        except Exception, e:
            print e
            self.session = project.Session()
    
    def save_session(self):
        #print self.session
        if self.session:
            #self.session.perspective = self.frame.manager.SavePerspective()
            if self.project:
                self.session.project_filename = self.project.filename
                print self.project.filename
            util.pickle_file(self.session, '.session')

    def new_project(self, path):
        if path:
            self.project = project.Project.create(path)
            self.project_view.set_project(self.project)
            menu.manager.publish(menu.PROJECT_OPEN)

    def load_project(self, path):
        self.project = project.Project.load(path)
        menu.manager.publish(menu.PROJECT_OPEN)
        self.project_view.set_project(self.project)
        self.session.project_filename = path
        print self.project

    def save_project(self):
        self.project.save()

    def open_file(self, path):
        self.frame.open_file(path)

    def update_settings(self):
        self.editor_view.update_settings()

    # IDE Functions, Building, Cleaning, Etc..
    def build(self):
        build_process = build.BuildProcess(self.project.build.build_cmd, notify=self, cwd=self.project.directory)
        build_process.start()
    
    def clean(self):
        build_process = build.BuildProcess(self.project.build.clean_cmd, notify=self, cwd=self.project.directory)
        build_process.start()

    def rebuild(self):
        build_process = build.BuildProcess(self.project.build.rebuild_cmd, notify=self, cwd=self.project.directory)
        build_process.start()

    # STATE MANAGEMENT
    # ==========================================================
    def enter_attached_state(self):
        #project = self.project
        menu.manager.publish(menu.TARGET_ATTACHED)
        #print "Entering the ATTACHED state."
        if self.state == IDLE:
            self.gdb.set_exec(self.project.absolute_path(self.project.debug.target))
        if self.state == IDLE or self.state == RUNNING:
            self.exit_current_state()
            self.frame.statusbar.icon = "connect.png"
            self.state = ATTACHED
        else:
            self.error_logger.log(logging.WARN, "Tried to attach from state %d" % self.state)

    def exit_attached_state(self):
        menu.manager.publish(menu.TARGET_ATTACHED)
        #print "Exiting the ATTACHED state."

    def enter_running_state(self):
        menu.manager.publish(menu.TARGET_RUNNING)
        #print "Entering the RUNNING state."
        if self.state == ATTACHED:
            self.exit_current_state()
            self.frame.statusbar.icon = "connect_green.png"
            self.state = RUNNING
        else:
            self.error_logger.log(logging.WARN, "Tried to run from state %d" % self.state)

    def exit_running_state(self):
        menu.manager.publish(menu.TARGET_HALTED)
        #print "Exiting the RUNNING state."

    def enter_idle_state(self):
        #print "Entering the IDLE state"
        self.exit_current_state()
        self.frame.statusbar.icon = "disconnect.png"
        self.state = IDLE

    def exit_idle_state(self):
        pass
        #print "Exiting the IDLE state"

    def exit_current_state(self):
        try:
            callable =  {ATTACHED   : self.exit_attached_state,
                         RUNNING    : self.exit_running_state,
                         IDLE       : self.exit_idle_state}[self.state]
            wx.CallAfter(callable)
        except Exception, e:
            print e
            pass

    def enter_state(self, state):
        try:
            callable =  {ATTACHED   : self.enter_attached_state,
                         RUNNING    : self.enter_running_state,
                         IDLE       : self.enter_idle_state}[state]
            wx.CallAfter(callable)
        except Exception, e:
            print e
            pass

    def change_state(self, state):    
        self.enter_state(state)

    # ==========================================================
    
   
    # STEP
    def step(self):
        if self.state == ATTACHED:
            self.gdb.exec_step()
    def step_out(self):
        if self.state == ATTACHED:
            self.gdb.exec_finish()
    # RUN
    def run(self):
        if self.state == IDLE:
            self.change_state(ATTACHED)
        elif self.state == RUNNING:
            return

        self.gdb.exec_continue(self.on_running)
            
    def on_running(self, result):
        if result.cls.lower() == "running":
            self.change_state(RUNNING)
        elif result.cls.lower() == "stopped":
            print result


    # HALT
    def halt(self):
        self.gdb.exec_interrupt(self.on_halted)
        
    def on_halted(self, result):
        if result.cls == "done" or result.cls == "stopped":
            self.change_state(ATTACHED)
            print result

    def download(self):
        if self.state == ATTACHED:
            self.gdb.target_download()

    # ATTACH TO GDB
    def attach(self):
        if self.state == IDLE:
            self.gdb = gdb.GDB(notify=self, mi_log=self.mi_logger, console_log=self.gdb_logger, target_log=self.gdb_logger, log_log=self.gdb_logger)
            self.gdb.command(self.project.debug.attach_cmd)
        else:
            print "Cannot attach to process from state %d" % self.state

    # DETACH FROM TARGET
    def detach(self):
        if self.gdb:
            self.gdb.quit()
        self.change_state(IDLE)
    
    # GDB EVENTS
    def on_gdb_started(self, evt):
        self.change_state(ATTACHED)
    
    def on_gdb_finished(self, evt):
        self.change_state(IDLE)

    def on_gdb_update(self, evt):
        pass
    
    def on_gdb_error(self, evt):
        self.error_logger.log(logging.ERROR, evt.data)

    def on_gdb_stopped(self, evt):
        self.change_state(ATTACHED)
        result = evt.data
        #print result.frame.fullname
        #print result.frame.line
        self.memory_view.request_update()
        self.locals_view.request_update()
        self.editor_view.set_exec_location(result.frame.fullname, int(result.frame.line))
        self.gdb.stack_list_locals()
        self.gdb.file_list_globals()

    def on_gdb_running(self, evt):
        self.change_state(RUNNING)

    # BUILD EVENTS
    def on_build_started(self, evt):
        self.state = BUILDING
        self.build_view.clear()
        self.build_view.update("Build Started.\n")

    def on_build_finished(self, evt):
        self.state = IDLE
        self.build_view.update("Build completed.\n")

    def on_build_update(self, evt):
        self.build_view.update(str(evt.data))

    # VIEW EVENTS
    def on_update_memory_view(self, evt):
        if self.state == ATTACHED:
            start, end = evt.data
            self.gdb.read_memory(start, self.memory_view.stride, end-start, callback=self.on_got_memory_data)
    def on_got_memory_data(self, result):
        if hasattr(result, 'memory'):
                memtable = []
                for entry in result.memory:
                    memtable.append(int(entry.data[0]))
                wx.CallAfter(self.memory_view.update, int(result.addr,16), memtable)

    def on_update_locals_view(self, evt):
        if self.state == ATTACHED:
            self.gdb.stack_list_locals(callback=self.on_got_locals_data)
    def on_got_locals_data(self, result):
        if hasattr(result, 'locals'):
            update_dict = {}
            for item in result.locals:
                update_dict[item.name] = item.value
            self.locals_view.update(update_dict)
