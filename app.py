import build, views, prefs, gdb, project, log
import logging
import wx
IDLE = 0
BUILDING = 1
ATTACHED = 2
CONNECTED = 3
RUNNING = 4

class Controller(wx.EvtHandler):

    def __init__(self, frame=None):
        super(Controller, self).__init__()
        self.state = IDLE
        self.gdb = None
        self.frame = frame
        
        # Build events
        self.Bind(build.EVT_BUILD_FINISHED, self.on_build_finished)
        self.Bind(build.EVT_BUILD_STARTED, self.on_build_started)
        self.Bind(build.EVT_BUILD_UPDATE, self.on_build_update)
        
        # GDB events 
        self.Bind(gdb.EVT_GDB_STARTED, self.on_gdb_started)
        self.Bind(gdb.EVT_GDB_FINISHED, self.on_gdb_finished)
        self.Bind(gdb.EVT_GDB_UPDATE, self.on_gdb_update)
        self.Bind(gdb.EVT_GDB_ERROR, self.on_gdb_error)
        
        # Views
        #   Build
        self.build_view = frame.build_view

        #   Memory
        self.memory_view = frame.memory_view
        self.memory_view.Bind(views.EVT_VIEW_REQUEST_UPDATE, self.on_update_memory_view)

        #   Logs
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
        self.load_session()
        
        # View Events

    def load_session(self):
        try:
            self.session = project.load('.session')
            self.frame.manager.LoadPerspective(self.session.perspective)
            self.frame.manager.Update()
        except Exception, e:
            print e
            self.session = project.Session()
    
    def save_session(self):
        print self.session
        if self.session:
            self.session.perspective = self.frame.manager.SavePerspective()
            project.save(self.session, '.session')
   
    # IDE Functions, Building, Cleaning, Etc..
    def build(self):
        build_process = build.BuildProcess(prefs.BUILD_COMMAND, notify=self)
        build_process.start()
    
    def clean(self):
        build_process = build.BuildProcess(prefs.CLEAN_COMMAND, notify=self)
        build_process.start()

    def rebuild(self):
        print "Controller is REBUILDing"

    # STATE MANAGEMENT
    def enter_attached_state(self):
        print "Entering the ATTACHED state."
        if self.state == IDLE or self.state == RUNNING:
            self.exit_current_state()
            self.frame.statusbar.icon = "connect.png"
            self.state = ATTACHED
        else:
            self.error_logger.log(logging.WARN, "Tried to attach from state %d" % self.state)

    def exit_attached_state(self):
        print "Exiting the ATTACHED state."

    def enter_running_state(self):
        print "Entering the RUNNING state."
        if self.state == ATTACHED:
            self.exit_current_state()
            self.frame.statusbar.icon = "connect_green.png"
            self.state = RUNNING
        else:
            self.error_logger.log(logging.WARN, "Tried to run from state %d" % self.state)

    def exit_running_state(self):
        print "Exiting the RUNNING state."

    def enter_idle_state(self):
        print "Entering the IDLE state"
        self.exit_current_state()
        self.frame.statusbar.icon = "disconnect.png"
        self.state = IDLE

    def exit_idle_state(self):
        print "Exiting the IDLE state"

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

    # RUN
    def run(self):
        if self.state == ATTACHED:
            self.gdb.exec_continue(self.on_running)
            
    def on_running(self, result):
        if result.cls.lower() == "running":
            self.change_state(RUNNING)


    # HALT
    def halt(self):
        self.gdb.exec_interrupt(self.on_halted)

    def on_halted(self, result):
        if result.cls == "done" or result.cls == "stopped":
            self.change_state(ATTACHED)

    # ATTACH TO GDB
    def attach(self):
        if self.state == IDLE:
            self.gdb = gdb.GDB(cmd=prefs.GDB, notify=self, mi_log=self.mi_logger, console_log=self.gdb_logger, target_log=self.gdb_logger, log_log=self.gdb_logger)
            self.gdb.command(prefs.ATTACH_COMMAND)
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
            print evt
            self.gdb.read_memory(start, self.memory_view.stride, end-start, callback=self.on_got_memory_data)

    def on_got_memory_data(self, result):
        if hasattr(result, 'memory'):
                memtable = []
                for entry in result.memory:
                    print entry
                    memtable.append(int(entry.data[0]))

                wx.CallAfter(self.memory_view.update, int(result.addr,16), memtable)
