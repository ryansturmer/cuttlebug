import wx
import util

class CategoryTree(wx.TreeCtrl):

    def __init__(self, parent, id=-1, style=0):
        super(CategoryTree, self).__init__(parent, id, style=style | wx.TR_HIDE_ROOT)
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
    
    def set_item_art(self, item, art, type = wx.TreeItemIcon_Normal):
        item = self.find_item(item)
        self.add_art(art)
        self.SetItemImage(item, self.art[art], type)
        
    def max_width(self):
        dc = wx.ScreenDC()
        dc.SetFont(self.GetFont())
        widths = []
        for item, depth in self.__walk_items():
            if item != self.root:
                width = dc.GetTextExtent(self.GetItemText(item))[0] + self.GetIndent()*depth
                widths.append(width)
        return max(widths) + self.GetIndent()

class Treebook(wx.Treebook):

    def __init__(self, parent, id=-1,  icons=None):
        super(Treebook, self).__init__(parent=parent, id=id)
        if icons:
            self.load_art(*icons)

    def load_art(self, *arts):
        self.art = {}
        self.image_list = wx.ImageList(16,16)
        for art in arts:
            self.art[art] = self.image_list.Add(util.get_icon(art))
        self.AssignImageList(self.image_list) 
    
    def add_page(self, page, text, icon=None):
        if icon:
            self.AddPage(page, text, imageId=self.art[icon])
        else:
            self.AddPage(page, text)

class ProjectOptionsDialog(wx.Dialog):

    def __init__(self, parent, title="Project Options", size=(600,400), project=None):
        super(ProjectOptionsDialog, self).__init__(parent, -1, title, size=size)
        self.project = project
        self.bindings = {}
        self.changed = 0

        dlg_sizer = wx.BoxSizer(wx.VERTICAL)
        
        # The Tree Book View
        self.tree = Treebook(self, -1, icons=["brick.png", "cog_edit.png", "bug.png", "layout_edit.png"])
        dlg_sizer.Add(self.tree, 1, wx.EXPAND)
   
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

        # All the preference pages
        self.create_general_panel()
        self.create_build_panel()
        self.create_debug_panel()
   
    def apply_changes(self):
        if self.project:
            for key in self.bindings:
                widget = self.bindings[key]
            
                if isinstance(widget, wx.TextCtrl):
                    self.project[key] = widget.GetValue()
    
    def on_change(self, evt):
        self.changed = 1
        self.btn_apply.Enable()

    def on_apply(self, evt):
       self.apply_changes() 

    def on_ok(self, evt):
        self.apply_changes()
        self.EndModal(self.changed)
    
    def on_cancel(self, evt):
        self.EndModal(0)

    @staticmethod
    def show(parent, project=None):
        dialog = ProjectOptionsDialog(parent, project=project)
        dialog.Centre()
        dialog.ShowModal()

    def bind(self, widget, key):
        if self.project:
            self.bindings[key] = widget
            if isinstance(widget, wx.TextCtrl):
                widget.ChangeValue(self.project[key])


    def add_panel(self, panel, text, icon=None):
        self.tree.add_page(panel, text, icon=icon)

    def create_general_panel(self):
        panel = wx.Panel(self.tree)
        self.add_panel(panel, "General", icon='layout_edit.png')

    def create_build_panel(self):

        panel = wx.Panel(self.tree, -1)
        sizer = wx.BoxSizer(wx.VERTICAL)

        box = wx.StaticBox(panel, -1, "Commands")
        group = wx.StaticBoxSizer(box, wx.VERTICAL)
        grid = wx.FlexGridSizer(1,2,8,8)
        grid.AddGrowableCol(1,1)
        
        widget = wx.TextCtrl(panel, -1)
        grid.Add(wx.StaticText(panel, -1, 'Build'), 0, wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT)
        grid.Add(widget, 0, wx.ALIGN_CENTER_VERTICAL | wx.EXPAND)
        widget.Bind(wx.EVT_TEXT,  self.on_change)
        self.bind(widget, "build.build_cmd")

        widget = wx.TextCtrl(panel, -1)
        grid.Add(wx.StaticText(panel, -1, 'Clean'), 0, wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT)
        grid.Add(widget, 0, wx.ALIGN_CENTER_VERTICAL | wx.EXPAND)
        sizer.Add(group, 0, wx.EXPAND)
        widget.Bind(wx.EVT_TEXT,  self.on_change)
        self.bind(widget, "build.clean_cmd")
        
        widget = wx.TextCtrl(panel, -1)
        grid.Add(wx.StaticText(panel, -1, 'Rebuild'), 0, wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT)
        grid.Add(widget, 0, wx.ALIGN_CENTER_VERTICAL | wx.EXPAND)
        group.Add(grid, 0, wx.EXPAND | wx.ALL, 8)
        widget.Bind(wx.EVT_TEXT,  self.on_change)
        self.bind(widget, "build.rebuild_cmd")
      
        panel.SetSizer(util.padded(sizer, 8))
        self.add_panel(panel,"Build", icon='brick.png')


    def create_debug_panel(self):
        panel = wx.Panel(self.tree, -1)
        sizer = wx.BoxSizer(wx.VERTICAL)

        box = wx.StaticBox(panel, -1, "Commands")
        group = wx.StaticBoxSizer(box, wx.VERTICAL)
        grid = wx.FlexGridSizer(1,2,8,8)
        grid.AddGrowableCol(1,1)
        
        widget = wx.TextCtrl(panel, -1)
        grid.Add(wx.StaticText(panel, -1, 'Target'), 0, wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT)
        grid.Add(widget, 0, wx.ALIGN_CENTER_VERTICAL | wx.EXPAND)
        sizer.Add(group, 0, wx.EXPAND)
        widget.Bind(wx.EVT_TEXT,  self.on_change)
        self.bind(widget, "debug.target")

         
        widget = wx.TextCtrl(panel, -1)
        grid.Add(wx.StaticText(panel, -1, 'Attach Command'), 0, wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT)
        grid.Add(widget, 0, wx.ALIGN_CENTER_VERTICAL | wx.EXPAND)
        group.Add(grid, 0, wx.EXPAND | wx.ALL, 8)
        widget.Bind(wx.EVT_TEXT,  self.on_change)
        self.bind(widget, "debug.attach_cmd")
        
        panel.SetSizer(util.padded(sizer, 8))
        self.add_panel(panel,"Debug", icon='bug.png')


if __name__ == "__main__":
    app = wx.App()
    frame = wx.Frame(None)
    ProjectOptionsDialog.show(frame)
