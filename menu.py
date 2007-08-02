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

    def __init__(self, *args, **kwargs):
        super(Menu, self).__init__(*args, **kwargs)
        self._items = odict.OrderedDict()

    def AppendSeparator(self):
        item = wx.MenuItem(self, id=wx.ID_SEPARATOR)
        self.Append(item)

    def Append(self, item):
        self._items[item] = True
        wx.Menu.AppendItem(self, item)

    def _clear(self):
        for item in self._items:
            if self._items[item]:
                self.Remove(item)

    def _repopulate(self):
        last_item = None
        for item in self._items:
            if self._items[item]:
                self.Append(item)

    def _rebuild(self):
        self.Freeze()
        self._clear()
        self._repopulate()
        self.Thaw()

    def Hide(self, item):
        if self._items[item]:
            self._items[item] = False
            items = list(self._items)
            # TODO keep separators from being at the beginning or end
            # Keep 2 separators from being right next to each other
            for i, itm in enumerate(items):
                if i > 0:
                    if itm.IsSeparator() and items[i-1].IsSeparator():
                        self._items[itm] = False
            
            self._rebuild()

    def Show(self, item):
        #TODO fix separators
        if not self._items[item]:
            self._items[item] = True
            self._rebuild()


class MenuManager(object):

    def __init__(self):
        self._menus = []
        self._topics = {}

    def menu_item(self, window, menu, label, func=None, icon=None, kind=wx.ITEM_NORMAL, enabled=True, enable=None, disable=None, show=None, hide=None):
        item = wx.MenuItem(menu, -1, label, kind=kind)
        if func:
            window.Bind(wx.EVT_MENU, func, id=item.GetId())
        if icon:
            item.SetBitmap(util.get_icon(icon))
            item.SetDisabledBitmap(util.get_icon('blank.png'))
        menu.AppendItem(item)
        if not isinstance(menu, Menu):
            raise TypeError("MenuManager can only manage menu.Menu objects, (not wx.Menu)")
        
        for topics, func in [(enable, self.enable), (disable, self.disable), (show, self.show), (hide, self.hide)]:
            if not topics:
                continue
            if not isinstance(topics, list):
                topics = [topics]
                for topic in topics:
                    self.subscribe(topic, item, func)

    def publish(self, topic):
        if topic not in self._topics:
            return
        for menu_item in self._topics[topic]:
            callback = self._topics[topic][menu_item]
            callback(menu_item)

    def subscribe(self, topic, menu_item, func):
        print "Subscribing to %s" % topic
        if topic not in self._topics:
            self._topics[topic] = {}
        self._topics[topic][menu_item] = func

    def enable(self, menu_item):
        menu_item.Enable(True)

    def disable(self, menu_item):
        menu_item.Enable(False)

    def show(self, menu_item):
        menu = menu_item.GetMenu()
        menu.Show(menu_item)

    def hide(self, menu_item):
        menu = menu_item.GetMenu()
        menu.Hide(menu_item)

manager = MenuManager()
