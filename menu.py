import wx
import odict
import util

# APPLICATION SPECIFIC
# pub/sub topics
PROJECT_OPEN = 0
PROJECT_CLOSE = 1

TARGET_ATTACHED = 2
TARGET_DETACHED = 3

TARGET_RUNNING = 4
TARGET_HALTED = 5


class Menu(wx.Menu):
    'Just like a wx.Menu, but iterable and able to show/hide items'
        
    def __init__(self, *args, **kwargs):
        wx.Menu.__init__(self, *args, **kwargs)
        self._items = odict.OrderedDict() # Menu item -> (visible, enabled)

    def __iter__(self):
        return iter(self._items)

    def AppendSeparator(self):
        item = wx.MenuItem(self, id=wx.ID_SEPARATOR)
        item.parent_menu = self # Do this because GetMenu() wont work with menu items that have been removed from a menu!
        self.AppendItem(item)

    def AppendItem(self, item):
        print "Adding a NEW item to the menu: %s" % item.GetItemLabelText()
        self._items[item] = (True, True) # New items are visible and enabled by default
        item.parent_menu = self # See above
        wx.Menu.AppendItem(self, item)

    def RemoveItem(self, item):
        self._clear()
        self._items.pop(item)
        self._repopulate()
        return item

    def _clear(self):
        for item in self._items:
            visible, enabled = self._items[item]
            if visible:
                print "Removing item: %s" % item.GetItemLabelText()
                wx.Menu.RemoveItem(self, item)

    def _repopulate(self):
        for item in self:
            visible, enabled = self._items[item]
            if visible:
                print "Adding item: %s enabled: %s" % (item.GetItemLabelText(), enabled)
                item = wx.Menu.AppendItem(self, item)
                if enabled:
                    #item.Enable(True)
                    self.Enable(item.GetId(), True)
                else:
                    #item.Enable(False)
                    self.Enable(item.GetId(), False)
            else:
                pass

    def rebuild(self):
        print "rebuild()ing"
        self._clear()
        self._repopulate()

    # You have to call rebuild() after you do these for the changes to take effect
    def enable(self, item):
        visible, enabled = self._items[item]
        self._items[item] = (visible, True)

    def disable(self, item):
        visible, enabled = self._items[item]
        self._items[item] = (visible, False)

    def hide(self, item):
        visible, enabled = self._items[item]    
        self._items[item] = (False, enabled)

    def show(self, item):
        visible, enabled = self._items[item]    
        self._items[item] = (True, enabled)

    def __str__(self):
        retval = "v e label\n"
        for item in self:
            visible, enabled = self._items[item]
            retval += "%s %s %s\n" % ("*" if visible else " ", "*" if enabled else " ", item.GetItemLabelText())
        return retval

class MenuManager(object):

    def __init__(self):
        self._menus = []
        self._topics = {}

    def menu_item(self, window, menu, label, func=None, icon=None, kind=wx.ITEM_NORMAL, enabled=True, enable=None, disable=None, show=None, hide=None):
        if not isinstance(menu, Menu):
            raise TypeError("MenuManager can only manage menu.Menu objects, (not wx.Menu)")
        item = wx.MenuItem(menu, -1, label, kind=kind)
        if func:
            menu.Bind(wx.EVT_MENU, func, id=item.GetId())
        if icon:
            item.SetBitmap(util.get_icon(icon))
            item.SetDisabledBitmap(util.get_icon('blank.png'))

        menu.AppendItem(item)
        
        for topics, func in [(enable, self.enable), (disable, self.disable), (show, self.show), (hide, self.hide)]:
            if topics == None:
                continue
            if not isinstance(topics, list):
                topics = [topics]
            for topic in topics:
                self._subscribe(topic, item, func)

    def publish(self, topic):
        if topic not in self._topics:
            return
        print "publishing topic %s: %d items affected." % (topic, len(self._topics[topic]))
        rebuilders = set()
        for menu_item in self._topics[topic]:
            if menu_item.parent_menu not in rebuilders:
                rebuilders.add(menu_item.parent_menu)
            callback = self._topics[topic][menu_item]
            callback(menu_item)
        for menu in rebuilders:
            menu.rebuild()
            print menu

    def _subscribe(self, topic, menu_item, func):
        if topic not in self._topics:
            self._topics[topic] = {}
        self._topics[topic][menu_item] = func

    def enable(self, menu_item):
        print "  mgr: enabling %s in menu %s" % (menu_item.GetItemLabelText(), menu_item.parent_menu.GetTitle())
        menu = menu_item.parent_menu
        menu.enable(menu_item)

    def disable(self, menu_item):
        print "  mgr: disabling %s in menu %s" % (menu_item.GetItemLabelText(), menu_item.parent_menu.GetTitle())
        menu = menu_item.parent_menu
        menu.disable(menu_item)

    def show(self, menu_item):
        print "  mgr: showing %s in menu %s" % (menu_item.GetItemLabelText(), menu_item.parent_menu.GetTitle())
        menu = menu_item.parent_menu
        menu.show(menu_item)

    def hide(self, menu_item):
        print "  mgr: hiding %s in menu %s" % (menu_item.GetItemLabelText(), menu_item.parent_menu.GetTitle())
        menu = menu_item.parent_menu
        menu.hide(menu_item)

manager = MenuManager()
