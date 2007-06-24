#from __future__ import with_statement
import wx.stc as stc
import os
import build, prefs, util
import wx
import wx.grid as grid
import views

class RegisterListControl(wx.ListCtrl):
    def __init__(self, parent, id=-1, style=0):
        super(RegisterListControl, self).__init__(parent=parent, id=id)
        self.InsertColumn(0, "Register")
        self.InsertColumn(1, "Value")
        self.InsertStringItem(0, "Hello")
        self.InsertStringItem(0, "World")
        self.InsertStringItem(0, "Goodbye")

class MemoryTable(grid.PyGridTableBase):

    def __init__(self, size, stride, update_callable=None):
        grid.PyGridTableBase.__init__(self)
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
        self.cached_range =  (base_addr, base_addr + len(values))
        self.cached_data = list(values)
    def is_in_cache(self, addr):
        return addr >= self.cached_range[0] and addr <= self.cached_range[1]

    def set_cols(self, cols):
        self.cols = cols
        self.rows = self.size / (self.stride*cols)
        self.ResetView()

    def __address_from_coordinate(self, row, col):
        return row*self.stride*self.cols + col*self.stride

    def __coordinate_from_address(self, address):
        row = address / self.stride*self.cols
        col = address % self.stride*self.cols
        return row, col

    def address_from_row(self, row):
        return self.__address_from_coordinate(row, 0)

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
        if addr >= self.cached_range[0] and addr <= self.cached_range[1]:
            fmt = "%%0%dx" % (self.stride*2)
            try:
                return fmt % self.cached_data[addr-self.cached_range[0]]
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
        table = MemoryTable(size=size, stride=stride, update_callable=update_callable)
        self.update_callable=update_callable
        self.SetTable(table,True)
        self.set_font("Courier New")
        self.EnableGridLines(False)
        self.AutoSizeLabels()
        self.resize()
        self.Bind(wx.EVT_SIZE, self.on_size)

    def __get_stride(self):
        return self.GetTable().stride

    def __set_stride(self, stride):
        self.GetTable.set_stride(stride)
    stride = property(__get_stride, __set_stride)
    def on_size(self, evt):
        self.resize()
    
    def visible_address_range(self):
        x,y1 = self.CalcScrolledPosition(0,0)
        y1 = abs(y1)
        x,y = self.GetClientSize() 
        y2 = y1 + y

        row1 = abs(y1)/self.GetDefaultRowSize()
        row2 = abs(y2)/self.GetDefaultRowSize()
        start_addr = self.GetTable().address_from_row(row1)
        end_addr = self.GetTable().address_from_row(row2) + self.GetNumberCols()*self.GetTable().stride
        return (start_addr, end_addr)

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

class BuildPortalControl(stc.StyledTextCtrl):
    pass

class EditorControl(stc.StyledTextCtrl):

    def get_name(self):
        if self.file_path:
            root, name = os.path.split(self.file_path)
            return name
        else:
            return 'Untitled'

    def open_file(self, path):
        file = None
        try:
            file = open(path, 'r')
            text = file.read()
            self.SetText(text)
            self.EmptyUndoBuffer()
            self.edited = False
            self.file_path = path
        except IOError:
            self.SetText('')
        finally:
            if file:
                file.close()

class StatusBar(wx.StatusBar):

    def __init__(self, *args, **kwargs):
        super(StatusBar, self).__init__(*args, **kwargs)
        self.SetFieldsCount(3)
        self.SetStatusWidths([18, -4,-1])
        self.text = ""
        self.gauge = wx.Gauge(self)
        self.timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.on_timer)
        self.Bind(wx.EVT_SIZE, self.on_size)
        self.Bind(wx.EVT_IDLE, self.on_idle)
        self.icon = None

    def __set_icon(self, icon):
        if icon:
            self.__icon = util.get_icon(icon)
        else:    
            self.__icon = util.get_icon('blank.png')
        self.staticbmp = wx.StaticBitmap(self, -1, self.__icon)
        self.Reposition()

    def __get_icon(self):
        return self.icon
    icon = property(__get_icon, __set_icon)

    def __set_text(self, text):
        self.SetStatusText(str(text), 1)
    def __get_text(self):
        return str(self.GetStatusText())
    text = property(__get_text, __set_text)

    def __set_working(self, working):
        self.__working = bool(working)
        if self.__working: 
            self.gauge.Pulse()
            self.timer.Start(100)
        else:
            self.timer.Stop()
            self.gauge.SetValue(0)
    def __get_working(self):
        return self.__working
    working = property(__get_working, __set_working)

    def on_timer(self, evt):
        if self.__working:
            self.gauge.Pulse()
   
    def on_idle(self, evt):
        if self.size_changed:
            self.Reposition()

    def on_size(self, evt):
        self.Reposition()
        self.size_changed = True

    def Reposition(self):
        # Gauge
        rect = self.GetFieldRect(2)
        self.gauge.SetPosition((rect.x+2, rect.y+2))
        self.gauge.SetSize((rect.width-4, rect.height-4))
        
        # Icon
        rect = self.GetFieldRect(0)
        self.staticbmp.SetPosition((rect.x+2, rect.y+2))
        self.size_changed = False
