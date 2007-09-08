import wx
import os, threading, time, logging
import antlr3, GDBMILexer, GDBMIParser
import util

def escape(s):
    return s.replace("\\", "\\\\")

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

class GDB(util.Process):

    def __init__(self, cmd="arm-elf-gdb -n -q -i mi", notify=None, mi_log=None, console_log=None, target_log=None, log_log=None):

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
        self.notify = notify
        self.cmd = cmd
        self.pid = None
        self.buffer = ''
        util.Process.__init__(self, cmd, start=self.on_start, stdout=self.on_stdout, end=self.on_end)

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

    def on_start(self):
        self.post_event(GDBEvent(EVT_GDB_STARTED, self.notify))
    
    def on_end(self):
        self.post_event(GDBEvent(EVT_GDB_FINISHED, self.notify))

    def on_stdout(self, line):
        self.__mi_log(line)
        self.buffer += line
        if line.strip() == '(gdb)':
            response = self.__parse(self.buffer)
            self.handle_response(response)
            self.buffer = ''

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
                    self.post_event(GDBEvent(EVT_GDB_ERROR, self.notify, data=result.msg))
                elif result.cls == 'stopped':
                    self.post_event(GDBEvent(EVT_GDB_STOPPED, self.notify, data=result))
                elif result.cls == 'running':
                    self.post_event(GDBEvent(EVT_GDB_RUNNING, self.notify, data=result))
                else:
                    self.post_event(GDBEvent(EVT_GDB_UPDATE, self.notify, data=result))

    def post_event(self, evt):
        if self.notify:
            wx.PostEvent(self.notify, evt)
    
    def __send(self, data):
        self.__mi_log(data)
        self.stdin.write(data)

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
    def command(self, cmd, callback=None, *args, **kwargs):
        self.__cmd('-interpreter-exec console "%s"' % cmd, callback, *args, **kwargs)
   
    def stack_list_locals(self, callback=None, *args, **kwargs):
        self.__cmd('-stack-list-locals 1', callback, *args, **kwargs)

    def file_list_globals(self, file='', callback=None, *args, **kwargs):
        self.__cmd('-symbol-list-variables', callback, *args, **kwargs)

    def exec_continue(self, callback=None, *args, **kwargs):
        self.__cmd('-exec-continue\n', callback, *args, **kwargs)

    def exec_step(self, callback=None, *args, **kwargs):
        self.__cmd('-exec-step\n', callback, *args, **kwargs)
   
    def exec_finish(self, callback=None, *args, **kwargs):
        self.__cmd('-exec-finish\n', callback, *args, **kwargs)
   
    def exec_until(self, file, line, callback=None, *args, **kwargs):
        line = int(line)
        file = str(file)
        self.__cmd('-exec-until %s:%d\n' % (file, line), callable, *args, **kwargs)

    def exec_interrupt(self, callable=None, *args, **kwargs):
        self.__cmd('-exec-interrupt\n', callable, *args, **kwargs)

    def target_download(self, callback=None, *args, **kwargs):
        self.__cmd('-target-download\n', callback, *args, **kwargs)

    def sig_interrupt(self):
        self.sigint()
        
    def quit(self):
        self.__cmd('-gdb-exit\n')
    
    def read_memory(self, start_addr, stride, count, callback=None, *args, **kwargs):
        self.__cmd('-data-read-memory 0x%x u %d %d 1\n' % (start_addr, stride, count), callback, *args, **kwargs)
        
    def break_list(self, callback=None, *args, **kwargs):
        self.__cmd('-break-list\n', callback, *args, **kwargs)

    def get_register_names(self):
        self.command('-data-list-register-names')
        
    def break_insert(self, file, line, hardware=False, temporary=False,  callback=None, *args, **kwargs):
        self.__cmd('-break-insert %s %s %s:%d' % ("-h" if hardware else "", "-t" if temporary else "", os.path.normpath(file), line), callback, *args, **kwargs)
        
    def break_delete(self, num, callback=None, *args, **kwargs):
        self.__cmd("-break-delete %d" % int(num), callback, *args, **kwargs)
    # Set Executable
    def set_exec(self, file):
        self.__cmd('-file-exec-and-symbols "%s"\n' % escape(file))


    def OnTerminate(self, *args, **kwargs):
        self.post_event(GDBEvent(EVT_GDB_FINISHED, self.notify))
