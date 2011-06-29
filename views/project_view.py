import wx
import view, util, icons , menu, file_tree
import os, shutil, pickle
#TODO selectable hiding of certain file extensions (from project settings)
#TODO renaming of files
#TODO close all project files when closing a project
#TODO fix kookiness in the modification of project attributes (save isn't always prompted, confirmation is broken, et al)

class ProjectViewEvent(view.ViewEvent): pass

EVT_PROJECT_DCLICK_FILE = wx.PyEventBinder(wx.NewEventType())

MNU_PROJECT = 0
MNU_FILE = 1
MNU_FILES = 2
MNU_FOLDER = 4

ITEM_ROOT = 0
ITEM_FILES = 1

SORT_ALPHA = 0
SORT_EXTENSION = 1

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
        pmenu.item("Create File...", show=(MNU_FILES, MNU_FOLDER), hide=(MNU_FILE, MNU_PROJECT), func=self.on_new_file, icon='page_white_text.png')
        pmenu.item("Create Folder...", show=(MNU_FILES,MNU_FOLDER), hide=(MNU_FILE, MNU_PROJECT), func=self.on_new_folder, icon='folder_add.png')
        pmenu.item("Import File...", show=(MNU_FILES, MNU_FOLDER), hide=(MNU_FILE, MNU_PROJECT), func=self.on_import_file)
        pmenu.item("Refresh", show=(MNU_FILES, MNU_FOLDER), hide=(MNU_FILE, MNU_PROJECT), func=self.on_refresh, icon='arrow_refresh.png')
        sm = pmenu.submenu("Sort By...", show=(MNU_FILES, MNU_FOLDER), hide=(MNU_FILE, MNU_PROJECT))
        sm.item("Name", func=self.on_sort_alpha)
        sm.item("Extension", func=self.on_sort_extension)

        self.menu_manager = manager
        self.context_menu = pmenu
        
    def on_import_file(self, evt):
        pass
    
    def on_sort_extension(self, evt):
        self.tree.set_sort_method(SORT_EXTENSION)
    def on_sort_alpha(self, evt):
        self.tree.set_sort_method(SORT_ALPHA)
        
    def on_new_file(self, evt):
        filename = util.get_text(self.controller.frame, "Enter new filename:", title="New File...")
        if os.path.isdir(self.selected_file):
            dir = self.selected_file
        elif os.path.isfile(path):
            dir = os.path.split(self.selected_file)[0]
        if filename and dir:
            fp = open(os.path.join(dir, filename), 'w')
            fp.close()
            self.tree.update_file_tree()

    def on_new_folder(self, evt):
        print self.selected_file
        foldername = util.get_text(self.controller.frame, "Enter new folder name:", title="New Folder...")
        if foldername:
            os.mkdir(os.path.join(self.project.directory, foldername))
            self.tree.update_file_tree()
            
    def on_remove_file(self, evt):
        base, fn = os.path.split(self.selected_file)
        if self.tree.confirm("Are you sure you want to remove the file '%s'?" % fn):
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
                self.selected_file = self.tree.GetPyData(item)
                if os.path.isfile(self.selected_file):
                    self.menu_manager.publish(MNU_FILE)
                elif os.path.isdir(self.selected_file):
                    self.menu_manager.publish(MNU_FOLDER)

            self.tree.PopupMenu(self.context_menu.build(self.tree))
        evt.Skip()
        
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
        self.tree.SetItemText(self.tree.GetRootItem(), self.project.general.project_name)
        self.tree.update_file_tree()
        
class DropData(wx.CustomDataObject):
    def __init__(self, format, data=None):
        wx.CustomDataObject.__init__(self, str(format))
        self.set_object(data)
        
    def set_object(self, obj):
        self.SetData(pickle.dumps(obj))
        
    def get_object(self):
        return pickle.loads(self.GetData())
    
class ProjectDropTarget(wx.PyDropTarget):
    def __init__(self, tree):
        wx.PyDropTarget.__init__(self)
        self.tree = tree
        self.selections = []
        self.data = DropData("FileDropData")
        self.SetDataObject(self.data)
        
        
    def save_selection(self):
        self.selections = self.tree.GetSelections()
    
    def restore_selection(self):
        self.tree.UnselectAll()
        for item in self.selections:
            self.tree.SelectItem(item)
        self.selections = []
        
    def OnEnter(self,x,y,d):
        self.save_selection()
        return d
    
    def OnLeave(self):
        self.restore_selection()

    def OnDragOver(self,x,y,d):
        item, flags = self.tree.HitTest((x,y))
        selections = self.tree.GetSelections()
        if item:
            if selections != [item]:
                self.tree.UnselectAll()
                path = self.tree.GetItemPyData(item)                
                if item == self.tree.files_item or (path in self.tree.files and os.path.isdir(path)):
                    self.tree.SelectItem(item)
        elif selections:
            self.tree.UnselectAll()
        return d    

    def OnData(self, x, y, d):
        if self.GetData():
            path_source =  self.data.get_object()
            path_target = self.path_target
            try:
                if d == wx.DragMove:
                    if self.move_file(path_source, path_target):
                        return wx.DragMove
                elif d == wx.DragCopy:
                    if self.copy_file(path_source, path_target):
                        return wx.DragCopy
            except:
                return wx.DragNone

            return wx.DragNone

    def move_file(self, path_source, path_target):
            root, fn = os.path.split(path_source)
            full_target = os.path.join(path_target, fn)
            if full_target == path_source:
                return False
            target_exists = os.path.exists(full_target)
            
            confirm = True
            if target_exists:
                confirm = self.tree.confirm("Replace '%s' in the target location?" % fn)
            if path_source and path_target and confirm:
                try:
                    if target_exists:
                        if os.path.isdir(full_target):
                            shutil.rmtree(full_target)
                        else:
                            os.remove(full_target)
                    shutil.move(path_source, path_target)
                    wx.CallAfter(self.tree.update)
                    return True
                except:
                    raise
                finally:
                    self.path_target = None
            return False
        

    def copy_file(self, path_source, path_target):
            root, fn = os.path.split(path_source)
            full_target = os.path.join(path_target, fn)
            if full_target == path_source:
                return False
            target_exists = os.path.exists(full_target)
            
            confirm = True
            if target_exists:
                confirm = self.tree.confirm("Replace '%s' in the target location?" % fn)
            if path_source and path_target and confirm:
                try:
                    if target_exists:
                        if os.path.isdir(full_target):
                            shutil.rmtree(full_target)
                        else:
                            os.remove(full_target)
                    shutil.move(path_source, path_target)
                    wx.CallAfter(self.tree.update)
                    return True
                except:
                    raise
                finally:
                    self.path_target = None
            return False
        
    def OnDrop(self,x,y):
        item, flags = self.tree.HitTest((x,y))
#        selections = self.tree.GetSelections()
        if item:
            self.tree.UnselectAll()
            path = self.tree.GetItemPyData(item)
            if item == self.tree.files_item:
                self.path_target = self.tree.project.directory
            if path in self.tree.files and os.path.isdir(path):
                self.path_target = path
            return True
        return False
        
class ProjectTree(wx.TreeCtrl):

    def __init__(self, parent, id):
        super(ProjectTree, self).__init__(parent, id, style=wx.TR_DEFAULT_STYLE)
        self.sort_method = SORT_ALPHA
        self.files_item = None
        self.art = {}
        self.icon_bindings = {}
        self.files = {}
        self.image_list = wx.ImageList(16,16)
        self.SetImageList(self.image_list)
        self.set_project(None)
        self.backups_visible = False
        self.Bind(wx.EVT_TREE_ITEM_GETTOOLTIP, self.on_get_tooltip)
        self.Bind(wx.EVT_MOTION, self.on_motion)
        self.Bind(wx.EVT_TREE_ITEM_EXPANDING, self.on_item_expanding)
        self.tooltip_flag = False
        
        dt = ProjectDropTarget(self)
        self.SetDropTarget(dt)

        self.Bind(wx.EVT_TREE_BEGIN_DRAG, self.on_begin_drag)
        
    def on_begin_drag(self, evt):
        item = evt.GetItem()
        path = self.GetItemPyData(item)
        if path in self.files:            
            data = DropData("FileDropData", path)
            source = wx.DropSource(self)
            source.SetData(data)
            result = source.DoDragDrop(wx.Drag_DefaultMove)
            
            #results = {wx.DragCopy: "DragCopy", wx.DragMove : "DragMove", wx.DragCancel : "DragCancel", wx.DragNone : "DragNone", wx.DragLink : "DragLink"}
            #print results.get(result)
            
    def on_item_expanding(self, evt):
        item = evt.GetItem()
        path = self.GetItemPyData(item)
        if path in self.files:
            self.file_tree.expand_directory(path)
            self.update_file_tree()

    def on_item_collapsing(self, evt):
        return
        item = evt.GetItem()
        path = self.GetItemPyData(item)
        if path in self.files:
            self.file_tree.collapse_directory(path)
            self.update_file_tree()
            
    def on_motion(self, evt):
        self.tooltip_flag = False 
        self.SetToolTipString('')
        evt.Skip()

    def on_get_tooltip(self, evt):
        #print "getting tooltip"
        self.tooltip_flag = True
        wx.CallLater(1000, self.set_tool_tip(evt))
        evt.Skip()
        
    def set_tool_tip(self, evt):
        item = evt.GetItem()
        if item == self.root_item:
            if self.project:
                evt.SetToolTip(self.project.directory)
        else:    
            data = self.GetPyData(item)
            try:
                stat = os.stat(data)
                evt.SetToolTip(data + "  " + util.human_size(stat.st_size))
            except:
                pass

    def confirm(self, *argc, **argv):
        return wx.GetApp().frame.confirm(*argc, **argv)
       
    def set_sort_method(self, method):
        self.sort_method = method
        state = self.save_state() # What is expanded and what isn't, etc...
        self.set_project(self.project)
        self.load_state(state)
        
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
            self.file_tree = file_tree.FileTree(project.directory)
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
        return item
    
    def OnCompareItems(self, i1, i2):
        p1 = self.GetPyData(i1)
        p2 = self.GetPyData(i2)
        if p1 in self.files and p2 in self.files:
            if self.sort_method == SORT_EXTENSION:
                return cmp(os.path.splitext(p1)[1], os.path.splitext(p2)[1])
            else:
                return cmp(self.GetItemText(i1), self.GetItemText(i2))
        else:
            return 0
        
    def update_file_tree(self):
        #TODO sort files
        if not self.project:
            return

        additions, deletions = self.file_tree.get_tree_changes()

        self.Freeze()
        self.files[self.project.directory] = self.files_item

        # Remove any file/folder items that no longer exist
        for deleted_file in deletions:
            item = self.files[deleted_file]
            self.Delete(item)
            del self.files[deleted_file]
                
        cmp_alpha = lambda x : x
        cmp_ext = lambda x :  os.path.splitext(x)[1]
        
       # methods = {SORT_ALPHA : cmp_alpha, SORT_EXTENSION : cmp_ext}
        # Add any file/folder items that aren't currently in the tree
        for root, dirs, files in self.file_tree.walk(self.project.directory):
            if root not in self.files:
                parent, d = os.path.split(root)
                if d.startswith("."):
                    self.add_file(root, 'folder_wrench.png')
                else:
                    self.add_file(root, 'folder.png')
            #print self.files

            for d in dirs:
                d = os.path.join(root, d)
                if d not in self.files:
                    if d.startswith("."):
                        item = self.add_file(d, 'folder_wrench.png')
                    else:
                        item = self.add_file(d, 'folder.png')
                    self.SetItemHasChildren(item, True)
            
            
            for file in files:
                file = os.path.join(root, file)
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

