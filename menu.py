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

class MenuItemProxy(object):

    def __init__(self, parent, label='', func=None, icon=None, kind=wx.ITEM_NORMAL, separator=False):
        self.parent = parent
        
        self._label = label
        self._func = func
        self._separator = bool(separator)
        self.kind = kind
        self.visible = True
        self.enabled = True
        self.icon = icon

    def __get_icon(self):
        return self._icon
    def __set_icon(self, icon):
        if self._separator:
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
        if self._separator:
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
        self._items = []

    def __iter__(self):
        return iter(self._items)

    def build(self, window=None):
        retval = wx.Menu()
        for item in self._items:
            if item.visible:
                menuitem = item.build(retval, window)
                retval.AppendItem(menuitem)
                if item.enabled:
                    menuitem.Enable()
                else:
                    menuitem.Enable(False)
             
        return retval

    def item(self, label, func=None, icon=None, kind=wx.ITEM_NORMAL, disable=None, enable=None, show=None, hide=None):
        item = MenuItemProxy(self, label=label, func=func, icon=icon, kind=kind)
        self.manager.subscribe(item, enable=enable, disable=disable, show=show, hide=hide)
        self._items.append(item)
        self.update()
        return item

    def enable(self): pass
    def disable(self): pass
    def show(self): pass
    def hide(self): pass
    
    def separator(self):
        item = MenuItemProxy(self.manager, self, separator=True)
        self._items.append(item)
        return item

    def update(self):
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

    def menu(self, label='', enable=None, disable=None, show=None, hide=None):
        retval = MenuProxy(self, None, label=label)
        self.subscribe(retval, enable=enable, disable=disable, show=show, hide=hide)
        return retval
    
    def subscribe(self, item, enable=None, disable=None, show=None, hide=None):
        for subscription, func in [(enable, item.enable), (disable, item.disable), (show, item.show), (hide, item.hide)]:
            if subscription:
                if not isinstance(subscription, list) or isinstance(subscription, tuple):
                    subscription = [subscription]
            
                for token in subscription:
                    if token not in self._subscriptions:
                        self._subscriptions[token] = {}

                    self._subscriptions[token][item] = func

    def update(self, token):
        if token not in self._subscriptions:
            return
        subscription = self._subscriptions[token]
        # Call the appropriate function for all the subscribed items
        for item in subscription:
            subscription[item]()

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
        panel.PopupMenu(pmenu.build_wx_menu(panel))
    
    # Stuff for popup menus
    panel = wx.Panel(frame)
    panel.SetBackgroundColour(wx.BLUE)
    panel.Bind(wx.EVT_CONTEXT_MENU, on_context_menu)

    file = menubar.menu('File')
    edit = menubar.menu('Edit')
    view = menubar.menu('View')

    def save_func(evt):
        manager.publish("SAVE")
        print "Save was clicked"
    def close_func(evt):
        manager.publish("CLOSE")
        print "Close was clicked"

    new = file.item("New", hide="SAVE", show="CLOSE")
    open = file.item("Open", disable="SAVE")
    close = file.item("Close", func=close_func)
    close = file.item("Save", icon="disk.png", func=save_func)

    print file
    print edit
    print view
    
    frame.Show()
    app.MainLoop()
