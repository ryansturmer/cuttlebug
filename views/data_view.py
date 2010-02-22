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

class TreeItemKey(object):
    def __init__(self, parent):
        self.parent = parent
        
    def is_ok(self):
        return self in self.parent._items

class KeyTree(object):
    def __init__(self):
        self._items = {}
            
    def append_item(self, parent_key, name):
        parent = self._items[parent_key]
        item = self.AppendItem(parent, name)
        key = TreeItemKey(self)
        self._items[key] = item
        self.SetItemPyData(item, (key, None))
        return key
    '''
    def walk(self, key):
        first, cookie = self.get_first_child(key)
        if first.is_ok(): 
            yield first
            next, cookie = self.get_next_child(key, cookie)
            while next.is_ok(): 
                for child in self.walk(next): yield child
                yield next
                next, cookie = self.get_next_child(key, cookie)
    '''
    
    def walk(self, top_item, include_root=True):
        retval = [top_item] if include_root else []
        child, cookie = self.get_first_child(top_item)
        while child.is_ok():
             retval.extend(self.walk(child))
             child, cookie = self.get_next_child(top_item, cookie)
        return retval
         
    def get_first_child(self, key):
        item = self._items[key]
        i, cookie = self.GetFirstChild(item)
        if i.IsOk():
            return self.get_key(i), cookie
        else:
            return TreeItemKey(self), cookie # Return a key that's NOT ok
        
    def get_next_child(self, key, cookie):
        item = self._items[key]
        i, cookie = self.GetNextChild(item, cookie)
        if i.IsOk():
            return self.get_key(i), cookie
        else:
            return TreeItemKey(self), cookie
        
    def get_children_count(self, key, recursive=True):
        item = self._items[key]
        return self.GetChildrenCount(item, recursive)
        
    def get_key(self, item):
        if item.IsOk():
            return self.GetItemPyData(item)[0]
        else:
            raise KeyError
        
    def get_event_item(self, evt):
        return self.get_key(evt.GetItem())
    
    def get_item_data(self, key):
        item = self._items[key]
        return self.GetItemPyData(item)[1]
    
    def set_item_data(self, key, data):
        item = self._items[key]
        key, old_data = self.GetItemPyData(item)
        self.SetItemPyData(item, (key, data))
        
    def set_item_image(self, key, image, style=wx.TreeItemIcon_Normal):
        item = self._items[key]
        self.SetItemImage(item, image, style)
        
    def set_item_has_children(self, key, has_children):
        item = self._items[key]
        self.SetItemHasChildren(item, has_children)
    
    def set_item_text(self, key, text, column=0):
        item = self._items[key]
        self.SetItemText(item, text, column)
        
    def set_item_bold(self, key, bold):
        item = self._items[key]
        self.SetItemBold(item, bold)

    def add_root(self, name):
        item = self.AddRoot(name)
        key = TreeItemKey(self)
        self._items[key] = item
        self.SetItemPyData(item, (key, None))
        return key
    
    def delete(self, key):
        item = self._items.pop(key)
        self.Delete(item)
    
    def delete_children(self, key):
        item = self._items.pop(key)
        self.DeleteChildren(item)
    
    def collapse(self, key):
        item = self._items[key]
        self.Collapse(item)
        
class RuntimeTree(gizmos.TreeListCtrl, ArtListMixin, KeyTree):
    def __init__(self, parent):
        super(RuntimeTree, self).__init__(id=-1, parent=parent, style=wx.TR_DEFAULT_STYLE  | wx.TR_FULL_ROW_HIGHLIGHT | wx.TR_HIDE_ROOT | wx.TR_HAS_BUTTONS | wx.TR_LINES_AT_ROOT)
        ArtListMixin.__init__(self)
        KeyTree.__init__(self)
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

    
    def set_model(self, model):
        self.model = model
        self.model.Bind(gdb.EVT_GDB_UPDATE_VARS, self.on_var_update)
        self.model.Bind(gdb.EVT_GDB_UPDATE_STACK, self.on_stack_update)
 #       self.model.Bind(gdb.EVT_GDB_UPDATE_BREAKPOINTS, self.on_breakpoint_update)

    def on_begin_label_edit(self, evt):
        pass
    
    def on_select_item(self, evt):
        item = self.get_event_item(evt)
        if item in self.vars:
            print self.vars[item]

    def on_end_label_edit(self, evt):
        item = self.get_event_item(evt)
        name = self.get_item_data(item)
        if name in self.vars and name in self.model.vars:
            print "Editing varname %s" % name
            new_var_value = evt.GetLabel()
            self.model.var_assign(name, new_var_value)
        evt.Veto()
            
    def on_get_tooltip(self, evt):
        item = self.get_event_item(evt)
        print self.model
        print item
        if self.model and item:
            print self.model
            if item == self.stack_item:
                evt.SetToolTip(wx.ToolTip("Stack Depth: %d frames" % self.model.stack.depth))            
        data = self.get_item_data(item)
        if hasattr(data, 'file'): # This is a stack frame
            evt.SetToolTip(wx.ToolTip("Stack frame %s() at 0x%x %s" % (data.func, data.addr, "in file %s" % data.file if data.file else "")))
        elif data in self.vars:
            evt.SetToolTip(wx.ToolTip(self.model.vars[data].expression))

    def on_expanding(self, evt):
        item=self.get_event_item(evt)
        item_data=self.get_item_data(item)
        if hasattr(item_data, 'level') and self.get_children_count(item, False) == 0: #item_data is a stack frame, and we wish to list its locals
            self.model.stack_list_locals(frame=item_data.level, callback=partial(self.on_listed_locals, item))
        elif item_data in self.vars and self.get_children_count(item, False) == 0:
            self.model.var_list_children(item_data, callback=partial(self.on_listed_children, item))
        
    def on_listed_children(self, parent, result):
        if hasattr(result, 'children'):
            for child in result.children:
                varname= child['child']['name']
                self.pending_vars[varname] = parent
                
    def on_listed_locals(self, frame_item, result):
        if result.cls != 'error':
            if hasattr(result, 'locals') and frame_item.is_ok():
                frame = self.get_item_data(frame_item)
                for item in result.locals:
                    varname = self.model.var_create(item['name'], frame=frame.level, callback=partial(self.on_created_framevar, frame_item))

    def on_created_framevar(self, frame_item, result):
        if hasattr(result, 'name') and frame_item.is_ok():
            self.pending_vars[result.name] = frame_item
            self.model.var_update(result.name)
            wx.CallAfter(self.add_var_item, frame_item, result.name)

    def add_var_item(self, parent, name):
        if parent.is_ok():
            var = self.model.vars[name]
            if var.name in self.vars:
                print "CAN'T ADD VAR ITEM.  VAR %s IS ALREADY IN MODEL" % var.name
                return 
            
            var_item = self.append_item(parent, var.expression)
            self.set_item_data(var_item, name)
            if var.children:
                self.set_item_has_children(var_item, bool(var.children))
            else:
                self.set_item_has_children(var_item, False)
                self.set_item_text(var_item, var.data, 1)
                
            icon_name = var.type.icon_name
            if has_icon(icon_name):    
                self.set_item_art(var_item, icon_name)
            self.vars[name] = var_item
            
            
    def update_var_item(self, name):
        var = self.model.vars[name]
        if name in self.vars:
            var_item = self.vars[name]
            if var_item.is_ok():
                self.set_item_text(var_item, var.expression, 0)
                self.set_item_text(var_item, str(var.data), 1)

                if var.children:
                    self.set_item_has_children(var_item, True)
                else:
                    self.set_item_has_children(var_item, False)
            
    def delete_var_item(self, name):
        if name in self.vars:
            var_item = self.vars[name]
            if var_item.is_ok():
                self.delete(var_item)
            self.vars.pop(name)
                
    def add_frame_item(self, frame):
        item = self.append_item(self.stack_item, frame.func + "( )")
        self.set_item_art(item, 'frame.png' if frame.level != 0 else 'frame_active.png')
        self.set_item_has_children(item, True)
        self.set_item_bold(item, True)
        self.set_item_data(item, frame)
        self.frames.append(item)
        #self.vars_by_frame[item] = []
        
    def __get_evt_item(self, evt):
        pt = evt.GetPosition()
        item, flags = self.HitTest(pt)
        return self.get_key(item)
        
        
    def set_item_art(self, item, name, style=wx.TreeItemIcon_Normal):
        if name not in self.art:
            self.add_art(name)
        if item.is_ok():
            self.set_item_image(item, self.art[name], style)
        else:
            print "Tried to set art for item that's NOT ok?"
        
     
    def __check_stack(self):
        if self.model:
            # Our list of frames is reversed from the models, because that's how we view it.
            for model_frame, view_frame in zip(reversed(self.model.stack), self.frames):
                view_frame = self.get_item_data(view_frame)
                if model_frame.key != view_frame.key: return False
        return True
    
    def rebuild_stack(self):
        while len(self.frames) > 0:
            self.pop_stack_frame()
        self.update_stack()
    
    def update_stack(self):
        stack = self.model.stack
        # If the frame count in the view is > the frame count in the model, pop off until they match (tossing frames that no longer exist)
        while len(self.frames) > len(self.model.stack):
            self.pop_stack_frame()
        
        # Otherwise add frames until we're all in sync
        idx = len(self.frames)+1
        while len(self.frames) < len(self.model.stack):
            frame = stack[len(stack)-idx]
            self.add_frame_item(frame)
            idx += 1

    def pop_stack_frame(self):
        stack = self.model.stack
        frame_item = self.frames[-1]
        if frame_item.is_ok():
            for child in self.walk(frame_item):
                print child
                name = self.get_item_data(child)
                print name
                to_delete = set()
                if name in self.vars:
                    self.vars.pop(name)
                    self.model.var_delete(name)
                    to_delete.add(child)
                    
                for item in to_delete:
                    self.delete(item)

            self.delete(frame_item)
            self.frames.pop()
        else:
            print "Can't remove frame.  Frame item is NOT ok."
            
    def on_stack_update(self, evt):
        print "Runtime view is processing a stack update"
        if self.model:
            print self.model.stack.pretty()
            # If the stack isn't wrecked, we do an update, otherwise, we tear it down and start over (ie: interrupts)
            if self.__check_stack():
                self.update_stack()
            else:
                self.rebuild_stack()                
        
    
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
    
    def on_breakpoint_update(self, evt):
        print "Runtime view is processing a breakpoint update"
        if self.model:
            breakpoints = self.model.breakpoints
            #self.DeletChildren(self.breakpoints_item)
            self.delete_children(self.breakpoints_item)
            print breakpoints
            for bp in breakpoints:
                if bp.fullname:
                    name = os.path.split(os.path.abspath(bp.fullname))[1]
                else:
                    name = '0x%x' % bp.address
                item = self.append_item(self.breakpoints_item, name)
                self.set_item_data(item, bp)
                self.set_item_text(item, str(bp.line), 1)
                self.set_item_art(item, 'stop.png' if bp.enabled else 'stop_disabled.png')
                
    def update(self):
        pass        
    
    def clear(self):
        self.DeleteAllItems()
        root_item = self.add_root('root')
        self.root_item = root_item
        self.stack_item = self.append_item(root_item,'Call Stack')
        self.breakpoints_item = self.append_item(root_item, 'Breakpoints')
        self.registers_item = self.append_item(root_item, 'Registers')
        self.set_item_art(self.registers_item, 'chip.png')
        self.set_item_art(self.stack_item, 'stack.png')
        self.set_item_art(self.breakpoints_item, 'breakpoint.png')
        self.frames = [] # Frame keys to tree items
        self.vars = bidict() # Var names to tree items
        self.pending_vars = {} # 
        self.var_pedigree = {}
        
            
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