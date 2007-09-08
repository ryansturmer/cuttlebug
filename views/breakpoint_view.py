import view
import wx
import wx.lib.mixins.listctrl as listmix
import sys
from odict import OrderedDict
import util

class BreakpointListCtrl(wx.ListCtrl, listmix.ListCtrlAutoWidthMixin, util.ArtListMixin):
    TYPE = 0
    LOCATION = 1
    
    def __init__(self, parent):
        wx.ListCtrl.__init__(self, parent, -1, style=wx.LC_VIRTUAL | wx.LC_REPORT | wx.LC_HRULES )
        listmix.ListCtrlAutoWidthMixin.__init__(self)
        util.ArtListMixin.__init__(self, wx.IMAGE_LIST_SMALL)
        self.add_art('stop.png', 'stop_disabled.png')
        self.InsertColumn(0, '')
        self.InsertColumn(1, "Location")
        self.SetColumnWidth(0, 24)
        self.SetColumnWidth(1, wx.LIST_AUTOSIZE)
        self.SetItemCount(0)
        self.__items = []

        # Attributes (for changing list item colors)
        self.redattr = wx.ListItemAttr()
        self.redattr.SetTextColour("red")
        self.blackattr = wx.ListItemAttr()
        self.blackattr.SetTextColour("black")

    def OnGetItemColumnImage(self, item, col):
        #return -1
        if col == 0:
            #return 0
            return self.get_art_idx('stop.png')
        else:
            return -1

    def OnGetItemImage(self, item):
        return 0
    
    def OnGetItemText(self, item, col):
        if col == 0:
            return ''
        else:
            return self.__items[item]
        
    def OnGetItemAttr(self, item):
        return self.blackattr

    def clear(self):
        self.SetItemCount(0)
        self.__items = []
        
    def add(self,item):
        self.__items.append(item)
        self.SetItemCount(len(self.__items))
    
class BreakpointView(view.View):
    
    def __init__(self, *args, **kwargs):
        super(BreakpointView, self).__init__(*args, **kwargs)
        self.list = BreakpointListCtrl(self)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.list, 1, wx.EXPAND)
        self.SetSizer(sizer)

    def on_target_connected(self):
        self._fetch_data()
    def on_target_halted(self, file, line):
        self._fetch_data()
        
    def _fetch_data(self):
        if self.controller.gdb:
            self.controller.gdb.break_list(callback=self._on_data_fetched)
    def _on_data_fetched(self, data):
        self.list.clear()
        if hasattr(data, 'BreakpointTable'):
            self.list.clear()
            for item in data.BreakpointTable.body:
                file = item['bkpt']['file']
                line = int(item['bkpt']['line'])
                self.list.add("%s:%d" % (file, line))
            self.list.Refresh()

    def update_breakpoints(self):
        self._fetch_data()