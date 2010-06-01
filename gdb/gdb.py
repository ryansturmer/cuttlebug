import wx
import os, threading, logging
import antlr3, GDBMILexer, GDBMIParser
import functools
from models import Type, Variable, GDBVarModel, GDBStackModel, GDBRegisterModel
import util, odict

STOPPED = 0
RUNNING = 1

HEXADECIMAL = 'x'
OCTAL = 'o'
BINARY = 't'
DECIMAL = 'd'
RAW = 'r'
NATURAL = 'n'

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
EVT_GDB_UPDATE_STACK = wx.PyEventBinder(wx.NewEventType())
EVT_GDB_UPDATE_REGISTERS = wx.PyEventBinder(wx.NewEventType())

EVT_GDB_RUNNING = wx.PyEventBinder(wx.NewEventType())
EVT_GDB_STOPPED = wx.PyEventBinder(wx.NewEventType())

class GDB(wx.EvtHandler):

    def __init__(self, cmd="arm-elf-gdb -n -q -i mi", mi_log=None, console_log=None, target_log=None, log_log=None):
        wx.EvtHandler.__init__(self)
        self.attached = False
        self.state = STOPPED
        
        # Console streams
        self.mi_log = mi_log
        self.console_log = console_log
        self.target_log = target_log
        self.log_log = log_log

        # Parser for GDBMI commands
        self.cmd_string = cmd
        
        self.__clear()
        
    def start(self):
        self.__clear()
        self.subprocess = util.Process(self.cmd_string, start=self.on_start, stdout=self.on_stdout, end=self.on_end)
        self.data_list_register_names()
        #self.cmd('-gdb-set target-async on')
        
    def __clear(self):
        self.buffer = ''
        self.pending = {} # Pending commands
        
        self.__varnames = {} # Variable names pending
        self.__varname_idx = 0
        
        self.token = 1    # Command token (increments on each command
        self.breakpoints = BreakpointTable(self)
        self.locals = []
        self.vars = GDBVarModel(self)
        self.stack = GDBStackModel(self)
        self.registers = GDBRegisterModel(self)
        self.__lexer = GDBMILexer.GDBMILexer(None)
        self.__parser = GDBMIParser.GDBMIParser(None)
        self.__deleted = []
       
    def update(self):
        self.__update_breakpoints()
        self.stack_list_frames()
        self.stack_list_locals()
        self.var_update()
        self.data_list_register_values()

    def parse(self, string):
        '''
        Parse a SINGLE gdb-mi response, returning a GDBMIResponse object
        '''
        stream = antlr3.ANTLRStringStream(unicode(string))
        self.__lexer.setCharStream(stream)
        tokens = antlr3.CommonTokenStream(self.__lexer)
        self.__parser.setTokenStream(tokens)
        output = self.__parser.output().response
        return output

    @property
    def running(self):
        return self.state == RUNNING
    
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
            response = self.parse(self.buffer)
            self.handle_response(response)
            self.buffer = ''
    
    def __on_running(self, record):
        self.state = RUNNING
        self.post_event(GDBEvent(EVT_GDB_RUNNING, self, data=record))
    
    def __on_stopped(self, record):
        self.state = STOPPED
        self.post_event(GDBEvent(EVT_GDB_STOPPED, self, data=record))
        self.update()
        
    def __on_error(self, command, record):
        # We make some corrections to the debugger state based on feedback from error messages
        if "while target is running" in record.msg: 
            self.__on_running(record)
        elif "while target is stopped" in record.msg or "not executing" in record.msg:
            self.__on_stopped(record)

        self.post_event(GDBEvent(EVT_GDB_ERROR, self, data=record.msg))
   
    
    def handle_response(self, response):
        # Deal with the console streams in the response
        for txt in response.console:
            self.__console_log(txt)
        for txt in response.target:
            self.__target_log(txt)
        for txt in response.log:
            self.__log_log(txt)

        results = (response.result, response.exc, response.status, response.notify)
        print results
        for result in results:
            command = ''
            if result != None: 
                if result.token:
                    # Call any function setup to be called as a result of this.... result.
                    if result.token in self.pending:
                        command, callback, internal_callback = self.pending[result.token]
                        if callable(internal_callback):
                            internal_callback(result)
                        if callable(callback):
                            callback(result)
                        
                # Post an event on error
                if result.cls == 'error':
                    self.__on_error(command, result)
                elif result.cls == 'stopped':
                    print "GOT A STOPPED RESPONSE"
                    self.__on_stopped(result)
                elif result.cls == 'running':
                    print "OK RUNNING NOW"
                    self.__on_running(result)
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
                    file = item.get('file', '<Unknown File>')
                    enabled = True if (item['enabled'].upper() == 'Y' or item['enabled'] == '1') else False
                    line = int(item.get('line', -1))
                    bp = Breakpoint(number, fullname, file, line, enabled=enabled, address=address)
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
            self.pending[self.token] = (cmd.strip(), callback, internal_callback)
            tok = self.token
            self.token += 1
            self.__send(str(tok) + cmd)
        else:
            self.__send(cmd)

    # Utility Stuff
    def command(self, cmd, callback=None):
        self.__cmd('-interpreter-exec console "%s"' % cmd, callback)
   
    def cmd(self, cmd, callback=None):
        self.__cmd(cmd, callback)
    
    def __clear_condition(self, condition, data):
        condition.acquire()
        condition.notify()
        condition.release()
        
    def __dummy(self, data): pass
        
    def __blocking_frameselect(self, frame):
        self.thing = False
        cv = threading.Condition(threading.RLock())
        try: frame = int(frame)
        except: frame = 0
        self.__cmd('-stack-select-frame %d' % int(frame), internal_callback = functools.partial(self.__clear_condition, cv), callback=self.__dummy)
        cv.acquire()
#        cv.wait() # TODO FIX THIS!
        cv.release()
        
    def stack_list_frames(self, callback=None):
        self.__cmd('-stack-list-frames', internal_callback=self.__on_stack_list_frames, callback=callback)
    def __on_stack_list_frames(self, data):
        if hasattr(data, 'stack'):
            self.stack.clear()
            frames = sorted([item['frame'] for item in data.stack], cmp=lambda x,y : cmp(int(x['level']), int(y['level'])))
            for frame in frames:
                level = int(frame['level'])
                addr = int(frame['addr'], 16)
                func = frame.get('func', '')
                fullname = frame.get('fullname', '')
                line = int(frame.get('line', -1))
                self.stack.add_frame(level, addr, func,  fullname, line)
            self.post_event(GDBEvent(EVT_GDB_UPDATE_STACK, self, data=self.stack))

    def var_create(self, expression, floating=False, frame=0, callback=None, name=None):
        if floating:
            frame = "@"

        if not floating:
            self.__blocking_frameselect(frame)
        if frame == 0:
            frame = "*"

        name = name or "cvar%d" % self.__varname_idx # We keep our own names so we can track expressions
        self.__varname_idx += 1
        self.__cmd('-var-create %s %s %s' % (name, frame, expression), callback=callback, internal_callback = functools.partial(self.__on_var_created, expression, frame))
        return name
    
    def __on_var_created(self, expression, frame, data):
        # Created variable info
        try:
            type = Type.parse(data.type)
            numchild = int(data.numchild)
            name = data.name
            value = [] if numchild else data.value
            # Update the model and notify
            self.vars.add(name, Variable(name, expression, type, children=numchild, data=value, frame=frame))
            self.post_event(GDBEvent(EVT_GDB_UPDATE_VARS, self, data=[name]))
        except Exception, e:
            print "Exception creating variable: %s" % e
            print data
        
    def var_delete(self, name, callback=None):
        self.__cmd('-var-delete %s' % name, callback, internal_callback=functools.partial(self.__on_var_deleted, name))
    def __on_var_deleted(self, name, data):
        self.vars.remove(name)
        self.post_event(GDBEvent(EVT_GDB_UPDATE_VARS, self, data=[name]))
                
    
    def var_update(self, name=None, callback=None):
        self.__cmd('-var-update --all-values %s' % (name or '*'), callback=callback, internal_callback = self.__on_var_updated)
    def __on_var_updated(self, data):
        if hasattr(data,'changelist'):
            names = [item['name'] for item in data.changelist]
            for item in data.changelist:
                if 'value' in item:
                    self.vars.vars[item['name']].data = item['value']
                if 'new_type' in item:
                    self.vars.vars[item['name']].type = Type.parse(item['new_type'])
                if 'new_num_children' in item:
                    self.vars.vars[item['name']].children = int(item['new_num_children'])                    
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
        self.var_update()
        
    def stack_list_locals(self, frame=0, callback=None):
        self.__cmd('-stack-select-frame %d' % frame, callback, internal_callback = functools.partial(self.__on_list_locals_fs, callback=callback))
    def __on_list_locals_fs(self, data, callback=None):
        self.__cmd('-stack-list-locals 0', callback=callback)

    def stack_list_arguments(self, frame=0, callback=None):
        self.__cmd('-stack-select-frame %d' % frame, callback, internal_callback = functools.partial(self.__on_list_arguments_fs, callback=callback))
    def __on_list_arguments_fs(self, data, callback=None):
        self.__cmd('-stack-list-arguments 0', callback=callback)
        
    def file_list_globals(self, file='', callback=None):
        self.__cmd('-symbol-list-variables', callback)

    def target_exec_status(self, callback=None):
        self.__cmd('-target-exec-status', callback, internal_callback=self.__on_exec_status)
        
    def __on_exec_status(self, data):
        return
        print data
        
    def data_disassemble(self, start_addr=None, end_addr=None, filename=None, linenum=None, lines=1, mode=0, callback=None):
        if filename:
            self.__cmd('-data-disassemble -f %s -l %s %s %d' % (filename, linenum, lines, mode), callback=callback)
        else:
            self.__cmd('-data-disassemble -s %s -e %s %d' % (start_addr, end_addr, mode), callback=callback)
            
    def exec_continue(self, callback=None):
        self.__cmd('-exec-continue\n', callback)
    def exec_step(self, callback=None):
        self.__cmd('-exec-step\n', callback)

    def exec_jump(self, address, callback=None):
        self.__cmd('-exec-jump %s\n' % address, callback)
   
    def exec_finish(self, callback=None):
        self.__blocking_frameselect(0)
        self.__cmd('-exec-finish\n', callback)
   
    def exec_until(self, file, line, callback=None):
        line = int(line)
        file = str(file)
        self.__cmd('-exec-until %s:%d\n' % (file, line), callable)

    def exec_interrupt(self, callable=None):
        self.__cmd('-exec-interrupt\n', callable)
    halt = exec_interrupt

    def exec_next_instruction(self, callable=None):
        self.__cmd('-exec-next-instruction\n', callable)

    def exec_step_instruction(self, callable=None):
        self.__cmd('-exec-step-instruction\n', callable)
        
    def target_download(self, callback=None):
        self.__cmd('-target-download\n', callback)

    def sig_interrupt(self):
        self.sigint()
        
    def quit(self):
        self.__cmd('-gdb-exit\n', internal_callback=self.__on_quit)
    def __on_quit(self, data):
        self.subprocess.terminate()
        
    
    def read_memory(self, start_addr, stride, count, callback=None):
        self.__cmd('-data-read-memory 0x%x u %d %d 1\n' % (start_addr, stride, count), callback)
        
    def break_list(self, callback=None):
        self.__cmd('-break-list\n', callback)

    def data_list_register_names(self, callback=None):
        self.__cmd('-data-list-register-names', internal_callback=self.__on_list_register_names, callback=callback)        
    def __on_list_register_names(self, data):
        if 'register-names' in data:
            self.registers.set_names(data['register-names'])

    def data_list_register_values(self, callback=None):
        self.__cmd('-data-list-register-values r', internal_callback=self.__on_list_register_values, callback=callback)        
    def __on_list_register_values(self, data):
        if 'register-values' in data:
            changed = []
            for d in data['register-values']:
                n = int(d['number'])
                new_value = d['value']
                old_value = self.registers.get_value_from_number(n)
                self.registers.set_value_from_number(n,new_value)
                if new_value != old_value:
                    changed.append(self.registers.get_name_from_number(n))
            
            self.post_event(GDBEvent(EVT_GDB_UPDATE_REGISTERS, self, data=changed))

    def data_evaluate_expression(self, expression, callback):
        self.__cmd('-data-evaluate-expression "%s"' % expression, callback=callback)
        
    def break_insert(self, file, line, hardware=False, temporary=False, callback=None):
        self.__cmd('-break-insert %s %s %s:%d' % ("-h" if hardware else "", "-t" if temporary else "", os.path.normpath(file), line), callback=callback, internal_callback=self.__update_breakpoints)
                
    def break_delete(self, num, callback=None):
        if isinstance(num, Breakpoint):
            num = num.number
        self.__cmd("-break-delete %d" % int(num), callback, internal_callback=self.__update_breakpoints)

    def break_disable(self, num, callback=None):
        if isinstance(num, Breakpoint):
            num = num.number
        self.__cmd("-break-disable %d" % int(num), callback, internal_callback=self.__update_breakpoints)

    def break_enable(self, num, callback=None):
        if isinstance(num, Breakpoint):
            num = num.number
        self.__cmd("-break-enable %d" % int(num), callback, internal_callback=self.__update_breakpoints)
                
    def set(self, name, val, callback=None):
        self.__cmd("-gdb-set %s=%s" % (name, val), callback)
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

    def remove(self, key):
        try:
            del self.__data[key]
        except:
            pass

    def get_number(self, file, line):
        for key, breakpoint in self.__data.iteritems():
            if breakpoint.line == line and (breakpoint.fullname == file or breakpoint.file == file): return key
        raise KeyError
                    
class Breakpoint(object):
    
    def __init__(self, number, fullname, file, line, enabled=True, address=None):
        self.number = number
        self.line = line
        self.fullname = fullname
        self.file = file
        self.enabled = enabled
        self.address = address
        
    def __str__(self):
        return "<Breakpoint %s[%d]%s%d>" % ('+' if self.enabled else ' ', self.number, self.fullname, self.line) 
        
if __name__ == "__main__":
    
    session = GDB()
    result = session.parse('*stopped,frame={addr="0x08000252",func="Delay",args=[{name="nCount",value="275526"}],file="main.c",fullname="C:\\Documents and Settings\\Cuttlebug Developer\\My Documents\\projects\\example_projects\\stm32f103\\blink_led/main.c",line="81"},thread-id="1",stopped-threads="all"')
    print result.exc
    print result
    
    result = session.parse('1^done,register-names=["r0","r1","r2","r3","r4","r5","r6","r7","r8","r9","r10","r11","r12","sp","lr","pc","f0","f1","f2","f3","f4","f5","f6","f7","fps","cpsr","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","",""]')
    print result