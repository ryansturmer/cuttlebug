import wx
import odict
import util

# APPLICATION SPECIFIC
# pub/sub topics
PROJECT_OPEN = 1
PROJECT_CLOSE = 2

TARGET_ATTACHED = 3
TARGET_DETACHED = 4

TARGET_RUNNING = 5
TARGET_HALTED = 6

BUILD_STARTED = 7
BUILD_FINISHED = 8

class MenuItemProxy(object):

    def __init__(self, parent, label='', func=None, icon=None, kind=wx.ITEM_NORMAL, separator=False):
        self.parent = parent
        
        self._label = label
        self._func = func
        self.is_separator = bool(separator)
        self.kind = kind
        self.visible = True
        self.enabled = True
        self.icon = icon

    def __str__(self):
        return "<MenuItemProxy '%s'>" % self.label
    def __repr__(self):
        return str(self)
    def __get_icon(self):
        return self._icon
    def __set_icon(self, icon):
        if self.is_separator:
            return

        if isinstance(icon, str):
            self._icon = util.get_icon(icon)
        else:
            self._icon = icon
        self.update()

    icon = property(__get_icon, __set_icon)

    def __get_label(self):
        return self._label

    def __set_label(self, lbl):
        self._label = str(lbl)
        self.update()
    label = property(__get_label, __set_label)

    def show(self):
        self.visible = True
        self.update()

    def hide(self):
        self.visible = False
        self.update()

    def enable(self):
        self.enabled = True
        self.update()

    def disable(self):
        self.enabled = False
        self.update()

    def build(self, menu, window):
        if self.is_separator:
            return wx.MenuItem(menu, id=wx.ID_SEPARATOR)
        else:
            menuitem = wx.MenuItem(menu, id=-1, text=self._label, kind=self.kind)
            if self._icon:    
                menuitem.SetBitmap(self._icon)
                menuitem.SetDisabledBitmap(util.get_icon('blank.png'))
            
            if self._func and window:
                window.Bind(wx.EVT_MENU, self._func, id=menuitem.GetId())

            return menuitem
    
    def update(self):
        self.parent.update()
        
class MenuProxy(object):
    def __init__(self, manager, parent, label):
        self.manager = manager
        self.parent = parent
        self.label = label
        self.visible = True
        self.enabled = True
        self.is_separator = False
        self._items = []

    @property
    def is_submenu(self):
        if self.parent and isinstance(self.parent, MenuProxy):
            return True
        return False

    @property
    def is_popup_menu(self):
        return not self.parent
     
    def __repr__(self):
        return "<MenuProxy '%s'>" % self.label
    def __str__(self):
        return repr(self)
    def __iter__(self):
        return iter(self._items)

    def build(self, window=None):

        #items = []
        retval = wx.Menu()
        
        # Trim out everything that's invisible
        visible_items = [item for item in self._items if item.visible]

        trimmed_items = []
        if visible_items:
            for i in range(len(visible_items)-1):
                item = visible_items[i]
                next_item = visible_items[i+1]
                if not (item.is_separator and next_item.is_separator):
                    trimmed_items.append(item)
            trimmed_items.append(visible_items[-1])

        if trimmed_items:
            while trimmed_items[-1].is_separator:
                trimmed_items.pop(-1)
        
        for item in trimmed_items:
            #   menuitem = item.build(retval, window)
            if isinstance(item, MenuItemProxy):    
                menuitem = item.build(retval, window)
                retval.AppendItem(menuitem)
                if item.enabled:
                    menuitem.Enable()
                else:
                    menuitem.Enable(False)            
            elif isinstance(item, MenuProxy):
                menuitem = item.build(window)                
                retval.AppendMenu(wx.ID_ANY, item.label, menuitem)
        return retval
    
    def item(self, label, func=None, icon=None, kind=wx.ITEM_NORMAL, disable=None, enable=None, show=None, hide=None):
        item = MenuItemProxy(self, label=label, func=func, icon=icon, kind=kind)
        self.manager.subscribe(item, enable=enable, disable=disable, show=show, hide=hide)
        self._items.append(item)
        self.update()
        return item

    def submenu(self, label, icon=None, disable=None, enable=None, show=None, hide=None):
#        sm = SubMenuProxy(self, self.manager, self.parent, label, icon)
        sm = self.manager.menu(label, enable, disable, show, hide)
        sm.parent = self
        sm.icon = icon
        self._items.append(sm)
        self.update(sm)
        return sm

    def show(self):
        self.visible = True
        self.update()

    def hide(self):
        self.visible = False
        self.update()

    def enable(self):
        self.enabled = True
        self.update()

    def disable(self):
        self.enabled = False
        self.update()

    
    def separator(self):
        item = MenuItemProxy(self.manager, self, separator=True)
        self._items.append(item)
        return item

    def update(self, child=None):
        if self.parent:
            self.parent.update(self)

class MenuBar(wx.MenuBar):
    def __init__(self, manager, window=None):
        self.window = window
        self.manager = manager
        wx.MenuBar.__init__(self)
        self._menus = {}

    def menu(self, label, enable=None, disable=None, show=None, hide=None):
        retval = MenuProxy(self.manager, self, label)
        self.Append(retval.build(self.window), label)
        self._menus[retval] = len(self._menus)
        # TODO Implement subscription for showing/hiding/enabling/disabling at the menu level
        return retval


    def update(self, menu):
        self.Replace(self._menus[menu], menu.build(self.window), menu.label)

class MenuManager(object):

    def __init__(self):
        self._subscriptions = {}

    def menu_bar(self, window):
        retval = MenuBar(self, window)
        window.SetMenuBar(retval)
        return retval

    def pretty(self):
        retval = ''
        for topic, d in self._subscriptions.iteritems():
            retval += "%s\n" % topic
            for k, v in d.iteritems():
                name = ""
                for f in v:
                    if hasattr(f, '__func__'):
                        name += f.__func__.__name__ + ","
                    elif hasattr(v, '__name__'):
                        name += f.__name__ + ","
                    else:
                        name += str(f)
                name.strip(",")
                retval += "  %10s : %s\n" % (name, k)
        return retval
    
    def menu(self, label='', enable=None, disable=None, show=None, hide=None):
        retval = MenuProxy(self, None, label=label)
        self.subscribe(retval, enable=enable, disable=disable, show=show, hide=hide)
        return retval
    
    def subscribe(self, item, enable=None, disable=None, show=None, hide=None):
        for topics, func in [(enable, item.enable), (disable, item.disable), (show, item.show), (hide, item.hide)]:
            if topics != None:
                if not (isinstance(topics, list) or isinstance(topics, tuple)):
                    topics = [topics]
                for topic in topics:
                    if topic not in self._subscriptions:
                        self._subscriptions[topic] = {}
                    d = self._subscriptions[topic]
                    if item in d:
                        d[item].append(func)
                    else:
                        d[item] = [func]

    def update(self, token):
        if token not in self._subscriptions:
            return
        subscription = self._subscriptions[token]
        # Call the appropriate functions for all the subscribed items
        for item in subscription:
            for func in subscription[item]:
                func()

    def publish(self, token):
        self.update(token)

manager = MenuManager()

if __name__ == "__main__":
    app = wx.PySimpleApp()
    frame = wx.Frame(None)
    menubar = manager.menu_bar(frame)
    frame.SetMenuBar(menubar)
    
    pmenu = manager.menu()
    pmenu.item("Popup item 1")
    pmenu.item("Popup item 2")
    pmenu.separator()
    pmenu.item("Popup item 3")

    def on_context_menu(evt):
        panel.PopupMenu(pmenu.build(panel))
    
    # Stuff for popup menus
    panel = wx.Panel(frame)
    panel.SetBackgroundColour(wx.BLUE)
    panel.Bind(wx.EVT_CONTEXT_MENU, on_context_menu)

    file = menubar.menu('File')
    edit = menubar.menu('Edit')
    view = menubar.menu('View')

    def save_func(evt):
        manager.publish("SAVE")
    def close_func(evt):
        manager.publish("CLOSE")

    new = file.item("New", hide="SAVE", show="CLOSE")
    open = file.item("Open", disable="SAVE")
    close = file.item("Close", func=close_func)
    save = file.item("Save", icon="disk.png", func=save_func)
    
    cut = edit.item("Cut")
    copy = edit.item("Copy")
    
    sub = edit.submenu("Paste")
    sub.item("Subitem 1", disable="CLOSE")
    sub.item("Subitem 2")
    sub.update()
    print manager.pretty()
    frame.Show()
    app.MainLoop()
