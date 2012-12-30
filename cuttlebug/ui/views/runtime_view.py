import view
import wx
import wx.gizmos as gizmos
from cuttlebug.ui.controls import DictListCtrl
from cuttlebug.util import ArtListMixin, has_icon, bidict, KeyTree, str2int
from functools import partial
import cuttlebug.gdb as gdb
import os, threading
import cuttlebug.ui.menu as menu
import cuttlebug.settings as settings
import cuttlebug.project as project
import cuttlebug.ui.controls as controls

MNU_ENABLE_BKPT = 0
MNU_DISABLE_BKPT = 1
class RuntimeTree(gizmos.TreeListCtrl, ArtListMixin, KeyTree):
    def __init__(self, parent):
        self.parent = parent
        gizmos.TreeListCtrl.__init__(self, id=-1, parent=parent, style=wx.TR_DEFAULT_STYLE  | wx.TR_FULL_ROW_HIGHLIGHT | wx.TR_HIDE_ROOT | wx.TR_HAS_BUTTONS | wx.TR_LINES_AT_ROOT | wx.TR_EDIT_LABELS)
        ArtListMixin.__init__(self)
        KeyTree.__init__(self)
        self.SetFont(wx.Font(8, wx.FONTFAMILY_MODERN, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
        self.parent = parent
        self.Bind(wx.EVT_TREE_ITEM_EXPANDING, self.on_expanding)
        self.Bind(wx.EVT_TREE_ITEM_GETTOOLTIP, self.on_get_tooltip)
        self.Bind(wx.EVT_TREE_BEGIN_LABEL_EDIT, self.on_begin_label_edit)
        self.Bind(wx.EVT_TREE_END_LABEL_EDIT, self.on_end_label_edit)
        self.Bind(wx.EVT_TREE_SEL_CHANGED, self.on_select_item)
        #self.Bind(wx.EVT_LEFT_DOWN, self.on_left_down)
        self.Bind(wx.EVT_LEFT_DCLICK, self.on_dclick)
        self.Bind(wx.EVT_TREE_ITEM_ACTIVATED, self.on_dclick) 
        self.Bind(wx.EVT_TREE_ITEM_RIGHT_CLICK, self.on_item_right_click)
        self.Bind(wx.EVT_LIST_COL_END_DRAG, self.on_col_resize)

        self.model = None
        self.AddColumn('Context')
        self.AddColumn('Value')      
        self.SetColumnEditable(1, True)
        self.SetColumnAlignment(1, wx.ALIGN_RIGHT)
        self.lock = threading.RLock()
        self.__var_idx = 0
        self.create_popup_menus()
        self.clear()
        self.load_positions()

    def on_col_resize(self, evt):
        self.save_positions()
        
    def save_positions(self):
        cols = self.GetColumnCount()
        widths = [self.GetColumnWidth(i) for i in range(cols)]
        settings.session_set('runtime_view_col_widths', widths)

    def load_positions(self):
        try:
            widths = settings.session_get('runtime_view_col_widths')
            cols = self.GetColumnCount()
            if len(widths) != cols:
                raise Exception("Mismatch of stored column widths")
            for i, width in enumerate(widths):
                self.SetColumnWidth(i, width)
        except:
            pass

    def create_popup_menus(self):
        self.menu_manager = menu.MenuManager()
        m = self.menu_manager.menu()
        m.item("Enable", func=self.on_enable_breakpoint, icon='stop.png', show=MNU_ENABLE_BKPT, hide=MNU_DISABLE_BKPT)
        m.item("Disable", func=self.on_disable_breakpoint, icon='stop_disabled.png', show=MNU_DISABLE_BKPT, hide=MNU_ENABLE_BKPT)
        m.item("Remove", func=self.on_remove_breakpoint, icon='ex.png')
        self.menu_breakpoint_item = m
        
        m = self.menu_manager.menu()
        m.item("Enable All Breakpoints", func=self.on_enable_all_breakpoints, icon='stop.png')
        m.item("Disable All Breakpoints", func=self.on_disable_all_breakpoints, icon='stop_disabled.png')
        m.item("Remove All Breakpoints", func=self.on_remove_all_breakpoints, icon='ex.png')
        self.menu_breakpoints = m
        
        m = self.menu_manager.menu()
        m.item("Show this Frame in Source", func=self.on_show_frame, icon='find.png')
        m.step_out = m.item("Step Out\tShift+F6", func=self.on_step_out, icon='control_play_blue.png')
        self.menu_frame_item = m
        
        m = self.menu_manager.menu()
        m.item("Add Watch...", func=self.on_add_watch, icon='magnifier_zoom_in.png')
        self.menu_watches = m

        m = self.menu_manager.menu()
        m.item("Remove Watch", func=self.on_remove_watch, icon='ex.png')
        self.menu_watch_item = m
                
    def set_model(self, model):
        self.model = model
        self.model.Bind(gdb.EVT_GDB_UPDATE_VARS, self.on_var_update)
        self.model.Bind(gdb.EVT_GDB_UPDATE_STACK, self.on_stack_update)
        self.model.Bind(gdb.EVT_GDB_UPDATE_BREAKPOINTS, self.on_breakpoint_update)
        self.model.Bind(gdb.EVT_GDB_UPDATE_REGISTERS, self.on_register_update)
        self.model.Bind(gdb.EVT_GDB_FINISHED, self.on_gdb_finished)
        self.model.Bind(gdb.EVT_GDB_STOPPED, self.on_gdb_stopped)
        wx.CallAfter(self.build_sfr_tree)

    def get_var_name(self):
        name = "rtv_%d" % self.__var_idx
        self.__var_idx += 1
        return name 

    def on_breakpoint_update(self, evt):
        wx.CallAfter(self.update_breakpoints)
        
    def on_register_update(self, evt):
        wx.CallAfter(self.update_registers, evt.data)
        self.save_positions()

    def on_var_update(self, evt):
        names = evt.data
        for name in names:
            if name in self.pending_var_additions:
                self.lock.acquire()
                parent = self.pending_var_additions.pop(name)
                self.lock.release()
                wx.CallAfter(self.add_var_item, parent, name, self.model.vars[name])
                if parent == self.watch_item:
                    self.expand(self.watch_item)
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

    def on_stack_update(self, evt):
        #print self.model.stack.pretty()
        if self.model:
            if self.__check_stack():
                wx.CallAfter(self.update_stack)
            else:
                wx.CallAfter(self.rebuild_stack)                
        evt.Skip()
        
    def on_gdb_finished(self, evt):
        self.clear()
        self.model = None    
        
    def on_item_right_click(self, evt):
        item = self.__get_evt_item(evt)
        if item.is_ok():        
            self.select_item(item)
            if self.model:
                if item == self.breakpoints_item and self.get_children_count(self.breakpoints_item) > 0:
                    self.PopupMenu(self.menu_breakpoints.build(self), evt.GetPoint())
                elif self.is_descendent(item, self.breakpoints_item):
                    bkpt = self.get_item_data(item)
                    self.breakpoint = bkpt
                    self.menu_manager.publish(MNU_DISABLE_BKPT) if bkpt.enabled else self.menu_manager.publish(MNU_ENABLE_BKPT)
                    self.PopupMenu(self.menu_breakpoint_item.build(self), evt.GetPoint())
                elif self.is_frame_item(item):
                    frame = self.get_item_data(item)
                    self.frame = frame
                    if frame.level == 0 and len(self.frames) > 1:
                        self.menu_frame_item.step_out.show()
                    else:
                        self.menu_frame_item.step_out.hide()
                        
                    self.PopupMenu(self.menu_frame_item.build(self), evt.GetPoint())
                elif item == self.watch_item:
                    self.PopupMenu(self.menu_watches.build(self), evt.GetPoint())
                elif self.is_descendent(item, self.watch_item):
                    self.selected_item = item
                    self.PopupMenu(self.menu_watch_item.build(self), evt.GetPoint())
                    
        evt.Skip()
        
    def on_dclick(self, evt):
        id = self.__get_evt_item(evt)
        if self.model and self.is_descendent(id, self.breakpoints_item):
            bkpt = self.get_item_data(id)
            if bkpt.enabled:
                self.model.break_disable(bkpt)
            else:
                self.model.break_enable(bkpt)
        elif self.model and self.is_descendent(id, self.sfr_item):
            reg = self.get_item_data(id)
            if reg:
                old_value = reg.value    
                try:
                    response = controls.RegisterEditDialog.show(self, reg)
                except Exception, e:
                    print e
                if response == wx.ID_OK:
                    self.model.data_evaluate_expression("%s=%s" % (reg.expression, reg.value), callback=partial(self.on_sfr_data, id,True))
                else:
                    reg.value = old_value
        elif self.model and self.is_descendent(id, self.registers_item):
            name = self.get_item_data(id)
            target_model = self.parent.controller.project.target
            reg = target_model.find_by_name(name)
            if not reg:
                reg = project.CPURegister(name, name, 4)
                reg.add_field(project.Field(0, 32, name))
                
            reg.value = str2int(self.register_registry[name])
            response = controls.RegisterEditDialog.show(self, reg)
            if response == wx.ID_OK:
                self.model.data_evaluate_expression("%s=%s" % (reg.expression, reg.value),callback=self.on_register_data)
        evt.Skip()                 
        
    def on_register_data(self, evt):
        self.model.update()
        
    def on_begin_label_edit(self, evt):
        item = self.get_event_item(evt)
        name = self.get_item_data(item)
        if name in self.var_registry: 
            if self.is_descendent(item, self.get_frame_items()[-1]):
                evt.Skip()
                return
        if self.is_descendent(item, self.sfr_item) or self.is_descendent(item, self.watch_item):
            evt.Skip()
            return
        evt.Veto()
            
    def on_select_item(self, evt):
        #item = self.get_event_item(evt)
        #print self.get_item_data(item)
        evt.Veto()
        #evt.Skip()
        
    def on_end_label_edit(self, evt):
        item = self.get_event_item(evt)
        name = self.get_item_data(item)
        if name in self.var_registry and name in self.model.vars:
            new_var_value = evt.GetLabel()
            self.model.var_assign(name, new_var_value)
        if self.is_descendent(item, self.sfr_item) or self.is_descendent(item, self.watch_item):
            reg = self.get_item_data(item)
            if hasattr(reg, 'expression'):
                self.model.data_evaluate_expression('%s=%s' % (reg.expression, evt.GetLabel()), callback=partial(self.on_sfr_data, item,True))
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
                
        if self.is_descendent(item, self.sfr_item):
            self.update_sfr_tree(item, force_root=True, colorize=False)
            return
        
        if hasattr(item_data, 'level') and self.get_children_count(item, False) == 0: #item_data is a stack frame, and we wish to list its locals
            if not self.model.running:
                self.model.stack_list_arguments(frame=item_data.level, callback=partial(self.__on_listed_arguments, item))
            else:
                evt.Veto()
        elif item_data in self.var_registry and self.get_children_count(item, False) == 0:
            if not self.model.running:
                self.model.var_list_children(item_data, callback=partial(self.__on_listed_children, item))
            else:
                evt.Veto()
        evt.Skip()
        
    def __on_listed_children(self, parent, result):

        names = []
        if hasattr(result, 'children'):
            for child in result.children:
                varname= child['child']['name']
                self.lock.acquire()
                self.pending_var_additions[varname] = parent
                self.lock.release()
                names.append(varname)
        class Dummy(object): pass
        evt = Dummy()
        evt.data = names
        wx.CallAfter(self.on_var_update, evt)
        
    def __on_listed_locals(self, frame_item, args, result):
        if result.cls != 'error':
            if hasattr(result, 'locals') and frame_item.is_ok():
                frame = self.get_item_data(frame_item)
                if self.get_children_count(frame_item, recursive=False) == 0:
                    for item in args + result.locals:
                        varname = self.get_var_name()
                        self.lock.acquire()
                        self.pending_var_additions[varname] = frame_item
                        self.lock.release()
                        self.model.var_create(item['name'], frame=frame.level, callback=self.__on_created_var, name=varname)

    def __on_listed_arguments(self, frame_item, result):
        if result.cls != 'error':
            if 'stack-args' in result and frame_item.is_ok():
                frame = self.get_item_data(frame_item)
                f = result['stack-args'][frame.level]['frame']
                if int(f['level']) != frame.level:
                    raise ValueError("Failed Sanity Check!")
                args =  f['args']
                self.model.stack_list_locals(frame=frame.level, callback=partial(self.__on_listed_locals, frame_item, args))
                
    def __on_created_var(self, result):
        if hasattr(result, 'name'):
            self.model.var_update(result.name)

            
    def add_var_item(self, parent, name, var):
        if parent.is_ok():
            var_item = self.append_item(parent, var.expression.strip('"'))
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
            
    def add_watch(self, s):
        vn = self.get_var_name()
        self.lock.acquire()
        self.pending_var_additions[vn] = self.watch_item
        self.lock.release()
        self.model.var_create(s, floating=True, callback=self.__on_created_var, name=vn)

    def on_add_watch(self, evt):
        dlg = wx.TextEntryDialog(self, "Watch Variable", self.last_watch)
        if dlg.ShowModal() == wx.ID_OK:
            var = dlg.GetValue().strip()
            self.add_watch('"%s"' % var) # Quoting the watch allows spaces
            
    def on_remove_watch(self, evt):
        item = self.get_item_data(self.selected_item)
        self.model.var_delete(item, callback=partial(self.on_watch_deleted, self.selected_item))
    def on_watch_deleted(self, watch_item, evt):
        self.delete(watch_item)

    def scrub_vars(self, all_vars=False):
        #TODO use a list
        to_update = {}        
        if self.get_frame_count() > 0:
            frame_items = self.get_frame_items()
            for name, var_item in self.var_registry.iteritems():
                if (not self.is_descendent(var_item, frame_items[-1]) or all_vars) and name in self.model.vars:
                    var = self.model.vars[name]
                    frame = self.get_var_frame(name)
                    if frame:
                        varname = self.get_var_name()
                        to_update[(name, varname)] = (frame, var)
                        self.pending_var_updates[varname] = var_item
                            
            for (old_name, new_name), (frame, var)in to_update.iteritems(): 
                self.model.var_delete(old_name)
                self.model.var_create(var.expression, frame=frame.level, callback=self.__on_created_var, name=new_name)

    def get_frame_items(self):
        return list(self.children(self.stack_item)) if self.stack_item.is_ok() else []
    
    def get_frames(self):
        return [self.get_item_data(frame_item) for frame_item in self.get_frame_items()]
    
    def get_frame_count(self):
        if self.stack_item.is_ok():
            return self.get_children_count(self.stack_item, recursive=False)
        else:
            return 0     
            
    def is_frame_item(self, item):
        return item.is_ok() and isinstance(self.get_item_data(item), gdb.GDBStackFrame)
    
    def add_frame_item(self, frame):
        item = self.append_item(self.stack_item, frame.func + "( )")
        self.update_frame_item(item, frame)
        
    def update_frame_item(self, frame_item, frame):
        self.set_item_data(frame_item, frame)
        self.set_item_art(frame_item, 'frame.png' if frame.level != 0 else 'frame_active.png')
        self.set_item_has_children(frame_item, True)
        self.set_item_bold(frame_item, True)
        self.set_item_data(frame_item, frame)
     
    def on_show_frame(self, evt):
        if self.model and self.frame:
            self.GetParent().controller.goto(self.frame.file, self.frame.line)
            self.frame = None
            
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
            else:
                return None
        return frame
    
    def on_step_out(self, evt):
        self.parent.controller.step_out()
        
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
        frame_item = self.get_frame_items()[-1]
        if frame_item.is_ok():
            for child in self.walk(frame_item):
                name = self.get_item_data(child)
                if name in self.var_registry:
                    self.var_registry.pop(name)
                    self.model.var_delete(name)
            self.delete(frame_item)
        else:
            print "Can't remove frame.  Frame item is NOT ok."
    
                                
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

    def on_enable_breakpoint(self, evt):
        if self.breakpoint and self.model:
            self.model.break_enable(self.breakpoint)
            self.breakpoint = None
            
    def on_disable_breakpoint(self, evt):
        if self.breakpoint and self.model:
            self.model.break_disable(self.breakpoint)
            self.breakpoint = None

    def on_remove_breakpoint(self, evt):
        if self.breakpoint and self.model:
            self.model.break_delete(self.breakpoint)
            self.breakpoint = None

    def on_enable_all_breakpoints(self, evt):
        if self.model:
            for bkpt in self.model.breakpoints:
                self.model.break_enable(bkpt)
            
    def on_disable_all_breakpoints(self, evt):
        if self.model:
            for bkpt in self.model.breakpoints:
                self.model.break_disable(bkpt)

    def on_remove_all_breakpoints(self, evt):
        if self.model:
            for bkpt in self.model.breakpoints:
                self.model.break_delete(bkpt)
            
    def update_registers(self, names):
        '''
        if self.model and self.registers_item.is_ok():
            registers = self.model.registers
            if len(registers) != self.get_children_count(self.registers_item, recursive=False):
                self.delete_children(self.registers_item)
                for key, value in registers.iteritems():
                    item = self.append_item(self.registers_item, key)
                    self.set_item_text(item, value, 1)
                    self.set_item_data(item, key)
                    self.register_registry[key] = value
            else:
                for child in self.children(self.registers_item):
                    self.set_item_text_colour(child, wx.BLACK)
                    
                for name in names:
                    item = self.register_registry[name]
                    print item
                    self.set_item_text(item, registers[name], 1)
                    self.set_item_text_colour(item, wx.RED)
        '''
        
    def build_sfr_tree(self):
        if not self.parent.controller.project:
            return
        self.delete_children(self.sfr_item)
        target_model = self.parent.controller.project.target
        def walk(self, tree_item, item):
            if isinstance(item, project.Group):
                group_item = self.append_item(tree_item, item.name)
                for child in item.items:
                    walk(self, group_item, child)
            elif isinstance(item, project.Peripheral):
                peripheral_item = self.append_item(tree_item, item.name)
                for child in item.registers:
                    walk(self, peripheral_item, child)
            elif isinstance(item, project.SpecialFunctionRegister):
                sfr_item = self.append_item(tree_item, item.fullname)
                self.set_item_data(sfr_item, item)
        tree_item = self.sfr_item
        for item in target_model.items:
            walk(self, tree_item, item)     
        
    def on_gdb_stopped(self, evt):
        self.update_sfr_tree(self.sfr_item)
        evt.Skip()
        
    def update_sfr_tree(self, sfr_item, force_root=False, colorize=True):
        if force_root: 
            items = self.children(sfr_item)
        else:
            items = [sfr_item]
        
        for i in items:
            for tree_item in self.walk_expanded(i, False):
                item = self.get_item_data(tree_item)
                if hasattr(item, 'expression'):
                    self.model.data_evaluate_expression(item.expression, callback=partial(self.on_sfr_data, tree_item, colorize))

    def on_sfr_data(self, item, colorize, data):
        if data.cls == "done" and hasattr(data, 'value'):
            wx.CallAfter(self.update_sfr_value, item, data.value, colorize)
    
    def update_sfr_value(self, item, value, colorize=True):
        current_value = self.get_item_text(item, 1)
        try:
            reg = self.get_item_data(item)
            reg.value = int(value)
            text = "0x%08x" % int(value)
        except:
            text = value
            
        self.set_item_text(item, text, 1)
        if current_value != text and colorize:
            self.set_item_text_colour(item, wx.RED)
        else:
            self.set_item_text_colour(item, wx.BLACK)
            
    def update(self):
        pass        
    
    def clear(self):
        self.last_watch = ""
        self.DeleteAllItems()
        self.root_item = self.add_root('root')
        self.stack_item = self.append_item(self.root_item,'Call Stack')
        self.breakpoints_item = self.append_item(self.root_item, 'Breakpoints')
        self.registers_item = self.append_item(self.root_item, 'CPU Registers')
        self.watch_item = self.append_item(self.root_item, 'Watch')
        self.sfr_item = self.append_item(self.root_item, 'HW Registers')
        
        self.set_item_art(self.registers_item, 'chip.png')
        self.set_item_art(self.stack_item, 'stack.png')
        self.set_item_art(self.breakpoints_item, 'breakpoint.png')
        self.set_item_art(self.watch_item, 'magnifier.png')
        self.set_item_art(self.sfr_item, 'application_view_list.png')
        
        self.lock.acquire()
        self.frames = [] # Frame keys to tree items
        self.var_registry = bidict() # Var names to tree items
        self.pending_var_additions = {}
        self.pending_var_updates = {}
        self.register_registry = bidict()
        self.lock.release()
        self.breakpoint = None
        
    def __get_evt_item(self, evt):
        item = evt.GetItem()
        if item and item.IsOk():
            try:
                return self.get_key(item)
            except:
                return None
            
        pt = evt.GetPosition()
        items = self.HitTest(pt)
        try:
            return self.get_key(items[0])
        except:
            return None
        
    def set_item_art(self, item, name, style=wx.TreeItemIcon_Normal):
        if name not in self.art:
            self.add_art(name)
        if item.is_ok():
            self.set_item_image(item, self.art[name], style)
        else:
            print "Tried to set art for item that's NOT ok?"
        
        
            
class RuntimeView(view.View):
    
    def __init__(self, *args, **kwargs):
        super(RuntimeView, self).__init__(*args, **kwargs)
        self.tree = RuntimeTree(self)
#      self.tree.Bind(wx.EVT_KEY_DOWN, self.tree.on_key_down)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.tree, 1, wx.EXPAND)
        self.SetSizer(sizer)
  
    def set_model(self, model):
        self.tree.set_model(model)
        
    def update(self, stack):
        self.tree.update()
        
    def add_watch(self, s):
        self.tree.add_watch(s)
        
class GDBDebugView(view.View):
    def __init__(self, *args, **kwargs):
        super(GDBDebugView, self).__init__(*args, **kwargs)
        self.list = DictListCtrl(self, color_changes=False)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.list, 1, wx.EXPAND)
        self.SetSizer(sizer)
        
    def set_model(self, model):
        self.model = model
        print "Binding the var update"
        self.model.Bind(gdb.EVT_GDB_UPDATE_VARS, self.on_var_update)

    def on_var_update(self, evt):
        for name in evt.data:
            if name in self.model.vars:
                self.list[name] = self.model.vars[name].data
            else:
                del self.list[name]
        evt.Skip()