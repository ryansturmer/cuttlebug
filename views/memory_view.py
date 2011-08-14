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

    def __address_from_coordinate(self, row, col):
        return row*self.stride*self.cols + col*self.stride

    def __coordinate_from_address(self, address):
        row = address / (self.stride*self.cols)
        col = (address % (self.cols))/self.stride
        return row, col

    def address_from_coordinate(self, row, col):
        return self.__address_from_coordinate(row, col)
    
    def address_from_row(self, row):
        return self.__address_from_coordinate(row, 0)

    def coordinate_from_address(self, address):
        return self.__coordinate_from_address(address)
    
    def GetAttr(self, row, col, kind):
        addr = self.__address_from_coordinate(row, col)
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
        addr = self.__address_from_coordinate(row ,col)
        if addr >= self.cached_range[0] and addr < self.cached_range[1]:
            fmt = "%%0%dx" % (self.stride*2)
            try:
                return fmt % self.cached_data[(addr-self.cached_range[0])/self.stride]
            except:
                return "??"*self.stride
        else:
            return "??"*self.stride

    def SetValue(self, row, col, value):
        addr = self.__address_from_coordinate(row,col)
        if self.update_callable:
            self.update_callable(addr, value)
         
    def clear_cache(self):
        self.cached_range = (-1,-1)
        self.cached_data = []

    def ResetView(self):
            """Trim/extend the control's rows and update all values"""
            #print "Table rows, cols = %s" % ((self.rows, self.cols),)
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
        
        
        #sizer.Add(self.create_toolbar(), 0, wx.EXPAND)        
        sizer.Add(self.grid,1, wx.EXPAND)
        
        self.SetSizer(sizer)
        self.controller.Bind(app.EVT_APP_TARGET_HALTED, self.on_target_halted)
        self.controller.Bind(app.EVT_APP_TARGET_RUNNING, self.on_target_running)
        self.controller.Bind(app.EVT_APP_TARGET_CONNECTED, self.on_target_connected)
        
        self.grid.Bind(grid.EVT_GRID_LABEL_LEFT_DCLICK, self.on_label_dclick)
        self.grid.GetGridWindow().Bind(wx.EVT_MOTION, self.on_mouse_motion)
    
    def create_toolbar(self):
        pnl_toolbar = wx.Panel(self)
        combo_address = wx.ComboBox(pnl_toolbar)
        toolbar_sizer = wx.BoxSizer(wx.HORIZONTAL)
        toolbar_sizer.Add(combo_address, border=5, flag=wx.ALL)
        pnl_toolbar.SetSizer(toolbar_sizer)
        return pnl_toolbar
        
    def on_target_connected(self, evt):
        self._fetch_data()
        
    def on_target_halted(self, evt):
        self._fetch_data()

    def on_target_running(self, evt):
        pass
    
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
        self.grid.update(base_addr, values)
        
    def on_cell_update(self, addr, value):
        print hex(addr) + "=" + str(value)

    def on_scrolled(self, evt):
        #print "scrolled"
        #print evt.GetPosition()
        wx.CallAfter(self._fetch_data)
        #self._fetch_data()
        evt.Skip()
    
    def on_size(self, evt):
        self._fetch_data()
        evt.Skip()
        
    def on_label_dclick(self, evt):
        start, end = self.grid.visible_address_range()
        #print "Visible Address Range: 0x%08x -> 0x%08x" % (start, end)
        #print "Stride: ", self.grid.GetTable().stride
        self._fetch_data()        
        
    def on_mouse_motion(self, evt):
        x,y = self.grid.CalcUnscrolledPosition(evt.GetPosition())
        row = self.grid.YToRow(y)
        col = self.grid.XToCol(x)
        if (row,col) != self.grid.hover_cell:
            self.grid.hover_cell = (row, col)
            self.grid.hover_address = self.grid.GetTable().address_from_coordinate(row, col)
            #print "Changed cell", self.grid.hover_cell, "0x%08x" % self.grid.hover_address
            v = int(self.grid.GetCellValue(row, col),16)
            self.controller.gdb.command('info symbol 0x%08x' % v, callback=self.on_symbol_lookup)    
        evt.Skip()

    def on_symbol_lookup(self, data):
        pass
        #print data

if __name__ == "__main__":
    pass