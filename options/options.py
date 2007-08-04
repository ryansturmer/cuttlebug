import wx
import util
import os
class OptionsEvent(wx.PyEvent):
    def __init__(self, type, object=None):
        super(OptionsEvent, self).__init__()
        self.SetEventType(type.typeId)
        self.SetEventObject(object)

EVT_OPTION_CHANGED = wx.PyEventBinder(wx.NewEventType())

class Tree(wx.TreeCtrl):
    '''
    Just a wx.TreeCtrl but with better handling of icons and functions for easily fetching tree items and their data members
    '''
    def __init__(self, parent, id=-1, style=0):
        super(Tree, self).__init__(parent, id, style=style | wx.TR_HIDE_ROOT)
        #self.SetQuickBestSize(False)
        self.clear()
        self.clear_art()

    def clear_art(self):
        self.art = {}
        self.image_list = wx.ImageList(16,16)
        self.SetImageList(self.image_list) 
    
    def get_art(self, name):
        il = self.GetImageList()
        return il.GetBitmap(self.art[name])

    def add_art(self, *arts):
        for art in arts:
            if art not in self.art:
                self.art[art] = self.image_list.Add(util.get_icon(art))
                self.SetImageList(self.image_list)

    def clear(self):
        self.best_size = None
        self.DeleteAllItems()
        self.root = self.AddRoot("root")
    
    def depth(self):
        return max(zip(*self.__walk_items())[1])

    def __iter__(self):
        return iter(self.get_items())

    def __walk_items(self, item=None, depth=0):
        '''
        Return all the items in this tree, preorder traversal
        '''
        items = []
        item = item or self.root

        # Preorder traversal, add this item, then worry about children
        items.append((item, depth))

        # Base case, no more children
        child, cookie= self.GetFirstChild(item)
        while child.IsOk():
            items.extend(self.__walk_items(child, depth+1))
            child, cookie = self.GetNextChild(item, cookie)

        return items

    def get_items(self):
        return zip(*self.__walk_items())[0]

    def find_item(self, data):
        for item in self.get_items():
            if self.GetItemPyData(item) == data:
                return item
        raise IndexError("Item not found in tree.")

    def add_item(self, item, name=None, parent=None, icon=None):
         
        name = name or str(item)

        if parent is not None:
            try:
                parent = self.find_item(parent)
            except IndexError:
                raise  ValueError("Parent item not found in tree.")
        else:
            parent = self.root

        # Actually install the item
        node = self.AppendItem(parent, name)
        self.SetItemPyData(node, item)
        if icon is not None:
            self.set_item_art(item, icon)
       
        self.compute_best_size()
        return node
    
    def compute_best_size(self):
        if os.name == 'nt':
            best_size = (self.__max_width_win32(), -1)
        else:
            best_size = (self.__max_width(), -1)
        self.SetMinSize(best_size)
    
    def __max_width_win32(self):
        dc = wx.ScreenDC()
        dc.SetFont(self.GetFont())
        widths = []
        for item, depth in self.__walk_items():
            if item != self.root:
                width = dc.GetTextExtent(self.GetItemText(item))[0] + self.GetIndent()*depth
                widths.append(width)
        return max(widths) + self.GetIndent()

    def __max_width(self):
        self.Freeze()
        expanded = {}
        for item in self.get_items():
            if item is not self.root:
                expanded[item] = self.IsExpanded(item)
        self.ExpandAll()
        best_size = self.GetBestSize()
        for item in expanded:
            if not expanded[item]: self.Collapse(item)
        self.Thaw()
        return best_size[0]

    def set_item_art(self, item, art, type = wx.TreeItemIcon_Normal):
        item = self.find_item(item)
        self.add_art(art)
        self.SetItemImage(item, self.art[art], type)
        
class TreeBook(wx.Panel):

    def __init__(self, *args, **kwargs):
        super(TreeBook, self).__init__(*args, **kwargs)
        self.tree = Tree(self, style=wx.TR_SINGLE | wx.TR_HAS_BUTTONS)
        self.empty_panel = wx.Panel(self)
        self.current_panel = self.empty_panel
        
        self.sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.sizer.Add(self.tree, 0, wx.EXPAND)
        self.sizer.Add(self.empty_panel, 1, wx.EXPAND)
        self.SetSizer(self.sizer)
        self.tree.Bind(wx.EVT_TREE_SEL_CHANGED, self.on_sel_changed)

    def add_panel(self, panel,name, parent=None, icon=None):
        node = self.tree.add_item(panel, name=name, parent=parent, icon=icon)
        self.Freeze()
        self.sizer.Add(panel, 1, wx.EXPAND)
        panel.Hide()
        self.Layout()
        #if self.current_panel == self.empty_panel:
        #    self.tree.SelectItem(node, True)
        self.Thaw()

    def __show_panel(self, panel):
        self.Freeze()
        self.current_panel.Hide()
        panel.Show()
        self.Layout()
        self.Thaw()
        self.current_panel = panel

    def on_sel_changed(self, evt):
        panel = self.tree.GetItemPyData(evt.GetItem())
        self.__show_panel(panel)

class OptionsTreeBook(TreeBook):
    def __init__(self, parent, *args, **kwargs):
        super(OptionsTreeBook, self).__init__(parent, *args, **kwargs)
        self.parent = parent

    def bind(self, widget, key):
        if self.parent:
            self.parent.bind(widget, key)

class OptionsPanel(wx.Panel):

    def __init__(self, parent, name="Unnamed"):
        wx.Panel.__init__(self, parent.book, -1)
        self.name = name
        self.groups = {}
        self.parent = parent
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(util.padded(self.sizer,8))

    def add(self, group, label, widget, key=None, label_on_right=False):
        import widgets
        if group not in self.groups:
            print self.groups
            box = wx.StaticBox(self, -1, group)
            group_sizer = wx.StaticBoxSizer(box, wx.VERTICAL)
            grid = wx.FlexGridSizer(1,2,8,8)
            grid.AddGrowableCol(1,1)
            self.sizer.Add(group_sizer, 0, wx.EXPAND)
            group_sizer.Add(grid, 0, wx.EXPAND | wx.ALL, 8)
            self.groups[group] = grid

        if isinstance(widget, widgets.OptionsWidget):
            w = widget
        else:
            w = widget(self, -1)
        w.Bind(EVT_OPTION_CHANGED, self.on_change)
        if key:
            self.bind(w, key)

        if label_on_right:
            self.groups[group].Add(w, 0, wx.ALIGN_CENTER_VERTICAL | wx.EXPAND)
            self.groups[group].Add(wx.StaticText(self, -1, str(label)), 0, wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT)
        else:
            self.groups[group].Add(wx.StaticText(self, -1, str(label)), 0, wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT)
            self.groups[group].Add(w, 0, wx.ALIGN_CENTER_VERTICAL | wx.EXPAND)

    def on_change(self, evt):
        self.parent.change()

    def bind(self, widget, key):
        if self.parent:
            self.parent.bind(widget, key)
                
class OptionsDialog(wx.Dialog):
    def __init__(self, parent, title="Options", size=(600,400), icons=[], data=None):
        super(OptionsDialog, self).__init__(parent, -1, title=title, size=size)
        self.bindings = {}
        self.data = data
        self.changed = False
        dlg_sizer = wx.BoxSizer(wx.VERTICAL)

        self.book = OptionsTreeBook(self, -1)
        dlg_sizer.Add(self.book, 1, wx.EXPAND)

         # The OK/Cancel/Apply buttons at the bottom
        panel = wx.Panel(self, -1)
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.AddStretchSpacer(1)
        
        self.btn_cancel = util.button(panel, "Cancel", self.on_cancel)
        sizer.Add(util.padded(self.btn_cancel, 8), 0, wx.ALIGN_RIGHT)
        
        self.btn_apply = util.button(panel, "Apply", self.on_apply)
        self.btn_apply.Disable()
        sizer.Add(util.padded(self.btn_apply, 8), 0, wx.ALIGN_RIGHT)
        
        self.btn_ok = util.button(panel, "Ok", self.on_ok)
        sizer.Add(util.padded(self.btn_ok, 8), 0, wx.ALIGN_RIGHT)
        
        panel.SetSizer(sizer)
        
        dlg_sizer.Add(panel, 0, wx.EXPAND)
        self.SetSizer(dlg_sizer)

    def change(self):
        self.changed = True
        self.btn_apply.Enable()

    def add_panel(self, page, parent=None, icon=None):
        self.book.add_panel(page, page.name, parent=parent, icon=icon)

    def on_apply(self, evt):
       self.apply_changes()

    def on_ok(self, evt):
        self.apply_changes()
        self.EndModal(self.changed)
    
    def on_cancel(self, evt):
        self.EndModal(0)

    def apply_changes(self):
        if self.data:
            for key in self.bindings:
                widget = self.bindings[key]
                self.data[key] = widget.get_value()
        self.btn_apply.Disable()

    def bind(self, widget, key):
        if self.data:        
            self.bindings[key] = widget
            widget.set_value(self.data[key])
    
    @classmethod
    def show(cls, parent, data=None):
        dialog = cls(parent, data=data)
        dialog.Centre()
        dialog.ShowModal()
