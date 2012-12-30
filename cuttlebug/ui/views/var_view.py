import view
import wx
import wx.lib.mixins.listctrl as listmix
import sys
from odict import OrderedDict
from cuttlebug.ui.controls import DictListCtrl
from cuttlebug.util import rgb

VARIABLES = 1

class VarTree(wx.TreeCtrl):
    def __init__(self, *args, **kwargs):
        style = kwargs.get('style', wx.TR_DEFAULT_STYLE)
        style |= wx.TR_EDIT_LABELS
        kwargs['style'] = style
        self.model = None
        self.__silent_expand = True
        super(VarTree, self).__init__(*args, **kwargs)
        self.clear()
        self.Bind(wx.EVT_LEFT_DCLICK, self.on_left_dclick)
        self.Bind(wx.EVT_TREE_BEGIN_LABEL_EDIT, self.on_start_edit)
        self.Bind(wx.EVT_TREE_END_LABEL_EDIT, self.on_end_edit)
        self.Bind(wx.EVT_TREE_ITEM_EXPANDING, self.on_expanding)
#        self.tree.Bind(wx.EVT_RIGHT_DOWN, self.on_right_click)
        self.__changed = []
        self.__suppress_child_listing = False
        self.__cached_edit_value = ''
        
    def __get_evt_item(self, evt):
        pt = evt.GetPosition()
        item, flags = self.HitTest(pt)
        return item
    
    def on_start_edit(self, evt):
        item = evt.GetItem()
        if item.IsOk() and item != self.root_item:
            entry = self.GetPyData(item)
            if not entry or entry not in self.model or self.model[entry].children > 0:
                evt.Veto()
            else:
                evt.Skip()
        else:
            evt.Veto()
            
    def on_end_edit(self, evt):
        item = evt.GetItem()
        entry = self.GetPyData(item)
        var = self.model[entry]
        label = evt.GetLabel()
        if not evt.IsEditCancelled():
            self.Parent.controller.gdb.var_assign(var.name, label)
        self.SetItemText(item, self.__cached_edit_value)
        evt.Veto()
        
    def on_left_dclick(self, evt):
        item = self.__get_evt_item(evt)
        entry = self.GetPyData(item)
        if self.model and item.IsOk() and entry in self.model:
            self.__cached_edit_value = self.GetItemText(item)
            var = self.model[entry]
            self.SetItemText(item,str(var.data))
            self.EditLabel(item)
        
    def on_expanding(self, evt):
        item=evt.GetItem()
        name=self.GetItemPyData(item)
        if not self.__suppress_child_listing:
            if name in self.model:
                self.Parent.controller.gdb.var_list_children(name)
            
    def set_model(self, model):
        self.model = model
        
    def clear(self):
        self.DeleteAllItems()
        self.root_item = self.AddRoot('Local Variables')
        self.SetPyData(self.root_item, VARIABLES)
        self.items = {}
        
        
    def __add_var(self, var):
        parent = self.model.get_parent(var.name)
        parent_item = self.items.get(parent, self.root_item)
        if var.children == 0:
            item = self.AppendItem(parent_item, "%s = %s" % (var.expression, var.data))
        else:
            item = self.AppendItem(parent_item, var.expression)
            self.SetItemHasChildren(item, True)
        self.SetPyData(item,var.name)
        self.items[var.name] = item
        
        self.__suppress_child_listing = True
        if parent_item != self.root_item:
            self.Expand(parent_item)
        self.__suppress_child_listing = False
        
        return item
    
    def __update_var(self, var):
        item = self.items[var.name]
        if var.children == 0:
            self.SetItemText(item, "%s = %s" % (var.expression, var.data))
            self.SetItemTextColour(item, rgb(255,0,0))
            self.__changed.append(item)
        else:
            self.SetItemText(item, var.expression)
            
    def __remove_var(self, name):
        if name in self.items:
            item = self.items.pop(name)
            self.Delete(item)
            
    def __add_or_update_var(self, var):
        #print "adding or updating %s" % var
        if var.name in self.items:
            self.__update_var(var)
        else:
            self.__add_var(var)
            
    def update(self, names):
        self.Freeze()
        while self.__changed:
            item = self.__changed.pop()
            self.SetItemTextColour(item, rgb(0,0,0))
        for name in names:
            if name in self.model:
                var = self.model[name]
                self.__add_or_update_var(var)
            else:
                self.__remove_var(name)
        self.Thaw()
            
class LocalsView(view.View):
    
    def __init__(self, *args, **kwargs):
        super(LocalsView, self).__init__(*args, **kwargs)
        self.tree = VarTree(self)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.tree, 1, wx.EXPAND)
        self.SetSizer(sizer)
  
    def set_model(self, model):
        self.tree.set_model(model)
        
    def update(self, locals):
        self.tree.update(locals)  