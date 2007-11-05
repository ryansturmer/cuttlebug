import wx
import os, threading, time, logging
import antlr3, GDBMILexer, GDBMIParser
import util, odict
from gdbvars import Type, Variable, GDBVarModel

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

EVT_GDB_UPDATE_BREAKPOINTS = wx.PyEventBinder(wx.NewEventType())

EVT_GDB_UPDATE_VARS = wx.PyEventBinder(wx.NewEventType())


#EVT_GDB_EXECUTE_UPDATE
#EVT_GDB_LOCALS_UPDATE
#EVT_GDB_MEMORY_UPDATE

EVT_GDB_RUNNING = wx.PyEventBinder(wx.NewEventType())
EVT_GDB_STOPPED = wx.PyEventBinder(wx.NewEventType())

class GDB(wx.EvtHandler):

    def __init__(self, cmd="arm-elf-gdb -n -q -i mi", mi_log=None, console_log=None, target_log=None, log_log=None):
        wx.EvtHandler.__init__(self)
        self.attached = False
        
        # Console streams
        self.mi_log = mi_log
        self.console_log = console_log
        self.target_log = target_log
        self.log_log = log_log

        # Parser for GDBMI commands
        self.cmd = cmd
        self.vars = GDBVarModel(self)
    def start(self):
        self.__clear()
        self.subprocess = util.Process(self.cmd, start=self.on_start, stdout=self.on_stdout, end=self.on_end)

    def __clear(self):
        self.buffer = ''
        self.pending = {} # Pending commands
        
        self.__varnames = {} # Variable names pending
        self.__varname_idx = 0
        
        self.token = 1    # Command token (increments on each command
        self.breakpoints = BreakpointTable(self)
        self.locals = []
        self.vars = GDBVarModel(self)
        self.__lexer = GDBMILexer.GDBMILexer(None)
        self.__parser = GDBMIParser.GDBMIParser(None)
        self.__deleted = []
        
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
        self.attached = True
        self.post_event(GDBEvent(EVT_GDB_STARTED, self))
    
    def on_end(self):
        self.attached = False
        self.post_event(GDBEvent(EVT_GDB_FINISHED, self))

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
                        callback, internal_callback = self.pending[result.token]
                        if callable(internal_callback):
                            internal_callback(result)
                        if callable(callback):
                            callback(result)
                        
                # Post an event on error
                if result.cls == 'error':
                    self.post_event(GDBEvent(EVT_GDB_ERROR, self, data=result.msg))
                elif result.cls == 'stopped':
                    self.post_event(GDBEvent(EVT_GDB_STOPPED, self, data=result))
                    self.__update_breakpoints()
                    self.stack_list_locals()
                    self.var_update()
                    
                elif result.cls == 'running':
                    self.post_event(GDBEvent(EVT_GDB_RUNNING, self, data=result))
                else:
                    self.post_event(GDBEvent(EVT_GDB_UPDATE, self, data=result))
        
    def __update_breakpoints(self, data=None):
        self.__cmd('-break-list\n', self.__process_breakpoint_update)
    def __process_breakpoint_update(self, data):
        if hasattr(data, 'BreakpointTable'):
            self.breakpoints.clear()
            for item in data.BreakpointTable.body:
                item = item.get('bkpt', None)
                if item:
                    number = int(item['number'])
                    address = int(item['addr'], 16)
                    fullname = item.get('fullname', '<Unknown File>')
                    enabled = True if (item['enabled'].upper() == 'Y' or item['enabled'] == '1') else False
                    line = int(item.get('line', -1))
                    bp = Breakpoint(number, fullname, line, enabled=enabled, address=address)
                    self.breakpoints[number] = bp
        wx.PostEvent(self, GDBEvent(EVT_GDB_UPDATE_BREAKPOINTS, self, data=self.breakpoints))
                        
    def post_event(self, evt):
        wx.PostEvent(self, evt)
    
    def __send(self, data):
        self.__mi_log(data)
        self.subprocess.stdin.write(data)

    def __cmd(self, cmd, callback=None, internal_callback=None):
        if cmd[-1] != '\n':
            cmd += '\n'
        if callback or internal_callback:
            self.__send(str(self.token) + cmd)
            self.pending[self.token] = (callback, internal_callback)
            self.token += 1
        else:
            self.__send(cmd)

    # Utility Stuff
    def command(self, cmd, callback=None):
        self.__cmd('-interpreter-exec console "%s"' % cmd, callback)
   
    def cmd(self, cmd, callback=None):
        self.__cmd(cmd, callback)
        
    def var_create(self, expression, floating=False, frame=None, callback=None):
        if floating:
            frame = "@"
        else:
            frame = "*" if frame == None else frame
        name = "cvar%d" % self.__varname_idx # We keep our own names so we can track expressions
        self.__varname_idx += 1
        self.__varnames[name] = expression
        self.__cmd('-var-create %s %s %s' % (name, frame, expression), callback=callback, internal_callback = self.__on_var_created)

    def __on_var_created(self, data):
        # Created variable info
        try:
            type = Type.parse(data.type)
            numchild = int(data.numchild)
            name = data.name
            expression = self.__varnames.pop(name)
            value = [] if numchild else data.value
        except Exception, e:
            print "Exception creating variable: %s" % e
            print data
        # Update the model and notify
        self.vars.add(name, Variable(name, expression, type, children=numchild, data=value))
        self.post_event(GDBEvent(EVT_GDB_UPDATE_VARS, self, data=[name]))
        
    def var_delete(self, name, callback=None):
        self.__deleted.append(name)
        self.vars.remove(name)
        self.__cmd('-var-delete %s' % name, callback, self.__on_var_deleted)
    def __on_var_deleted(self, data):
        var = self.__deleted.pop()
        self.post_event(GDBEvent(EVT_GDB_UPDATE_VARS, self, data=[var]))
                
    
    def var_update(self, name=None, callback=None):
        self.__cmd('-var-update --all-values %s' % (name or '*'), callback=callback, internal_callback = self.__on_var_updated)
    def __on_var_updated(self, data):
        print self.vars
        if hasattr(data,'changelist'):
            names = [item['name'] for item in data.changelist if item['in_scope'] != 'false']
            for item in data.changelist:
                if 'value' in item:
                    self.vars.vars[item['name']].data = item['value']
                if 'in_scope' in item:
                    if item['in_scope'] == 'false':
                        pass
                        #self.var_delete(item['name'])
        if names:
            self.post_event(GDBEvent(EVT_GDB_UPDATE_VARS, self, data=names))
    
    def var_list_children(self, name, callback=None):
        self.__cmd('-var-list-children --all-values %s' % name, internal_callback=self.__on_var_list_children, callback=callback)
    def __on_var_list_children(self, data):
        kids = []
        updated_kids =[]
        for item in data.children:
            child = item['child']
            numchild = int(child['numchild'])
            value = [] if numchild else child['value']
            type = Type.parse(child['type'])
            expression = child['exp']
            name = child['name']
            parent = GDBVarModel.parent_name(name)
            if name not in self.vars:
                self.vars.add(name, Variable(name, expression, type, children=numchild, data=value))
                updated_kids.append(name)
            kids.append(name)
        if parent:
            self.vars[parent].data = kids

        if updated_kids:
            self.post_event(GDBEvent(EVT_GDB_UPDATE_VARS, self, data=kids))
            
    def var_assign(self, name, value, callback=None):
        self.__cmd('-var-assign %s %s' % (name, value), internal_callback=self.__on_var_assign, callback=callback)
    def __on_var_assign(self, data):
        print data
        self.var_update()
        
    def stack_list_locals(self, callback=None):
        self.__cmd('-stack-list-locals 0', callback, internal_callback = self.__on_list_locals)

    def __on_list_locals(self, data):
        if hasattr(data, 'locals'):
            self.locals = []
            for entry in data.locals:                    
                self.locals.append(entry['name'])
        for expr in self.locals:
            try: 
                self.vars.name_from_expr(expr)
            except Exception, e: 
                print e
                self.var_create(expr)
        
    def file_list_globals(self, file='', callback=None):
        self.__cmd('-symbol-list-variables', callback)

    def exec_continue(self, callback=None):
        self.__cmd('-exec-continue\n', callback)

    def exec_step(self, callback=None):
        self.__cmd('-exec-step\n', callback)
   
    def exec_finish(self, callback=None):
        self.__cmd('-exec-finish\n', callback)
   
    def exec_until(self, file, line, callback=None):
        line = int(line)
        file = str(file)
        self.__cmd('-exec-until %s:%d\n' % (file, line), callable)

    def exec_interrupt(self, callable=None):
        self.__cmd('-exec-interrupt\n', callable)

    def target_download(self, callback=None):
        self.__cmd('-target-download\n', callback)

    def sig_interrupt(self):
        self.sigint()
        
    def quit(self):
        self.__cmd('-gdb-exit\n')
    
    def read_memory(self, start_addr, stride, count, callback=None):
        self.__cmd('-data-read-memory 0x%x u %d %d 1\n' % (start_addr, stride, count), callback)
        
    def break_list(self, callback=None):
        self.__cmd('-break-list\n', callback)

    def get_register_names(self):
        self.command('-data-list-register-names')
        
    def break_insert(self, file, line, hardware=False, temporary=False, callback=None):
        self.__cmd('-break-insert %s %s %s:%d' % ("-h" if hardware else "", "-t" if temporary else "", os.path.normpath(file), line), callback=callback, internal_callback=self.__update_breakpoints)
                
    def break_delete(self, num, callback=None):
        self.__cmd("-break-delete %d" % int(num), callback, internal_callback=self.__update_breakpoints)

    def break_disable(self, num, callback=None):
        self.__cmd("-break-disable %d" % int(num), callback, internal_callback=self.__update_breakpoints)

    def break_enable(self, num, callback=None):
        self.__cmd("-break-enable %d" % int(num), callback, internal_callback=self.__update_breakpoints)
        
    # Set Executable
    def set_exec(self, file):
        self.__cmd('-file-exec-and-symbols "%s"\n' % escape(file))


    def OnTerminate(self, *args, **kwargs):
        self.post_event(GDBEvent(EVT_GDB_FINISHED, self))



class BreakpointTable(object):
    def __init__(self, parent):
        self.__data = odict.OrderedDict()
        self.parent = parent
        
    def __setitem__(self, key, val):
        self.__data[int(key)] = val
        
    def __str__(self):
        return '\n'.join([str(self.__data[num]) for num in sorted(self.__data)])
        
    def clear(self):
        self.__data= odict.OrderedDict()
    
    def __iter__(self):
        return iter([self.__data[key] for key in sorted(self.__data.keys())])

    def remove(self, item):
        try:
            del self.__data[key]
        except:
            pass

    def get_number(self, file, line):
        for key, breakpoint in self.__data.iteritems():
            if breakpoint.line == line and breakpoint.fullname == file: return key
        raise KeyError
                    
class Breakpoint(object):
    
    def __init__(self, number, fullname, line, enabled=True, address=None):
        self.number = number
        self.line = line
        self.fullname = fullname
        self.enabled = enabled
        self.address = address
        
    def __str__(self):
        return "%s[%d]%s%d" % ('+' if self.enabled else ' ', self.number, self.fullname, self.line) 
        
