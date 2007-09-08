import view
import wx
import wx.lib.mixins.listctrl as listmix
import sys
from odict import OrderedDict
from controls import DictListCtrl

class LocalsView(view.View):
    
    def __init__(self, *args, **kwargs):
        super(LocalsView, self).__init__(*args, **kwargs)
        self.list = DictListCtrl(self)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.list, 1, wx.EXPAND)
        self.SetSizer(sizer)

    def on_target_connected(self):
        self._fetch_data()
    def on_target_halted(self, file, line):
        self._fetch_data()
        
    def _fetch_data(self):
        if self.controller.gdb:
            self.controller.gdb.stack_list_locals(callback=self._on_data_fetched)
            
    def _on_data_fetched(self, data):
        if hasattr(data, 'locals'):
            update_dict = {}
            for item in data.locals:
                update_dict[item.name] = item.value
            self.update(update_dict)

    def update(self, dict):
        self.list.update(dict) 
