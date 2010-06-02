import wx
import wx.lib.mixins.listctrl as listmix
import gdb, view, util, odict, menu
import os, sys

class BreakpointListCtrl(wx.ListCtrl, listmix.ListCtrlAutoWidthMixin, util.ArtListMixin):
    TYPE = 0
    LOCATION = 1
    
    def __init__(self, parent):
        wx.ListCtrl.__init__(self, parent, -1, style=wx.LC_VIRTUAL | wx.LC_REPORT | wx.LC_HRULES )
        listmix.ListCtrlAutoWidthMixin.__init__(self)
        util.ArtListMixin.__init__(self, wx.IMAGE_LIST_SMALL)
        self.parent = parent
        self.add_art('stop.png', 'stop_disabled.png')
        self.InsertColumn(0, '')
        self.InsertColumn(1, "File")
        self.InsertColumn(2, "Line")
        self.SetColumnWidth(0, 24)
        self.SetColumnWidth(1, wx.LIST_AUTOSIZE)
        self.SetItemCount(0)
        self.clicked_item = None
        self.breakpoints = None
        
        # Attributes (for changing list item colors)
        self.redattr = wx.ListItemAttr()
        self.redattr.SetTextColour("red")
        self.blackattr = wx.ListItemAttr()
        self.blackattr.SetTextColour("black")
        
        self.create_popup_menu()
        self.Bind(wx.EVT_RIGHT_DOWN, self.on_context_menu)

        
    def OnGetItemColumnImage(self, item, col):
        #return -1
        if col == 0:
            #return 0
            if self.breakpoints[item].enabled:
                return self.get_art_idx('stop.png')
            else:
                return self.get_art_idx('stop_disabled.png')

        else:
            return -1

    def OnGetItemImage(self, item):
        return 0
    
    def OnGetItemText(self, item, col):
        if col == 1:
            try:
                return os.path.basename(self.breakpoints[item].fullname)
            except:
                return "<Unknown File>"
        elif col == 2:
            line = self.breakpoints[item].line    
            return str(line) if line > 0 else ''
        else:
            return ''
        
    def OnGetItemAttr(self, item):
        return self.blackattr
        

    def create_popup_menu(self):
        m = menu.manager.menu()        
        self.mnu_clear_bp = m.item("Clear Breakpoint", func=self.on_clear_breakpoint, icon="stop_disabled.png", hide=[menu.TARGET_RUNNING, menu.TARGET_DETACHED], 
                                                                                show=[menu.TARGET_HALTED, menu.TARGET_ATTACHED])
        self.mnu_disable_bp = m.item("Disable Breakpoint", func=self.on_disable_breakpoint, icon="stop_disabled.png", hide=[menu.TARGET_RUNNING, menu.TARGET_DETACHED], 
                                                                                show=[menu.TARGET_HALTED, menu.TARGET_ATTACHED])
        self.mnu_enable_bp = m.item("Enable Breakpoint", func=self.on_enable_breakpoint, icon="stop.png", hide=[menu.TARGET_RUNNING, menu.TARGET_DETACHED], 
                                                                                show=[menu.TARGET_HALTED, menu.TARGET_ATTACHED])

        self.popup_menu = m
    
    def on_context_menu(self, evt):
        click_pos = evt.GetPosition()            
        id, flag = self.HitTest(click_pos)
        if flag & wx.LIST_HITTEST_ONITEM:
            self.clicked_item = self.breakpoints[id]
            if self.clicked_item.enabled:
                self.mnu_disable_bp.show()
                self.mnu_enable_bp.hide()

            else:
                self.mnu_disable_bp.hide()
                self.mnu_enable_bp.show()
                
            self.PopupMenu(self.popup_menu.build(self))     
        
    def on_clear_breakpoint(self, evt):
        if self.clicked_item:
            self.parent.controller.clear_breakpoint(self.clicked_item.number) 

    def on_disable_breakpoint(self, evt):
        if self.clicked_item:
            self.parent.controller.disable_breakpoint(self.clicked_item.number)

    def on_enable_breakpoint(self, evt):
        if self.clicked_item:
            self.parent.controller.enable_breakpoint(self.clicked_item.number)
                        
    def update(self, bkpt_table):
        items = list(bkpt_table)
        self.Freeze()
        self.breakpoints = items
        self.SetItemCount(len(items))
        self.Refresh()
        self.Thaw()
        
class BreakpointView(view.View):
    
    def __init__(self, *args, **kwargs):
        super(BreakpointView, self).__init__(*args, **kwargs)
        self.list = BreakpointListCtrl(self)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.list, 1, wx.EXPAND)
        self.SetSizer(sizer)
        
    def on_breakpoint_update(self, data):
        pass
    def update(self):
        self.list.update(self.controller.gdb.breakpoints)
    
