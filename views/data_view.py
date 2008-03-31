import view
import wx
import wx.gizmos as gizmos
import wx.lib.mixins.listctrl as listmix
import sys
from odict import OrderedDict
from controls import DictListCtrl
from util import rgb, ArtListMixin
from functools import partial
import gdb

class RuntimeTree(gizmos.TreeListCtrl, ArtListMixin):
    def __init__(self, parent):
        gizmos.TreeListCtrl.__init__(self, id=-1, parent=parent, style=wx.TR_DEFAULT_STYLE | wx.TR_COLUMN_LINES | wx.TR_FULL_ROW_HIGHLIGHT)
        ArtListMixin.__init__(self)
        self.Bind(wx.EVT_TREE_ITEM_EXPANDING, self.on_expanding)
        self.AddColumn('Context')
        self.AddColumn('Value')        
        self.clear()
        
       
    def on_expanding(self, evt):
        item=evt.GetItem()
        item_data=self.GetPyData(item)
        if hasattr(item_data, 'level'): #item_data is a stack frame, and we wish to list its locals
            self.model.stack_list_locals(frame=item_data.level, callback=partial(self.on_listed_locals, item_data))
        elif item_data in self.vars:
            self.model.var_list_children(item_data, callback=partial(self.on_listed_children, item))
        
    def on_listed_children(self, parent, result):
        if hasattr(result, 'children'):
            for child in result.children:
                varname= child['child']['name']
                self.pending_vars[varname] = parent
                
    def on_listed_locals(self, frame, result):
        if result.cls != 'error':
            if hasattr(result, 'locals') and frame.key in self.frames:
                for item in result.locals:
                    varname = self.model.var_create(item['name'], frame=frame.level, callback=partial(self.on_created_framevar, frame))

    def on_created_framevar(self, frame, result):
        if hasattr(result, 'name') and frame.key in self.frames:
            self.pending_vars[result.name] = self.frames[frame.key]
            self.model.var_update(result.name)
            #wx.CallAfter(self.add_var_item, self.frames[frame], result.name)
                         
    def add_var_item(self, parent, name):
        var = self.model.vars[name]
        var_item = self.AppendItem(parent, var.expression)
        self.SetItemPyData(var_item, name)
        if var.children:
            self.SetItemHasChildren(var_item, bool(var.children))
        else:
            self.SetItemHasChildren(var_item, False)
            self.SetItemText(var_item, var.data, 1)
        self.vars[name] = var_item

    def update_var_item(self, name):
        var = self.model.vars[name]
        if name in self.vars:
            var_item = self.vars[name]
            self.SetItemText(var_item, var.expression, 0)
            if var.children:
                self.SetItemHasChildren(var_item, True)
            else:
                self.SetItemHasChildren(var_item, False)
                self.SetItemText(var_item, var.data, 1)
            
    def delete_var_item(self, name):
        if name in self.vars:
            var_item = self.vars[name]
            self.Delete(var_item)
            self.vars.pop(name)
            
        
    def __get_evt_item(self, evt):
        pt = evt.GetPosition()
        item, flags = self.HitTest(pt)
        return item
        
    def set_model(self, model):
        self.model = model
        self.model.Bind(gdb.EVT_GDB_UPDATE_VARS, self.on_var_update)
        self.model.Bind(gdb.EVT_GDB_UPDATE_STACK, self.on_stack_update)
        
    def set_item_art(self, item, name, style=wx.TreeItemIcon_Normal):
        if name not in self.art:
            self.add_art(name)
        self.SetItemImage(item, self.art[nam], style)
        
    def on_var_update(self, evt):
        names = evt.data
        print names
        print self.pending_vars
        for name in names:
            if name in self.model.vars:
                if name in self.pending_vars: # Vars that are waiting to get added to the tree
                    parent = self.pending_vars.pop(name)
                    wx.CallAfter(self.add_var_item, parent, name)
                elif name in self.vars: # Vars that are already in the tree
                    wx.CallAfter(self.update_var_item, name)
            else:
                if name in self.pending_vars: self.pending_vars.pop(name)
                if name in self.vars: wx.CallAfter(self.delete_var_item,name)
                    
    def on_stack_update(self, evt):
        if self.model:
            stack = self.model.stack
            stack_keys = set([frame.key for frame in stack])
            items_to_remove = set()
            for frame_key, frame_item in self.frames.iteritems():
                if not stack.has_key(frame_key):
                    self.Delete(frame_item)
                    items_to_remove.add(frame_key)
            for frame_key in items_to_remove: self.frames.pop(frame_key)
            for frame in reversed(list(stack)):
                if frame.key not in self.frames:
                    item = self.AppendItem(self.stack_item, frame.func)
                    self.SetItemHasChildren(item)
                    self.SetPyData(item, frame)
                    self.frames[frame.key] = item
        
                    
    def update(self):
        pass        
    
    def clear(self):
        self.DeleteAllItems()
        self.stack_item = self.AddRoot('Call Stack')
        self.frames = {}
        self.vars = {}
        self.pending_vars = {}
        
            
class DataView(view.View):
    
    def __init__(self, *args, **kwargs):
        super(DataView, self).__init__(*args, **kwargs)
        self.tree = RuntimeTree(self)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.tree, 1, wx.EXPAND)
        self.SetSizer(sizer)
  
    def set_model(self, model):
        self.tree.set_model(model)
        
    def update(self, stack):
        self.tree.update()