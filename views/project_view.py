import wx
import view, project, util
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

    def on_left_dclick(self, evt):
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

class ProjectTree(wx.TreeCtrl):

    def __init__(self, parent, id):
        super(ProjectTree, self).__init__(parent, id)
        self.art = {}
        self.icon_bindings = {}
        self.files = {}
        self.image_list = wx.ImageList(16,16)
        self.SetImageList(self.image_list)
        self.bind_icons()
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

    def bind_icons(self):
        self.bind_icon('.c', 'file_c.png')        
        self.bind_icon('.s', 'file_s.png')
        self.bind_icon('.ld', 'file_link.png')
        self.bind_icon('.bz2', 'file_archive.png')
        self.bind_icon('.gz', 'file_archive.png')
        self.bind_icon('.zip', 'file_archive.png')
        self.bind_icon('.tar', 'file_archive.png')
        self.bind_icon('.ini', 'file_wrench.png')
        self.bind_icon('.cfg', 'file_wrench.png')
        self.bind_icon('.py', 'file_py.png')
        self.bind_icon('.h', 'file_h.png')
        self.bind_icon('.png', 'file_picture.png')
        self.bind_icon('.jpg', 'file_picture.png')
        self.bind_icon('.gif', 'file_picture.png')
        self.bind_icon('.tif', 'file_picture.png')
        self.bind_icon('.tiff', 'file_picture.png')
        self.bind_icon('.sh', 'file_gear.png')
        self.bind_icon('.script', 'file_gear.png')

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

            for file in files:
                if file not in self.files:
                    if not self.backups_visible and file.endswith("~"):
                        continue
                    self.add_file(os.path.join(root, file), self.get_file_icon(file))
