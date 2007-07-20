import view
import wx
import sys
from odict import OrderedDict

class DictListCtrl(wx.ListCtrl):
    
    def __init__(self, parent):
        super(self.__class__, self).__init__(parent, -1, style=wx.LC_REPORT | wx.LC_VIRTUAL)
        self.InsertColumn(0, "Name")
        self.InsertColumn(1, "Value")
        self.SetItemCount(0)
        self.__items = OrderedDict()
        self.__changed = {}
        self.redattr = wx.ListItemAttr()
        self.redattr.SetTextColour("red")
        self.blackattr = wx.ListItemAttr()
        self.blackattr.SetTextColour("black")

    def OnGetItemText(self, item, col):
        if col == 0:
            return self.__items.keys()[item]
        else:
            return self.__items.values()[item]

    def OnGetItemAttr(self, item):
        key = self.__items.keys()[item]
        if key in self.__changed and self.__changed[key]:
            return self.redattr
        else:
            return self.blackattr

    def __contains__(self, key):
        return key in self.__items

    def __setitem__(self, key, value):
        changed = False
        try:
            old_value = self.__items[key]
            if value != old_value:
                changed = True
        except:
            changed = True
        if changed:
            self.__changed[key] = True
        else:
            self.__changed[key] = False

        self.__items[key] = value
        self.SetItemCount(len(self.__items))

    def __getitem__(self, key):
        return self.__items[key]

    def __iter__(self):
        return iter(self.__items.keys()[:])

    def remove_item(self, key):
        try:
            self.__items.pop(key)
            self.__changed.pop(key)
        except:
            pass
        self.SetItemCount(len(self.__items))

    def update(self, items):
        for key in items:
            self[key] = items[key]
        for key in self:
            if key not in items:
                self.remove_item(key)

class LocalsView(view.View):
    
    def __init__(self, *args, **kwargs):
        super(LocalsView, self).__init__(*args, **kwargs)
        self.list = DictListCtrl(self)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.list, 1, wx.EXPAND)
        self.SetSizer(sizer)

    def request_update(self):
        evt = view.ViewEvent(view.EVT_VIEW_REQUEST_UPDATE, self)
        wx.PostEvent(self, evt)

    def update(self, dict):
        self.list.update(dict) 
