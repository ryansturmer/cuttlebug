import view
import wx
import wx.gizmos as gizmos
import wx.lib.mixins.listctrl as listmix
import sys
from odict import OrderedDict
from controls import DictListCtrl
from util import rgb, ArtListMixin, has_icon, bidict, button, KeyTree, TreeItemKey
from functools import partial
import gdb
import os, threading

        
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
        self.lock = threading.RLock()
        self.__var_idx = 0
        self.clear()

    def get_frame_items(self):
        if self.stack_item.is_ok():
            l=  list(self.children(self.stack_item))
        else:
            l = []
        return l
    def get_frames(self):
        l =  [self.get_item_data(frame_item) for frame_item in self.get_frame_items()]
        return l
    
    def get_frame_count(self):
        if self.stack_item.is_ok():
            return self.get_children_count(self.stack_item, recursive=False)
        else:
            return 0 
        
    def get_var_name(self):
        name = "rtv_%d" % self.__var_idx
        self.__var_idx += 1
        return name 
    
    def set_model(self, model):
        self.model = model
        self.model.Bind(gdb.EVT_GDB_UPDATE_VARS, self.on_var_update)
        self.model.Bind(gdb.EVT_GDB_UPDATE_STACK, self.on_stack_update)
        self.model.Bind(gdb.EVT_GDB_UPDATE_BREAKPOINTS, self.on_breakpoint_update)
        self.model.Bind(gdb.EVT_GDB_UPDATE_REGISTERS, self.on_register_update)

    def on_begin_label_edit(self, evt):
        item = self.get_event_item(evt)
        name = self.get_item_data(item)
        if name in self.var_registry: 
            if self.is_descendent(item, self.get_frame_items()[-1]):
                return
        evt.Veto()
            
    def on_select_item(self, evt):
        item = self.get_event_item(evt)
        print item
        print self.get_item_data(item)
        evt.Skip()
        
    def on_end_label_edit(self, evt):
        item = self.get_event_item(evt)
        name = self.get_item_data(item)
        if name in self.var_registry and name in self.model.vars:
            new_var_value = evt.GetLabel()
            self.model.var_assign(name, new_var_value)
        evt.Veto()
            
    def on_get_tooltip(self, evt):
        item = self.get_event_item(evt)
        if self.model and item:
            if item == self.stack_item:
                evt.SetToolTip(wx.ToolTip("Stack Depth: %d frames" % self.model.stack.depth))            
        data = self.get_item_data(item)
        if hasattr(data, 'file'): # This is a stack frame
            evt.SetToolTip(wx.ToolTip("Stack frame %s() at 0x%x %s" % (data.func, data.addr, "in file %s" % data.file if data.file else "")))
        elif data in self.var_registry:
            evt.SetToolTip(wx.ToolTip(self.model.vars[data].expression))

    def on_expanding(self, evt):
        item=self.get_event_item(evt)
        item_data=self.get_item_data(item)
        if hasattr(item_data, 'level') and self.get_children_count(item, False) == 0: #item_data is a stack frame, and we wish to list its locals
            self.model.stack_list_locals(frame=item_data.level, callback=partial(self.__on_listed_locals, item))
        elif item_data in self.var_registry and self.get_children_count(item, False) == 0:
            self.model.var_list_children(item_data, callback=partial(self.__on_listed_children, item))
       
    def __on_listed_children(self, parent, result):
        if hasattr(result, 'children'):
            for child in result.children:
                varname= child['child']['name']
                self.lock.acquire()
                self.pending_var_additions[varname] = parent
                self.lock.release()
                
    def __on_listed_locals(self, frame_item, result):
        if result.cls != 'error':
            if hasattr(result, 'locals') and frame_item.is_ok():
                frame = self.get_item_data(frame_item)
                if self.get_children_count(frame_item, recursive=False) == 0:
                    for item in result.locals:
                        varname = self.get_var_name()
                        self.lock.acquire()
                        self.pending_var_additions[varname] = frame_item
                        self.lock.release()
                        self.model.var_create(item['name'], frame=frame.level, callback=self.__on_created_var, name=varname)

    def __on_created_var(self, result):
        if hasattr(result, 'name'):
            self.model.var_update(result.name)

    def on_var_update(self, evt):
        names = evt.data
        for name in names:
            if name in self.pending_var_additions:
                self.lock.acquire()
                parent = self.pending_var_additions.pop(name)
                self.lock.release()
                wx.CallAfter(self.add_var_item, parent, name, self.model.vars[name])
            elif name in self.pending_var_updates:
                self.lock.acquire()
                var_item = self.pending_var_updates.pop(name)
                old_name= self.get_item_data(var_item)
                if old_name in self.var_registry:
                    self.var_registry.pop(old_name)
                self.lock.release()
                wx.CallAfter(self.update_var_item, var_item, name, self.model.vars[name])
            elif name in self.var_registry and name in self.model.vars:
                var_item = self.var_registry[name]
                wx.CallAfter(self.update_var_item, var_item, name, self.model.vars[name])
            else:
                pass
            
    def add_var_item(self, parent, name, var):
        if parent.is_ok():
            var_item = self.append_item(parent, var.expression)
            self.update_var_item(var_item, name, var)
            
    def update_var_item(self, var_item, name, var):
        if var_item.is_ok():
            self.set_item_data(var_item, name)
            if var.children:
                self.set_item_has_children(var_item, bool(var.children))
            else:
                self.set_item_has_children(var_item, False)
                self.set_item_text(var_item, var.data, 1)
                
            icon_name = var.type.icon_name
            if has_icon(icon_name):    
                self.set_item_art(var_item, icon_name)
            self.lock.acquire()
            self.var_registry[name] = var_item
            self.lock.release()
            
    def delete_var_item(self, var_item):
        if var_item.is_ok():
            self.delete(var_item)
            
    def add_frame_item(self, frame):
        item = self.append_item(self.stack_item, frame.func + "( )")
        self.update_frame_item(item, frame)
        
    def update_frame_item(self, frame_item, frame):
        self.set_item_data(frame_item, frame)
        self.set_item_art(frame_item, 'frame.png' if frame.level != 0 else 'frame_active.png')
        self.set_item_has_children(frame_item, True)
        self.set_item_bold(frame_item, True)
        self.set_item_data(frame_item, frame)
        
        
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
            for model_frame, view_frame in zip(reversed(self.model.stack), self.get_frames()):
                if model_frame.key != view_frame.key: return False
        return True
    
    def get_var_frame(self, name):
        frame = None
        item = self.var_registry[name]
        frames = self.get_frames()
        while frame not in frames:
            item = self.get_parent(item)
            if item.is_ok():
                frame = self.get_item_data(item)
        return frame
    
    def scrub_vars(self, all_vars=False):
        to_update = {}        
        if self.get_frame_count() > 0:
            frame_items = self.get_frame_items()
            for name, var_item in self.var_registry.iteritems():
                if (not self.is_descendent(var_item, frame_items[-1]) or all_vars) and name in self.model.vars:
                    var = self.model.vars[name]
                    frame = self.get_var_frame(name)
                    varname = self.get_var_name()
                    to_update[(name, varname)] = (frame, var)
                    self.pending_var_updates[varname] = var_item
                            
            for (old_name, new_name), (frame, var)in to_update.iteritems(): 
                self.model.var_delete(old_name)
                self.model.var_create(var.expression, frame=frame.level, callback=self.__on_created_var, name=new_name)
                    
    def clear_stack(self):
        n = self.get_frame_count()
        for i in range(n):
            self.pop_stack_frame()
            
    def rebuild_stack(self):
        self.clear_stack()
        self.update_stack()
    
    def update_stack(self):
        stack = self.model.stack
        stack_changed=False
        # If the frame count in the view is > the frame count in the model, pop off until they match (tossing frames that no longer exist)
        n = self.get_frame_count()-len(stack)
        if n > 0:
            for i in range(n):
                self.pop_stack_frame()
                stack_changed = True
        
        for frame_item, frame in zip(self.get_frame_items(), reversed(self.model.stack)):
            self.update_frame_item(frame_item, frame)
            
        # Otherwise add frames until we're all in sync
        idx = self.get_frame_count()+1
        while self.get_frame_count() < len(self.model.stack):
            frame = stack[len(stack)-idx]
            self.add_frame_item(frame)
            idx += 1
                        
        self.scrub_vars(all_vars=stack_changed)

    def pop_stack_frame(self):
        stack = self.model.stack
        frame_item = self.get_frame_items()[-1]
        if frame_item.is_ok():
            for child in self.walk(frame_item):
                name = self.get_item_data(child)
                to_delete = set()
                if name in self.var_registry:
                    self.var_registry.pop(name)
                    self.model.var_delete(name)
                    to_delete.add(child)
                    
                for item in to_delete:
                    self.delete(item)

            self.delete(frame_item)
        else:
            print "Can't remove frame.  Frame item is NOT ok."
            
    def on_stack_update(self, evt):
        #print self.model.stack.pretty()
        if self.model:
            if self.__check_stack():
                wx.CallAfter(self.update_stack)
            else:
                wx.CallAfter(self.rebuild_stack)                
            
    def update_breakpoints(self):
        if self.model and self.breakpoints_item.is_ok():
            breakpoints = self.model.breakpoints
            self.delete_children(self.breakpoints_item)
            for bp in breakpoints:
                if bp.fullname:
                    name = os.path.split(os.path.abspath(bp.fullname))[1]
                else:
                    name = '0x%x' % bp.address
                item = self.append_item(self.breakpoints_item, name)
                self.set_item_data(item, bp)
                self.set_item_text(item, str(bp.line), 1)
                self.set_item_art(item, 'stop.png' if bp.enabled else 'stop_disabled.png')

    def update_registers(self, names):
        if self.model and self.registers_item.is_ok():
            registers = self.model.registers
            if len(registers) != self.get_children_count(self.registers_item, recursive=False):
                self.delete_children(self.registers_item)
                for key, value in registers.iteritems():
                    item = self.append_item(self.registers_item, key)
                    self.set_item_text(item, value, 1)
                    self.set_item_data(item, key)
                    self.register_registry[key] = item
            else:
                for child in self.children(self.registers_item):
                    self.set_item_text_colour(child, wx.BLACK)
                    
                for name in names:
                    item = self.register_registry[name]
                    self.set_item_text(item, registers[name], 1)
                    self.set_item_text_colour(item, wx.RED)
                    
    def on_breakpoint_update(self, evt):
        wx.CallAfter(self.update_breakpoints)
        
    def on_register_update(self, evt):
        wx.CallAfter(self.update_registers, evt.data)
        
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
        self.var_registry = bidict() # Var names to tree items
        self.pending_var_additions = {}
        self.pending_var_updates = {}
        self.register_registry = bidict()
        
            
class RuntimeView(view.View):
    
    def __init__(self, *args, **kwargs):
        super(RuntimeView, self).__init__(*args, **kwargs)
        self.tree = RuntimeTree(self)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.tree, 1, wx.EXPAND)
        self.SetSizer(sizer)
  
    def set_model(self, model):
        self.tree.set_model(model)
        
    def update(self, stack):
        self.tree.update()
        
class GDBDebugView(view.View):
    def __init__(self, *args, **kwargs):
        super(GDBDebugView, self).__init__(*args, **kwargs)
        self.list = DictListCtrl(self, color_changes=False)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.list, 1, wx.EXPAND)
        self.SetSizer(sizer)
        
    def set_model(self, model):
        self.model = model
        self.model.Bind(gdb.EVT_GDB_UPDATE_VARS, self.on_var_update)

    def on_var_update(self, evt):
        for name in evt.data:
            if name in self.model.vars:
                self.list[name] = self.model.vars[name].data
            else:
                del self.list[name]
        evt.Skip()