import wx
import view, project, util

class ProjectView(view.View):

    def __init__(self, *args, **kwargs):
        super(ProjectView, self).__init__(*args, **kwargs)
        self.tree = wx.TreeCtrl(self, -1, style=wx.TR_HIDE_ROOT)
        self.create_art("folder.png")
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.tree, 1, wx.EXPAND)
        self.SetSizer(sizer)

    def create_art(self, *artlist):
        self.art = {}
        image_list = wx.ImageList(16,16)
        for icon in artlist:
            self.art[icon] = image_list.Add(util.get_icon(icon))
        self.tree.SetImageList(image_list)
        self.image_list = image_list

    def add_item(self, name, icon=None, parent=None):
        if not parent: parent = self.root
        item = self.tree.AppendItem(parent, name)
        if icon:
            self.tree.SetItemImage(item, self.art[icon], wx.TreeItemIcon_Normal)
        return item

    def setup_tree(self):
        self.clear_tree()
        self.files = self.add_item("Files", icon="folder.png")

    def clear_tree(self):
        self.tree.DeleteAllItems()
        self.root = self.tree.AddRoot("root")

    def set_project(self, project):
        self.project = project
        self.setup_tree()
