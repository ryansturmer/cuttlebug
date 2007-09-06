import wx
import view, project, util, icons
import os

class ProjectViewEvent(view.ViewEvent): pass

EVT_PROJECT_DCLICK_FILE = wx.PyEventBinder(wx.NewEventType())

class ProjectView(view.View):

    def __init__(self, *args, **kwargs):
        super(ProjectView, self).__init__(*args, **kwargs)
        self.tree = ProjectTree(self, -1)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.tree, 1, wx.EXPAND)
        self.SetSizer(sizer)
        self.SetSize((200,-1))
        self.tree.Bind(wx.EVT_LEFT_DCLICK, self.on_left_dclick)
        self.tree.Bind(wx.EVT_RIGHT_DOWN, self.on_right_click)

    def on_left_dclick(self, evt):
        pt = evt.GetPosition()
        item, flags = self.tree.HitTest(pt)
        if item:
            path = self.tree.GetPyData(item)
            if path:
                evt = ProjectViewEvent(EVT_PROJECT_DCLICK_FILE, self, data=path)
                wx.PostEvent(self, evt)

    def on_right_click(self, evt):
        pt = evt.GetPosition()
        item, flags = self.tree.HitTest(pt)
        if item:
            path = self.tree.GetPyData(item)
            if path:
                evt = ProjectViewEvent(EVT_PROJECT_DCLICK_FILE, self, data=path)
                wx.PostEvent(self, evt)
        
    def set_project(self, project):
        self.project = project
        self.tree.set_project(project)

    def show_backups(self, show):
        self.tree.show_backups(show)

    def update(self):
        self.tree.update()

class ProjectTree(wx.TreeCtrl):

    def __init__(self, parent, id):
        super(ProjectTree, self).__init__(parent, id)
        self.art = {}
        self.icon_bindings = {}
        self.files = {}
        self.image_list = wx.ImageList(16,16)
        self.SetImageList(self.image_list)
        self.set_project(None)
        self.backups_visible = False

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
        parent, fn = os.path.split(file)
        parent_item = self.files[parent]

        item = self.AppendItem(parent_item, fn)
        self.SetPyData(item, file)
        self.files[file] = item
        self.SetItemImage(item, icon)

    def update_file_tree(self):
        if not self.project:
            return
        self.files[self.project.directory] = self.files_item
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
                    
    def update(self):
        self.SetItemText(self.root_item, self.project.general.project_name)
        self.update_file_tree()

