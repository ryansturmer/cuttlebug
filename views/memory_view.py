import wx
import wx.grid as grid
import view
import util
import app

class MemoryTable(grid.PyGridTableBase):

    def __init__(self, base, size, stride, update_callable=None):
        grid.PyGridTableBase.__init__(self)
        self.base = base
        self.size = size
        self.stride = stride
        self.set_cols(1)
        self.cached_range = (-1,-1)
        self.cached_data = []
        self.update_callable=update_callable

    def set_stride(self, stride):
        self.stride = int(stride)
        self.ResetView()

    def set_base(self, base):
        self.base = int(base)
        self.ResetView()
        
    def update(self, base_addr, values):
        self.cached_range =  (base_addr, base_addr + (len(values)*self.stride))
        self.cached_data = list(values)
        
    def is_in_cache(self, addr):
        min_addr, max_addr = self.cached_range
        return addr >= min_addr and addr <= max_addr

    def set_cols(self, cols):
        self.cols = cols
        self.rows = self.size / (self.stride*cols)
        self.ResetView()

    def address_from_coordinate(self, row, col):
        return self.base + row*self.stride*self.cols + col*self.stride

    def coordinate_from_address(self, address):
        row = (address-self.base) / (self.stride*self.cols)
        col = ((address-self.base) % (self.cols))/self.stride
        return row, col

    def address_from_row(self, row):
        return self.address_from_coordinate(row, 0)
    
    def GetAttr(self, row, col, kind):
        addr = self.address_from_coordinate(row, col)
        attr = grid.GridCellAttr()
        if not self.is_in_cache(addr):
            attr.SetTextColour("darkgray")
        else:
            attr.SetTextColour(wx.BLACK)
        attr.IncRef()
        return attr

    def GetRowLabelValue(self, row):
        return "0x%08x" % int(self.address_from_row(row))

    def GetNumberRows(self):
        return self.rows

    def GetNumberCols(self):
        return self.cols

    def IsEmptyCell(self, row,col):
        return False

    def GetValue(self, row,col):
        addr = self.address_from_coordinate(row ,col)
        if addr >= self.cached_range[0] and addr < self.cached_range[1]:
            fmt = "%%0%dx" % (self.stride*2)
            try:
                return fmt % self.cached_data[(addr-self.cached_range[0])/self.stride]
            except:
                return "??"*self.stride
        else:
            return "??"*self.stride

    def SetValue(self, row, col, value):
        addr = self.address_from_coordinate(row,col)
        if self.update_callable:
            self.update_callable(addr, value)
         
    def clear_cache(self):
        self.cached_range = (-1,-1)
        self.cached_data = []

    def ResetView(self):
            """Trim/extend the control's rows and update all values"""
            if self.GetView() is None:
                return
            self.clear_cache()
            self.GetView().BeginBatch()
            for current, new, delmsg, addmsg in [
                    (self.GetView().GetNumberRows(), self.GetNumberRows(), grid.GRIDTABLE_NOTIFY_ROWS_DELETED, grid.GRIDTABLE_NOTIFY_ROWS_APPENDED),
                    (self.GetView().GetNumberCols(), self.GetNumberCols(), grid.GRIDTABLE_NOTIFY_COLS_DELETED, grid.GRIDTABLE_NOTIFY_COLS_APPENDED),
            ]:
                    if new < current:
                            msg = grid.GridTableMessage(
                                    self,
                                    delmsg,
                                    new,    # position
                                    current-new,
                            )
                            self.GetView().ProcessTableMessage(msg)
                    elif new > current:
                            msg = grid.GridTableMessage(
                                    self,
                                    addmsg,
                                    new-current
                            )
                            self.GetView().ProcessTableMessage(msg)
            self.GetView().EndBatch()

class MemoryGridControl(grid.Grid):

    def __init__(self, parent, id=-1, style=0, size=1048576, stride=4, update_callable=None):
        grid.Grid.__init__(self, parent, id=id, style=style)
        self.SetColLabelSize(0)
        table = MemoryTable(base=0, size=size, stride=stride, update_callable=update_callable)
        self.hover_cell = (None,None)
        self.hover_address = None
        self.update_callable=update_callable
        self.SetTable(table,True)
        self.set_font("Courier New")
        self.EnableGridLines(False)
        self.AutoSizeLabels()
        self.resize()
        self.Bind(wx.EVT_SIZE, self.on_size)
        self.Bind(grid.EVT_GRID_CELL_LEFT_CLICK, self.on_cell_clicked)
        
    def on_size(self, evt):
        self.resize()
            
    def visible_address_range(self):
        x,y1 = self.CalcScrolledPosition(0,0)
        y1 = abs(y1)
        x,y = self.GetClientSize() 
        y2 = y1 + y

        row1 = abs(y1)/self.GetDefaultRowSize()
        row2 = abs(y2)/self.GetDefaultRowSize()
        start_addr = self.GetTable().address_from_row(row1-1 if row1-1 >= 0 else 0)
        end_addr = self.GetTable().address_from_row(row2+1) + self.GetNumberCols()*self.GetTable().stride
        #print "getting visible address range: %s" % ((start_addr, end_addr),)
        return (start_addr, end_addr)

    def on_cell_clicked(self, evt):
        #print evt.GetPosition()
        r,c = evt.GetRow(), evt.GetCol()
        #print "Row=%d, Col=%d, Addr =0x%08x" % (r,c,self.Table.address_from_coordinate(r,c))
        #print "Computed Row and Column: %d,%d" % self.Table.coordinate_from_address(self.Table.address_from_coordinate(r,c))
        evt.Skip()
        
    def set_font(self, face, size=9):
        font = self.GetDefaultCellFont()
        font.SetFaceName(face)
        font.SetPointSize(size)
        self.SetDefaultCellFont(font)
        self.SetLabelFont(font)
        self.SetDefaultCellAlignment(wx.ALIGN_CENTRE, wx.ALIGN_CENTRE)

    def update(self, base_addr, values):
        self.GetTable().update(base_addr,values)
        self.ForceRefresh()

    def clear_cache(self):
        self.GetTable().clear_cache()

    def set_size(self, size):
        self.size = size
    
    def resize(self):
        table = self.GetTable()
        grid_width,grid_height = self.GetClientSize()
        grid_width -= self.GetRowLabelSize()
        grid_width -= wx.SystemSettings.GetMetric(wx.SYS_VSCROLL_X)
        dc = wx.ScreenDC()
        dc.SetFont(self.GetDefaultCellFont())

        cell_width,cell_height = dc.GetTextExtent("M"*((table.stride*2)+2))
        columns = grid_width/cell_width or 1
        cell_width = grid_width/columns
        table.set_cols(columns)
        self.SetDefaultColSize(cell_width)
        self.ForceRefresh()

    def AutoSizeLabels(self):
            dc = wx.ScreenDC()
            dc.SetFont(self.GetLabelFont())
            width = dc.GetTextExtent("0x00000000 ")[0]
            self.SetRowLabelSize(width)

class MemoryView(view.View):

    def __init__(self, parent, controller, size=1048576, stride=4):
        super(MemoryView, self).__init__(parent, -1, style=wx.BORDER_STATIC, size=(300, 800), controller=controller)
        self.grid = MemoryGridControl(self, -1, style=wx.BORDER_NONE, stride=stride, update_callable=self.on_cell_update)
        self.grid.Bind(wx.EVT_SCROLLWIN, self.on_scrolled) 
        #self.grid.Bind(wx.EVT_SIZE, self.on_size)
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.fetching = False
        
        
        sizer.Add(self.create_toolbar(), 0, wx.EXPAND)        
        sizer.Add(self.grid,1, wx.EXPAND)
        
        self.SetSizer(sizer)
        self.controller.Bind(app.EVT_APP_TARGET_HALTED, self.on_target_halted)
        self.controller.Bind(app.EVT_APP_TARGET_RUNNING, self.on_target_running)
        self.controller.Bind(app.EVT_APP_TARGET_CONNECTED, self.on_target_connected)
        
        self.grid.GetGridWindow().Bind(wx.EVT_MOTION, self.on_mouse_motion)
    
    def create_toolbar(self):
        toolbar = wx.ToolBar(self, -1, style=wx.TB_HORIZONTAL | wx.NO_BORDER | wx.TB_FLAT)
        toolbar.SetToolBitmapSize((18,18))
        combo_address = wx.ComboBox(toolbar, style=wx.TE_PROCESS_ENTER)
        combo_address.Bind(wx.EVT_TEXT_ENTER, self.on_addr_changed)
        combo_address.Bind(wx.EVT_COMBOBOX, self.on_addr_changed)
        combo_address.SetValue('0x00000000')
        self.combo_address = combo_address
        combo_size = wx.ComboBox(toolbar, style=wx.CB_READONLY)
        combo_size.Append("Byte (8)")
        combo_size.Append("Word (16)")
        combo_size.Append("Long (32)")
        combo_size.SetSelection(2)
        combo_size.Bind(wx.EVT_COMBOBOX, self.on_size_changed)
        
        toolbar.AddControl(wx.StaticText(toolbar, -1, " Base Addr: "))
        toolbar.AddControl(combo_address)
        toolbar.AddControl(wx.StaticText(toolbar, -1, " Size: "))
        toolbar.AddControl(combo_size)
        
        util.tool_item(self, toolbar, label="Refresh", func=self.on_refresh, icon='arrow_refresh.png')
        
        toolbar.Realize()
        toolbar.Fit()
        return toolbar
    
    def on_addr_changed(self, evt):
        cb = evt.GetEventObject()
        try:
            s = cb.GetValue()
            new_addr = util.str2int(s)
            self.grid.Table.set_base(new_addr)
            self.refresh()
            self.last_set_address = s
            if cb.FindString(s) < 0:
                cb.Append(s)
        except:
            cb.SetValue(self.last_set_address)
        
    def on_size_changed(self, evt):
        cb = evt.GetEventObject()
        item = cb.GetSelection()
        self.grid.Table.set_stride({0:1, 1:2, 2:4}[item])
        self.grid.resize()
        self.refresh()
        
    def on_refresh(self, evt):
        self.refresh()
    
    def on_target_connected(self, evt):
        self._fetch_data()
        evt.Skip()
        
    def on_target_halted(self, evt):
        self._fetch_data()
        evt.Skip()

    def on_target_running(self, evt):
        evt.Skip()
    
    def refresh(self):
        self._fetch_data()
    def _fetch_data(self):
        if not self.fetching and self.controller.gdb:
            start, end = self.grid.visible_address_range()
            
            #print "Fetching data for 0x%08x -> 0x%08x" % (start, end)
            self.controller.gdb.read_memory(start, self.grid.GetTable().stride, end-start, callback=self._on_data_fetched)
            self.fetching = True

    def _on_data_fetched(self, result):
        self.fetching = False
        if hasattr(result, 'memory'):
                memtable = []
                for entry in result.memory:
                    memtable.append(int(entry.data[0]))
                wx.CallAfter(self.update,int(result.addr,16), memtable)
        
    def update(self, base_addr, values):
        print "view update"
        self.grid.update(base_addr, values)
        
    def on_cell_update(self, addr, value):
        print hex(addr) + "=" + str(value)

    def on_scrolled(self, evt):
        wx.CallAfter(self._fetch_data)
        evt.Skip()
    
    def on_size(self, evt):
        self._fetch_data()
        evt.Skip()
                
    def on_mouse_motion(self, evt):
        x,y = self.grid.CalcUnscrolledPosition(evt.GetPosition())
        row = self.grid.YToRow(y)
        col = self.grid.XToCol(x)
        if (row,col) != self.grid.hover_cell:
            self.grid.hover_cell = (row, col)
            self.grid.hover_address = self.grid.GetTable().address_from_coordinate(row, col)
            #print "Changed cell", self.grid.hover_cell, "0x%08x" % self.grid.hover_address
            #self.controller.gdb.command('info symbol 0x%08x' % v, callback=self.on_symbol_lookup)    
            tooltip = "Address = 0x%08x" % self.grid.hover_address
            self.grid.GetGridWindow().SetToolTipString(tooltip)
        else:
            pass
            #self.grid.GetGridWindow().HideToolTip()
        evt.Skip()

    def on_symbol_lookup(self, data):
        pass
        #print data

if __name__ == "__main__":
    pass