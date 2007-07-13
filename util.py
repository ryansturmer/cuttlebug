import wx
import os, threading, subprocess

from os.path import abspath, dirname, normcase, normpath, splitdrive
from os.path import join as path_join, commonprefix

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
            print e
import proc

class Process(proc.Popen):

    def __init__(self, cmd, start=None, stdout=None, stderr=None, end=None):
        self.start = start
        self.end = end
        self.stdout = stdout
        self.stderr = stderr
        self.done = False
        super(proc.Popen, self).__init__(cmd, shell=True, stdout=proc.PIPE, stderr=proc.PIPE, stdin=proc.PIPE)
        if start:
            start()
        
        self.outworker = ThreadWorker(self.__monitor, self.recv)
        self.errworker = ThreadWorker(self.__monitor, self.recv_err)
        self.doneworker = ThreadWorker(self.__watch_for_done)
        
        self.outworker.start()
        self.errworker.start()
        self.doneworker.start()
    
    def write(self, data):
        self.send(data)

    def __monitor(self, f, g):
        buffer = ''
        while True:
            ch = f(1)
            buffer += ch
            if ch == '\n':
                buffer += ch
                if g:
                    g(buffer)
                buffer = ''

    def __watch_for_done(self):
        self.wait()
        self.done = True
        if self.end:
            self.end()

if __name__ == "__main__":
    import os
    import recipe
    import subprocess
    def prn(s):
        print s

    p = Process("python -u subprocess_test.py")

    while True: pass
