import view
import wx
import wx.gizmos as gizmos
import wx.lib.mixins.listctrl as listmix
import sys
from odict import OrderedDict
from controls import DictListCtrl
from util import rgb, ArtListMixin, has_icon, bidict, button
from functools import partial
import gdb
import os

class VariableEditor(wx.Panel):
    def __init__(self, parent, widget=None):
        wx.Panel.__init__(self, parent, id=wx.ID_ANY)
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.widget=widget
        if widget:
            self.widget = widget
            widget.Reparent(self)
            sizer.AddStretchSpacer(1)
            sizer.Add(widget, flag=wx.EXPAND)
            self.SetSizer(sizer)
        
    def DoGetBestSize(self):
        return wx.Size(100,100)    

class RuntimeTree(gizmos.TreeListCtrl, ArtListMixin):
    def __init__(self, parent):
        super(RuntimeTree, self).__init__(id=-1, parent=parent, style=wx.TR_DEFAULT_STYLE  | wx.TR_FULL_ROW_HIGHLIGHT | wx.TR_HIDE_ROOT | wx.TR_HAS_BUTTONS | wx.TR_LINES_AT_ROOT)
        ArtListMixin.__init__(self)
        self.SetFont(wx.Font(8, wx.FONTFAMILY_MODERN, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))

        self.Bind(wx.EVT_TREE_ITEM_EXPANDING, self.on_expanding)
        self.Bind(wx.EVT_TREE_ITEM_GETTOOLTIP, self.on_get_tooltip)
        self.Bind(wx.EVT_TREE_BEGIN_LABEL_EDIT, self.on_begin_label_edit)
        self.Bind(wx.EVT_TREE_END_LABEL_EDIT, self.on_end_label_edit)
        self.Bind(wx.EVT_TREE_SEL_CHANGED, self.on_select_item)
        self.model = None
        self.AddColumn('Context')
        self.AddColumn('Value')      
        self.SetColumnEditable(1, True)
        self.SetColumnAlignment(1, wx.ALIGN_RIGHT)
        self.clear()

    def on_begin_label_edit(self, evt):
        pass
    
    def on_select_item(self, evt):
        item = evt.GetItem()
        if item in self.vars:
            print self.vars[item]
    def on_end_label_edit(self, evt):
        item = evt.GetItem()
        data = self.GetPyData(item)
        if data in self.vars and data in self.model.vars:
            #print "Editing varname %s" % data
            new_var_value = evt.GetLabel()
            self.model.var_assign(data, new_var_value)
        evt.Veto()
            
    def on_get_tooltip(self, evt):
        item = evt.GetItem()
        print self.model
        print item
        if self.model and item:
            print self.model
            if item == self.stack_item:
                evt.SetToolTip(wx.ToolTip("Stack Depth: %d frames" % self.model.stack.depth))            
        data = self.GetPyData(item)
        if hasattr(data, 'file'): # This is a stack frame
            evt.SetToolTip(wx.ToolTip("Stack frame %s() at 0x%x %s" % (data.func, data.addr, "in file %s" % data.file if data.file else "")))
        elif data in self.vars:
            evt.SetToolTip(wx.ToolTip(self.model.vars[data].expression))

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
            if hasattr(result, 'locals') and frame.key in self.frames and frame.key not in self.expanded_frames:
                self.expanded_frames = frame.key
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
            
        icon_name = var.type.icon_name
        if has_icon(icon_name):    
            self.set_item_art(var_item, icon_name)
        self.vars[name] = var_item

    def update_var_item(self, name):
        var = self.model.vars[name]
        if name in self.vars:
            var_item = self.vars[name]
            self.SetItemText(var_item, var.expression, 0)
            self.SetItemText(var_item, str(var.data), 1)

            if var.children:
                self.SetItemHasChildren(var_item, True)
            else:
                self.SetItemHasChildren(var_item, False)
            
    def delete_var_item(self, name):
        if name in self.vars:
            var_item = self.vars[name]
            self.Delete(var_item)
            self.vars.pop(name)
                
    def add_frame_item(self, frame):
        item = self.AppendItem(self.stack_item, frame.func + "( )")
        self.set_item_art(item, 'frame.png' if frame.level != 0 else 'frame_active.png')
        self.SetItemHasChildren(item)
        self.SetItemBold(item, True)
        self.SetPyData(item, frame)
        self.frames[frame.key] = item
        
    def __get_evt_item(self, evt):
        pt = evt.GetPosition()
        item, flags = self.HitTest(pt)
        return item
        
    def set_model(self, model):
        self.model = model
        self.model.Bind(gdb.EVT_GDB_UPDATE_VARS, self.on_var_update)
        self.model.Bind(gdb.EVT_GDB_UPDATE_STACK, self.on_stack_update)
        self.model.Bind(gdb.EVT_GDB_UPDATE_BREAKPOINTS, self.on_breakpoint_update)
        
    def set_item_art(self, item, name, style=wx.TreeItemIcon_Normal):
        if name not in self.art:
            self.add_art(name)
        self.SetItemImage(item, self.art[name], style)
        
    def on_var_update(self, evt):
        print "Runtime view is processing a var update."
        names = evt.data
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
        print "Runtime view is processing a stack update"
        if self.model:
            stack = self.model.stack
            stack_keys = set([frame.key for frame in stack])
            items_to_remove = set()
            for frame_key, frame_item in self.frames.iteritems():
                if not stack.has_key(frame_key):
                    self.Delete(frame_item)
                    items_to_remove.add(frame_key)
            for frame_key in items_to_remove: self.frames.pop(frame_key)
            item = None
            for frame in reversed(list(stack)):
                if frame.key not in self.frames:
                    self.add_frame_item(frame)
            if item:
                self.set_item_art(item, 'frame_active.png')
        
    def on_breakpoint_update(self, evt):
        print "Runtime view is processing a breakpoint update"
        if self.model:
            breakpoints = self.model.breakpoints
            #self.DeletChildren(self.breakpoints_item)
            self.DeleteChildren(self.breakpoints_item)
            print breakpoints
            for bp in breakpoints:
                if bp.fullname:
                    name = os.path.split(os.path.abspath(bp.fullname))[1]
                else:
                    name = '0x%x' % bp.address
                item = self.AppendItem(self.breakpoints_item, name)
                self.SetPyData(item, bp)
                self.SetItemText(item, str(bp.line), 1)
                self.set_item_art(item, 'stop.png' if bp.enabled else 'stop_disabled.png')
                
    def update(self):
        pass        
    
    def clear(self):
        self.DeleteAllItems()
        root_item = self.AddRoot('root')
        self.root_item = root_item
        self.stack_item = self.AppendItem(root_item,'Call Stack')
        self.breakpoints_item = self.AppendItem(root_item, 'Breakpoints')
        self.registers_item = self.AppendItem(root_item, 'Registers')
        self.set_item_art(self.registers_item, 'chip.png')
        self.set_item_art(self.stack_item, 'stack.png')
        self.set_item_art(self.breakpoints_item, 'breakpoint.png')
        self.frames = bidict({})
        self.vars = bidict({})
        self.pending_vars = {}
        self.expanded_frames = set()
        
            
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