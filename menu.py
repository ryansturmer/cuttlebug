import wx
import odict

class Menu(wx.Menu):

    def __init__(self, *args, **kwargs):
        wx.Menu(self, *args, **kwargs)
        self._items = OrderedDict()

    def AppendSeparator(self):
        item = wx.MenuItem(self, id=wx.ID_SEPARATOR)
        self.Append(item)

    def Append(self, item):
        self._items[item] = True
        wx.Menu.Append(self, item)

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

            # Keep 2 separators from being right next to each other
            for i, itm in enumerate(items):
                if i > 0:
                    if itm.IsSeparator() and items[i-1].IsSeparator():
                        self._items[itm] = False
            
            self._rebuild()

    def Show(self, item):
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
            item.SetBitmap(get_icon(icon))
            item.SetDisabledBitmap(get_icon('blank.png'))
        menu.AppendItem(item)
        if not isinstance(menu, Menu):
            raise TypeError("MenuManager can only manage menu.Menu objects, (not wx.Menu)")


    def enable(self, menu_item):
        menu_item.Enable(True)

    def disable(self, menu_item):
        menu_item.Enable(False)

    def show(self, menu_item):
        menu = menu_item.GetMenu()
        menu.

    def hide(self, menu_item):
        menu = menu_item.GetMenu()
        menu.Remove(menu_item)
