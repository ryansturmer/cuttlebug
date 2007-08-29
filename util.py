import wx
import os, threading, subprocess, pickle

from os.path import abspath, dirname, normcase, normpath, splitdrive
from os.path import join as path_join, commonprefix
class FontEnumerator(wx.FontEnumerator):
    def __init__(self):
        super(FontEnumerator, self).__init__()
        self.fonts = []
        self.EnumerateFacenames(fixedWidthOnly=True)
    def OnFacename(self, name):
        self.fonts.append(name)
        return True
        
def get_fonts():
    fonts = FontEnumerator().fonts
    fonts.sort()
    return fonts
    
def get_font():
    preferred_fonts = [
        'Bitstream Vera Sans Mono',
        'Courier New',
        'Courier',
    ]
    fonts = get_fonts()
    for font in preferred_fonts:
        if font in fonts:
            return font
    return fonts[0] if fonts else None
def menu_item(window, menu, label, func, icon=None, kind=wx.ITEM_NORMAL, toolbar=None, registries=None, enabled=True):
    item = wx.MenuItem(menu, -1, label, kind=kind)
    if func:
        window.Bind(wx.EVT_MENU, func, id=item.GetId())
    if icon:
        item.SetBitmap(get_icon(icon))
        item.SetDisabledBitmap(get_icon('blank.png'))
    menu.AppendItem(item)
    if toolbar and icon:
        tool_item = toolbar.AddSimpleTool(-1, get_icon(icon), label)
        if func:
            window.Bind(wx.EVT_TOOL, func, id=tool_item.GetId())
    if registries != None:
        for registry in registries:
            if item not in registry:
                registry.append(item)
    item.Enable(bool(enabled))
    return item
    
def tool_item(window, toolbar, label, func, icon):
    item = toolbar.AddSimpleTool(-1, get_icon(icon), label)
    if func:
        window.Bind(wx.EVT_TOOL, func, id=item.GetId())
    return item

def button(window, label, func=None, icon=None):
    #if icon and isinstance(icon, str):
    #    button = wx.BitmapButton(window, -1, bitmap=get_icon(icon), label=text, style=wx.BU_LEFT)
    #else:
    button = wx.Button(window, -1, label)
    if func:
        button.Bind(wx.EVT_BUTTON, func)
    return button

def padded(window, padding, sides=wx.ALL):
    sizer = wx.BoxSizer(wx.VERTICAL)
    sizer.Add(window, 1, wx.EXPAND|sides, padding)
    return sizer

def get_icon(file):
    file = 'icons/%s' % file
    return wx.Bitmap(file)

# Taken from http://code.activestate.com/recipes/302594/

def commonpath(a, b):
    """Returns the longest common to 'paths' path.

    Unlike the strange commonprefix:
    - this returns valid path
    - accepts only two arguments
    """
    a = normpath(normcase(a))
    b = normpath(normcase(b))

    if a == b:
        return a

    while len(a) > 0:
        if a == b:
            return a

        if len(a) > len(b):
            a = dirname(a)
        else:
            b = dirname(b)

    return None

def relpath(target, base_path):
    """
    Return a relative path to the target from either the current directory
    or an optional base directory.

    Base can be a directory specified either as absolute or relative
    to current directory.
    """

    base_path = normcase(abspath(normpath(base_path)))
    target = normcase(abspath(normpath(target)))

    if base_path == target:
        return '.'

    # On the windows platform the target may be on a different drive.
    if splitdrive(base_path)[0] != splitdrive(target)[0]:
        return None

    common_path_len = len(commonpath(base_path, target))

    # If there's no common prefix decrease common_path_len should be less by 1
    base_drv, base_dir = splitdrive(base_path)
    if common_path_len == len(base_drv) + 1:
        common_path_len -= 1

    # if base_path is root directory - no directories up
    if base_dir == os.sep:
        dirs_up = 0
    else:
        dirs_up = base_path[common_path_len:].count(os.sep)

    ret = os.sep.join([os.pardir] * dirs_up)
    if len(target) > common_path_len:
        ret = path_join(ret, target[common_path_len + 1:])

    return ret

class ThreadWorker(threading.Thread):
    def __init__(self, callable, *args, **kwargs):
        super(ThreadWorker, self).__init__()
        self.callable = callable
        self.args = args
        self.kwargs = kwargs
        self.setDaemon(True)

    def run(self):
        try:
            self.callable(*self.args, **self.kwargs)
        except wx.PyDeadObjectError:
            pass
        except Exception, e:
            #print "omg exception"
            #print e
            raise
'''
import proc

class Process(proc.Popen):

    def __init__(self, cmd, start=None, stdout=None, stderr=None, end=None):
        self.start = start
        self.end = end
        self.stdout_func = stdout
        self.stderr_func = stderr
        self.done = False
        super(Process, self).__init__(cmd, shell=True, stdout=proc.PIPE, stderr=proc.PIPE, stdin=proc.PIPE)
        if start:
            start()
        
        self.outworker = ThreadWorker(self.__monitor, self.recv, self.stdout_func)
        self.errworker = ThreadWorker(self.__monitor, self.recv_err, self.stderr_func)
        #self.doneworker = ThreadWorker(self.__watch_for_done)
        
        self.outworker.start()
        self.errworker.start()
        #self.doneworker.start()
    
    def write(self, data):
        self.send(data)

    def __monitor(self, f, g):
        buffer = ''
        while True:
            ch = f(1)
            if buffer:
                buffer += ch
                print buffer
            if ch == '\n':
                if g:
                    g(buffer)
                buffer = ''

    def __watch_for_done(self):
        self.wait()
        self.done = True
        if self.end:
            self.end()
'''
class Process(subprocess.Popen):
    def __init__(self, cmd, start=None, stdout=None, stderr=None, end=None, cwd=os.curdir):
        self.start = start
        self.stdout_func = stdout
        self.stderr_func = stderr
        self.end = end
        self.done = False
        super(Process, self).__init__(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE, cwd=cwd)
        if start:
            self.start()

        self.stdoutworker = ThreadWorker(self.monitor_stream, self.stdout_func, self.stdout)
        self.stderrworker = ThreadWorker(self.monitor_stream, self.stderr_func, self.stderr)

        self.stdoutworker.start()        
        self.stderrworker.start()

    def monitor_stream(self, func, stream):
        while True:
            data = stream.readline()
            if data:
                if func:
                    func(data)
            else:
                self.done = True
                break
        if self.end:
            self.end()

class Category(object):

    def __init__(self, name='', parent=None):
        # TODO ordered dict later?
        self.items = dict()
        self.name = str(name)
        #self.parent = parent
        self.__modified = False
        self.modified = False
    '''
    def __get_modified(self):
        return self.__modified

    def __set_modified(self, x):
        self.__modified = bool(x)
        if self.modified and self.parent:
            self.parent.modified = True
    modified = property(__get_modified, __set_modified)
    '''
    def __setstate__(self, data):
      self.__dict__.update(data)

    def reset(self):
        self.modified = False
    
    #def __getstate__(self):
    #    return self.__dict__

    def __getattr__(self, attr):
        try:
            return self.items[str(attr)]
        except KeyError:
            raise AttributeError
    
    #def __setattr__(self, attr, val):
    #    self.items[str(attr)] = val
    
    def __getitem__(self, idx):
        names = idx.split(".")
        if len(names) == 1:
            return self.items[idx]
        else:
            next = self.items[names[0]]
            return next[".".join(names[1:])]

    def __setitem__(self, idx, val):
        names = idx.split(".")
        if len(names) == 1:
            self.items[idx] = val
            self.modified = True
        else:
            next = self.items[names[0]]
            next[".".join(names[1:])] = val

    def add_category(self, name):
        if name in self:
            raise ProjectError("Already a category called '%s'" % name)
        self[name] = Category(name)
        self.modified = True

    def __iter__(self):
        return iter(self.items)

    def __str__(self):
        return str(self.items)
    def __repr__(self):
        return str(self)

def pickle_file(object, filename):
        try:
            del(object.filename)
        except:
            pass
        
        fp = open(os.path.abspath(filename),'wb')
        pickle.dump(object, fp, -1)
        fp.close()

def unpickle_file(filename):
    path = os.path.abspath(filename)
    fp = open(path, 'r')
    object = pickle.load(fp)
    fp.close()
    object.filename = path
    return object


if __name__ == "__main__":
    import os
    import recipe
    import subprocess
    def prn(s):
        print s

    p = Process("python -u subprocess_test.py")

    while True: pass


