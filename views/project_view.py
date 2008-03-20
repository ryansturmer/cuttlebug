import wx
import view, project, util, icons , menu
import os, shutil
#TODO selectable hiding of certain file extensions (from project settings)
#TODO renaming of files
#TODO close all project files when closing a project
#TODO fix kookiness in the modification of project attributes (save isn't always prompted, confirmation is broken, et al)

class ProjectViewEvent(view.ViewEvent): pass

EVT_PROJECT_DCLICK_FILE = wx.PyEventBinder(wx.NewEventType())

MNU_PROJECT = 0
MNU_FILE = 1
MNU_FILES = 2

ITEM_ROOT = 0
ITEM_FILES = 1

class ProjectView(view.View):

    def __init__(self, *args, **kwargs):
        super(ProjectView, self).__init__(*args, **kwargs)
        self.tree = ProjectTree(self, -1)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.tree, 1, wx.EXPAND)
        self.SetSizer(sizer)
        self.SetSize((200,-1))
        self.setup_menus()        
        self.tree.Bind(wx.EVT_LEFT_DCLICK, self.on_left_dclick)
        self.tree.Bind(wx.EVT_RIGHT_DOWN, self.on_right_click)
        self.tree.Bind(wx.EVT_KEY_DOWN, self.on_key)
        self.selected_file = ''
        self.selected_item = None
        
    def on_key(self, evt):
        item = self.tree.GetSelection()
        print item
        evt.Skip()
        
    def on_left_dclick(self, evt):
        pt = evt.GetPosition()
        item, flags = self.tree.HitTest(pt)
        if item and item.IsOk():
            path = self.tree.GetPyData(item)
            if path:
                if os.path.isfile(path):
                    evt = ProjectViewEvent(EVT_PROJECT_DCLICK_FILE, self, data=path)
                    wx.PostEvent(self, evt)
                elif os.path.isdir(path):
                    self.tree.Expand(item)
            else:
                self.tree.Expand(item)
        
    def setup_menus(self):
        manager = menu.MenuManager()
        pmenu = manager.menu()
        pmenu.item("Open in shell", icon='application_osx_terminal.png', show=(MNU_FILE, MNU_FILES), hide=(MNU_PROJECT,), func=self.on_open_in_shell)
        pmenu.item("Rename...", show=(MNU_FILE, MNU_PROJECT), hide=(MNU_FILES), func=self.on_rename, icon='textfield_rename.png')
        pmenu.item("Delete", show=(MNU_FILE), hide=(MNU_FILES, MNU_PROJECT), func=self.on_remove_file, icon='delete.png')
        pmenu.separator()
        pmenu.item("Create File...", show=MNU_FILES, hide=(MNU_FILE, MNU_PROJECT), func=self.on_new_file, icon='page_white_text.png')
        pmenu.item("Create Folder...", show=MNU_FILES, hide=(MNU_FILE, MNU_PROJECT), func=self.on_new_folder, icon='folder_add.png')
        pmenu.item("Refresh", show=MNU_FILES, hide=(MNU_FILE, MNU_PROJECT), func=self.on_refresh, icon='arrow_refresh.png')
        self.menu_manager = manager
        self.context_menu = pmenu
        
    def on_new_file(self, evt):
        filename = util.get_text(self.controller.frame, "Enter new filename:", title="New File...")
        if filename:
            fp = open(os.path.join(self.project.directory, filename), 'w')
            fp.close()
            self.tree.update_file_tree()

    def on_new_folder(self, evt):
        foldername = util.get_text(self.controller.frame, "Enter new folder name:", title="New Folder...")
        if foldername:
            import shutil
            os.mkdir(os.path.join(self.project.directory, foldername))
            self.tree.update_file_tree()
            
    def on_remove_file(self, evt):
        if self.selected_file:
            try:
                shutil.rmtree(self.selected_file)
            except OSError:
                os.remove(self.selected_file)
        self.update()
    
    def set_project(self, project):
        self.project = project
        self.tree.set_project(project)

    def show_backups(self, show):
        self.tree.show_backups(show)

    def update(self):
        self.tree.update()
    
    def on_right_click(self, evt):
        pt = evt.GetPosition()
        item, flags = self.tree.HitTest(pt)
        if item and item.IsOk():
            self.selected_item = item
            self.tree.SelectItem(item)
            if item == self.tree.files_item:
                self.menu_manager.publish(MNU_FILES)
                self.selected_file = os.path.split(self.tree.project.filename)[0]
            elif item == self.tree.root_item:
                self.menu_manager.publish(MNU_PROJECT)
            else:
                self.menu_manager.publish(MNU_FILE)
                self.selected_file = self.tree.GetPyData(item)
            self.tree.PopupMenu(self.context_menu.build(self.tree))
            
    def on_open_in_shell(self, evt):
        if self.selected_file:
            util.launch(self.selected_file)
            
    def on_rename(self, evt):
        if self.selected_item == self.tree.root_item:
            name = util.get_text(self.controller.frame, "Enter new name for project '%s':" % self.project.general.project_name, title="Rename Project", default=self.project.general.project_name)
            if name != None:
                self.project.general.project_name = name
        else:
            print "RENAMING OF FILES NOT YET SUPPORTED"
        self.tree.update()
    
    def on_refresh(self, evt):
        self.update()
            
    def save_state(self):
        return self.tree.save_state()
    
    def load_state(self, state):
        self.tree.load_state(state)
        
    def update(self):
        self.tree.update_file_tree()
        
class ProjectTree(wx.TreeCtrl):

    def __init__(self, parent, id):
        super(ProjectTree, self).__init__(parent, id)
        self.files_item = None
        self.art = {}
        self.icon_bindings = {}
        self.files = {}
        self.image_list = wx.ImageList(16,16)
        self.SetImageList(self.image_list)
        self.set_project(None)
        self.backups_visible = False
        self.Bind(wx.EVT_TREE_ITEM_GETTOOLTIP, self.on_get_tooltip)

    def on_get_tooltip(self, evt):
        item = evt.GetItem()
        if item == self.root_item:
            if self.project:
                evt.SetToolTip(self.project.directory)
                return
            
        data = self.GetPyData(item)
        try:
            stat = os.stat(data)
            evt.SetToolTip(data + "\n" + util.human_size(stat.st_size))
        except:
            pass
    def show_backups(self, show):
        self.backups_visible = bool(show)

    def set_project(self, project):
        self.project = project
        if project:
            self.clear()
            self.root_item = self.AddRoot(project.general.project_name)
            self.SetItemImage(self.root_item, 'package.png')
            self.files_item = self.AppendItem(self.root_item, "Files")
            self.SetItemImage(self.files_item, "folder.png")
            self.update_file_tree()
        else:
            self.clear()

    def walk(self, top_item, include_root=True):
        retval = [top_item] if include_root else []
        child, cookie = self.GetFirstChild(top_item)
        while child.IsOk():
             retval.extend(self.walk(child))
             child, cookie = self.GetNextChild(top_item, cookie)
        return retval
    
    def get_file_icon(self, filename):
        fn, ext = os.path.splitext(filename)
        return self.icon_bindings.get(ext.lower(), 'file_white.png')

        
    def bind_icon(self, extension, icon):
        self.add_art(icon)
        self.icon_bindings[str(extension).lower()] = icon

    def add_art(self, *arts):
        for art in arts:
            if art not in self.art:
                bmp = util.get_icon(art)
                self.art[art] = self.image_list.Add(bmp)
        self.SetImageList(self.image_list)

    def clear(self):
        self.files = {}
        self.DeleteAllItems()

    def SetItemImage(self, item, name, style=wx.TreeItemIcon_Normal):
        if name not in self.art:
            self.add_art(name)
        super(ProjectTree, self).SetItemImage(item, self.art[name], style)

    def add_file(self, file, icon):
        if file in self.files:
            return
        parent, fn = os.path.split(file)
        parent_item = self.files[parent]

        item = self.AppendItem(parent_item, fn)
        self.SetPyData(item, file)
        self.files[file] = item
        self.SetItemImage(item, icon)
        self.SortChildren(parent_item)

    def update_file_tree(self):
        #TODO sort files
        if not self.project:
            return
        self.Freeze()
        self.files[self.project.directory] = self.files_item

        # Remove any file/folder items that no longer exist
        for item in self.walk(self.files_item, False):
            path = self.GetPyData(item)
            try:
                os.stat(path)
            except:
                del self.files[path]
                self.Delete(item)
                
        # Add any file/folder items that aren't currently in the tree
        for root, dirs, files in os.walk(self.project.directory):
            if root not in self.files:
                parent, dir = os.path.split(root)
                if dir.startswith("."):
                    self.add_file(root, 'folder_wrench.png')
                else:
                    self.add_file(root, 'folder.png')
            #print self.files
            for file in files:
                #print file
                if file not in self.files:
                    if not self.backups_visible and file.endswith("~"):
                        continue
                    self.add_file(os.path.join(root, file), icons.get_file_icon(file))
        self.Thaw()

    def save_state(self):
        state = set()
        if self.IsExpanded(self.root_item): state.add(ITEM_ROOT)
        if self.IsExpanded(self.files_item): state.add(ITEM_FILES)
        for item in self.walk(self.files_item, include_root=False):
            if self.IsExpanded(item):
                state.add(self.GetPyData(item))
        return state
        
    def load_state(self, state):
        self.Freeze()
        if ITEM_ROOT in state:
            self.Expand(self.root_item)
        if ITEM_FILES in state:
            self.Expand(self.files_item)
        for item in self.walk(self.files_item, include_root=False):
            if self.GetPyData(item) in state:
                self.Expand(item)
        self.Thaw() 
        
    def update(self):
        self.SetItemText(self.root_item, self.project.general.project_name)
        self.update_file_tree()

