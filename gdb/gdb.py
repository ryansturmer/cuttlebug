import wx
import os, threading, time, logging
import antlr3, GDBMILexer, GDBMIParser

class GDBEvent(wx.PyEvent):
    def __init__(self, type, object=None, data=None):
        super(GDBEvent, self).__init__()
        self.SetEventType(type.typeId)
        self.SetEventObject(object)
        self.data = data


EVT_GDB_STARTED = wx.PyEventBinder(wx.NewEventType())
EVT_GDB_FINISHED = wx.PyEventBinder(wx.NewEventType())

EVT_GDB_ERROR = wx.PyEventBinder(wx.NewEventType())
EVT_GDB_UPDATE = wx.PyEventBinder(wx.NewEventType())

EVT_GDB_RUNNING = wx.PyEventBinder(wx.NewEventType())
EVT_GDB_STOPPED = wx.PyEventBinder(wx.NewEventType())

class GDB(wx.Process, threading.Thread):

    def __init__(self, cmd="gdb -n -q -i mi", notify=None, polling_interval=100, mi_log=None, console_log=None, target_log=None, log_log=None):
        wx.Process.__init__(self, notify)
        threading.Thread.__init__(self)
        
        self.pending = {}
        self.token = 1

        # Console streams
        self.mi_log = mi_log
        self.console_log = console_log
        self.target_log = target_log
        self.log_log = log_log

        # Parser for GDBMI commands
        self.__lexer = GDBMILexer.GDBMILexer(None)
        self.__parser = GDBMIParser.GDBMIParser(None)
        self.Redirect()
        self.notify = notify
        self.cmd = cmd
        self.pid = None
        self.start_process()

    def __parse(self, string):
        '''
        Parse a SINGLE gdb-mi response, returning a GDBMIResponse object
        '''
        stream = antlr3.ANTLRStringStream(unicode(string))
        self.__lexer.setCharStream(stream)
        tokens = antlr3.CommonTokenStream(self.__lexer)
        self.__parser.setTokenStream(tokens)
        output = self.__parser.output().response
        return output

    def __console_log(self, txt):
        if self.console_log:
            self.console_log.log(logging.INFO,txt )

    def __target_log(self, txt):
        if self.target_log:
            self.target_log.log(logging.INFO, txt)
    
    def __log_log(self, txt):
        if self.log_log:
            self.log_log.log(logging.INFO, txt )
   
    def __mi_log(self, txt):
        if self.mi_log:
            self.mi_log.log(logging.INFO, txt)

    def run(self):
        input = self.GetInputStream()
        buffer = ''
        while(self.Exists(self.pid)):
            if input.CanRead():
                line = input.readline()
                self.__mi_log(line)
                buffer += line
                if line.strip() == '(gdb)':
                    response = self.__parse(buffer)
                    self.handle_response(response)
                    buffer = ''
            else:
                time.sleep(0.01)
                continue

    def handle_response(self, response):
        # Deal with the console streams in the response
        for txt in response.console:
            self.__console_log(txt)
        for txt in response.target:
            self.__target_log(txt)
        for txt in response.log:
            self.__log_log(txt)

        results = (response.result, response.exc, response.status, response.notify)
        for result in results:
            if result != None: 
                if result.token:
                    # Call any function setup to be called as a result of this.... result.
                    if result.token in self.pending:
                        callable, args, kwargs = self.pending[result.token]
                        callable(result, *args, **kwargs)
                        
                # Post an event on error
                if result.cls == 'error':
                    self.post_event(GDBEvent(EVT_GDB_ERROR, self, data=result.msg))
                elif result.cls == 'stopped':
                    self.post_event(GDBEvent(EVT_GDB_STOPPED, self, data=result))
                else:
                    self.post_event(GDBEvent(EVT_GDB_UPDATE, self, data=result))

    def post_event(self, evt):
        if self.notify:
            wx.PostEvent(self.notify, evt)
    
    def start_process(self):
        self.pid = wx.Execute(self.cmd, wx.EXEC_ASYNC, self)
        self.post_event(GDBEvent(EVT_GDB_STARTED, self))
        self.start()
    
    def __send(self, data):
        self.__mi_log(data)
        stream = self.GetOutputStream()
        stream.write(data)

    def __cmd(self, cmd, callback=None, *args, **kwargs):
        if cmd[-1] != '\n':
            cmd += '\n'
        if callback:
            self.__send(str(self.token) + cmd)
            self.pending[self.token] = (callback, args, kwargs)
            self.token += 1
        else:
            self.__send(cmd)

    # Utility Stuff
    def command(self, cmd):
        self.__cmd(cmd)
    
    def exec_continue(self, callback=None, *args, **kwargs):
        self.__cmd('-exec-continue\n', callback, *args, **kwargs)

    def exec_step(self, callback=None, *args, **kwargs):
        self.__cmd('-exec-step\n', callback, *args, **kwargs)
    
    def exec_interrupt(self, callable=None, *args, **kwargs):
        self.__cmd('-exec-interrupt\n', callable, *args, **kwargs)

    def sig_interrupt(self):
        self.__cmd('\x03\n')

    def quit(self):
        self.__cmd('-gdb-exit\n')
    
    def read_memory(self, start_addr, stride, count, callback=None, *args, **kwargs):
        self.__cmd('-data-read-memory 0x%x u %d %d 1' % (start_addr, stride, count), callback, *args, **kwargs)
        

    def get_register_names(self):
        self.command('-data-list-register-names')
        
    # Set Executable
    def set_exec(self, file):
        file = os.path.abspath(file)
        self.__cmd('-file-exec-and-symbols %s\n' % file)


    def OnTerminate(self, *args, **kwargs):
        self.post_event(GDBEvent(EVT_GDB_FINISHED, self))
