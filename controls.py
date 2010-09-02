import wx
#import util
import wx.lib.mixins.listctrl as listmix
from odict import OrderedDict

class BusyMenuBar(wx.MenuBar):
    pass

class StatusBar(wx.StatusBar):
    ICON = 0
    TEXT = 1
    LINE = 2
    STATE = 3
    GAUGE = 4
    def __init__(self, *args, **kwargs):
        super(StatusBar, self).__init__(*args, **kwargs)
        self.SetFieldsCount(5)
        self.SetStatusWidths([18, -24,-2,-8,-8])


        # Progress Bar
        self.gauge = wx.Gauge(self)
        self.work_timer = wx.Timer(self, id=1)

        # State (text that is blinking
        self.state_timer = wx.Timer(self, id=2)
        self.state_on = True
        self._state = ""

        self.Bind(wx.EVT_TIMER, self.on_work_timer, id=1)
        self.Bind(wx.EVT_TIMER, self.on_state_timer, id=2)
        
        self.Bind(wx.EVT_SIZE, self.on_size)
        self.Bind(wx.EVT_IDLE, self.on_idle)
        self.icon = None

    def __set_line(self, line=0):
        if line:
            self._line = int(line)
            self.SetStatusText(str(line), self.LINE)
        else:
            self._line = 0
            self.SetStatusText('', self.LINE)
            
    def __get_line(self): return self._line
    line = property(__get_line, __set_line)
    
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

    def set_state(self, text, blink=False, color=wx.BLACK):
        #TODO Put COLOR support in here
        self._state = text
        if text and blink:
            self.state_timer.Start(500)
        else:
            self.state_timer.Stop()
        self.SetStatusText(text, self.STATE)
        
    def get_state(self): return self._state
    
    def __set_text(self, text):
        wx.CallAfter(self.SetStatusText,str(text), self.TEXT)
    def __get_text(self):
        return str(self.GetStatusText())
    text = property(__get_text, __set_text)

    def __set_working(self, working):
        self.__working = bool(working)
        if self.__working: 
            wx.CallAfter(self.gauge.Pulse)
            wx.CallAfter(self.work_timer.Start,100)
        else:
            wx.CallAfter(self.work_timer.Stop)
            wx.CallAfter(self.gauge.SetValue,0)
    
    def __get_working(self):
        return self.__working
    working = property(__get_working, __set_working)

    def on_work_timer(self, evt):
        if self.__working:
            self.gauge.Pulse()
        else:
            self.gauge.SetValue(0)
            
    def on_state_timer(self, evt):
        if self.state_on:
            self.state_on = False
            self.SetStatusText(self._state, self.STATE)
        else:
            self.state_on = True
            self.SetStatusText("", self.STATE)
            
    def on_idle(self, evt):
        if self.size_changed:
            self.Reposition()

    def on_size(self, evt):
        self.Reposition()
        self.size_changed = True

    def Reposition(self):
        # Gauge
        rect = self.GetFieldRect(self.GAUGE)
        self.gauge.SetPosition((rect.x+2, rect.y+2))
        self.gauge.SetSize((rect.width-4, rect.height-4))
        
        # Icon
        rect = self.GetFieldRect(self.ICON)
        self.staticbmp.SetPosition((rect.x+2, rect.y+2))
        self.size_changed = False

class DictListCtrl(wx.ListCtrl, listmix.ListCtrlAutoWidthMixin, listmix.TextEditMixin):
    
    def __init__(self, parent, color_changes=True):
        wx.ListCtrl.__init__(self, parent, -1, style=wx.LC_REPORT | wx.LC_VIRTUAL | wx.LC_HRULES)
        listmix.ListCtrlAutoWidthMixin.__init__(self)
        listmix.TextEditMixin.__init__(self)

        self.InsertColumn(0, "Name")
        self.InsertColumn(1, "Value")
        self.SetColumnWidth(0, wx.LIST_AUTOSIZE_USEHEADER)
        self.SetColumnWidth(2, wx.LIST_AUTOSIZE_USEHEADER)

        self.SetItemCount(0)
        self.__items = OrderedDict()
        self.__changed = {}

        # Attributes (for changing list item colors)
        self.redattr = wx.ListItemAttr()
        self.redattr.SetTextColour("red") if color_changes else self.redattr.SetTextColour("black")
        self.blackattr = wx.ListItemAttr()
        self.blackattr.SetTextColour("black")

    def OnGetItemText(self, item, col):
        if col == 0:
            return self.__items.keys()[item]
        else:
            return self.__items.values()[item]

    def OnGetItemAttr(self, item):
        key = self.__items.keys()[item]
        if key in self.__changed and self.__changed[key]:
            return self.redattr
        else:
            return self.blackattr

    def __contains__(self, key):
        return key in self.__items

    def __setitem__(self, key, value):
        changed = False
        try:
            old_value = self.__items[key]
            if value != old_value:
                changed = True
        except:
            changed = True
        if changed:
            self.__changed[key] = True
        else:
            self.__changed[key] = False

        self.__items[key] = value
        self.SetItemCount(len(self.__items))
        self.Refresh()
        
    def __getitem__(self, key):
        return self.__items[key]

    def __iter__(self):
        return iter(self.__items.keys()[:])

    def __delitem__(self, key):
        self.remove_item(key)
        
    def remove_item(self, key):
        try:
            self.__items.pop(key)
            self.__changed.pop(key)
        except:
            pass
        self.SetItemCount(len(self.__items))
        self.Refresh()
        
    def update(self, items):
        for key in items:
            self[key] = items[key]
        for key in self:
            if key not in items:
                self.remove_item(key)
        self.Refresh()

class ListControl(wx.ListCtrl):
    def __init__(self, parent):
        super(ListControl, self).__init__(parent, -1, style=wx.LC_REPORT|wx.LC_SINGLE_SEL|wx.LC_HRULES)
        self.data = {}
    def clear(self):
        self.DeleteAllItems()
    def set_columns(self, columns):
        for i, column in enumerate(columns):
            self.InsertColumn(i, column)
    def update_item(self, row, item):
        for i, s in enumerate(item):
            s = str(s)
            self.SetStringItem(row, i, s)
    def add_item(self, item, data=None, color=wx.BLACK, bgcolor=wx.WHITE):
        n = self.GetItemCount()
        for i, s in enumerate(item):
            s = str(s)
            if i == 0:
                self.InsertStringItem(n, s)
            else:
                self.SetStringItem(n, i, s)
        self.SetItemTextColour(n,color)
        self.SetItemBackgroundColour(n, bgcolor)
        self.data[n] = data
    def get_data(self, n):
        return self.data[n]
    def auto_size(self):
        n = self.GetColumnCount()
        for i in range(n):
            self.SetColumnWidth(i, -1)
            s1 = self.GetColumnWidth(i)
            self.SetColumnWidth(i, -2)
            s2 = self.GetColumnWidth(i)
            width = max(s1, s2)
            if i < n-1: width += 20
            self.SetColumnWidth(i, width)

        
class BitField(object):
    
    def __init__(self, width, start=0):
        self.width = width
	self.start = start
        self.fields = []
        
    def set_bit(self, name, bit):
        self.set_field(name, bit)
        
    def set_field(self, name, start, length=1):
        if start < self.start or (start+length) > self.width:
            raise ValueError("Cannot set bit %d of a %d bit field.") % (start+length, self.width)
        self.fields.append((name, start, length))
    @property             
    def empty_slots(self):
        full_slots = set()
        for name, start, length in self.fields:
            for i in range(start, start+length):
                full_slots.add(i)
        return set(range(self.width)) - full_slots
    
import wx.lib.buttons as buttons  
def button(parent, label, style):
    pnl = wx.Panel(parent)
    txt = wx.StaticText(pnl, label=label, style=wx.ALIGN_CENTER)
    txt.SetBackgroundColour(wx.RED)
    sizer = wx.BoxSizer(wx.VERTICAL)

    pnl.SetBackgroundColour(wx.WHITE)
    sizer.Add(txt, 1, flag=wx.EXPAND)
    pnl.SetSizer(sizer)
    return pnl
    #btn =  buttons.GenButton(parent, -1, label=label, style=style)      
    #btn.SetBackgroundColour(wx.WHITE)
    #btn.SetMinSize((10,10))
    #return btn

class Cell(wx.Panel):
    def __init__(self, parent, type=wx.ALL, padding=0):
        self.dc = None
        self.padding = padding
        self.type = type
        wx.Panel.__init__(self, parent, -1)
        self.Bind(wx.EVT_SIZE, self.on_size)
        self.Bind(wx.EVT_PAINT, self.on_paint)
        #self.Bind(wx.EVT_ERASE_BACKGROUND, self.on_erase)
        
    def set_child(self, child):
        self.child = child
        self.sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.sizer.Add(child, proportion=1, flag=wx.EXPAND | self.type, border=1+self.padding)
        self.SetSizerAndFit(self.sizer)

    def on_size(self, evt):
        w,h = self.GetClientSize()
        bitmap = wx.EmptyBitmap(w,h)
        dc = wx.MemoryDC(bitmap)
        dc.SetBackground(wx.WHITE_BRUSH)
        dc.Clear()
        self.dc = dc
        self.draw()
        evt.Skip()
        
    def on_paint(self, evt):
        dc = wx.PaintDC(self)
        if self.dc:
            w, h = self.dc.GetSize()
            dc.Blit(0,0,w,h, self.dc, 0,0)
                    
    def draw(self):
        if self.dc:
            self.dc.Clear()
            w,h = self.dc.GetSize()
            self.dc.SetPen(wx.BLACK_PEN)
            if self.type & wx.TOP:
                self.dc.DrawLine(0,0,w-1,0)
            if self.type & wx.BOTTOM:
                self.dc.DrawLine(0,h-1,w,h-1)
            if self.type & wx.LEFT:
                self.dc.DrawLine(0,0,0,h-1)
            if self.type & wx.RIGHT:
                self.dc.DrawLine(w-1,0,w-1,h-1)
        self.Refresh()
               
def text_cell(parent, label, sides=wx.ALL):
    cell = Cell(parent, type=sides)
    p = wx.Panel(cell)
    st = wx.StaticText(p, label=label)
    st.SetBackgroundColour(wx.RED)
    s = wx.BoxSizer(wx.HORIZONTAL)
    s.AddStretchSpacer(1)
    s.Add(st, 0, wx.CENTER)
    s.AddStretchSpacer(1)
    p.SetSizerAndFit(s)
    cell.set_child(p)
    return cell

class BitFieldControl(wx.Panel):
    
    def __init__(self, parent, value=None, show_bit_numbers=True):
        super(BitFieldControl, self).__init__(parent, -1)
        self.set_value(value)

    def set_value(self, value):
        self.value = value
        sizer = wx.GridBagSizer()
        #sizer.AddGrowableRow(0)        
        nums = []
        for i in range(value.width):
            cell = text_cell(self, str(i), sides=0) 
            sizer.Add(cell, pos=(0,value.width-i-1), flag=wx.EXPAND)
            if i != 0:
                sizer.AddGrowableCol(value.width-i-1)
            nums.append(cell)

        sizer.AddGrowableRow(1)                    
        sizer.AddGrowableRow(2)                    

        mw = 0
        for name, start, length in value.fields:
            pos = value.width-start-length
            span = length
            sides = wx.TOP | wx.BOTTOM | wx.RIGHT
            if pos == 0:
                sides |= wx.LEFT
            cell = text_cell(self, name, sides=sides) 
            sizer.Add(cell, pos=(1, pos), span=(1, span), flag=wx.EXPAND)
            sides = wx.BOTTOM  | wx.RIGHT            
            if pos == 0:
                sides |= wx.LEFT
            cell = text_cell(self, name, sides=sides) 
            w, h = cell.GetSize()
            if w > mw:
                mw = w
            sizer.Add(cell, pos=(2, pos), span=(1, span), flag=wx.EXPAND)
        for cell in nums:
            sizer.SetItemMinSize(cell, (mw, h))
            
        for bit in self.value.empty_slots:
            pos = value.width-bit-1
            sides = wx.TOP | wx.BOTTOM | wx.RIGHT
            if pos == 0:
                sides |= wx.LEFT
            cell = text_cell(self, ' ', sides=sides)
            sizer.Add(cell, pos=(1, value.width-bit-1), flag=wx.EXPAND)
            sides = wx.BOTTOM  | wx.RIGHT
            if pos == 0:
                sides |= wx.LEFT
            cell = text_cell(self, ' ', sides=sides)
            sizer.Add(cell, pos=(2, value.width-bit-1), flag=wx.EXPAND)
        
        self.SetSizerAndFit(sizer)
        
class RegisterEditDialog(wx.Dialog):
    def __init__(self, parent, model, name=None, fullname=None, ):
        wx.Dialog.__init__(self, parent)
        self.model = model
        self.name = name
        self.fullname = fullname
        self.setup()
        
    def setup(self):
        sizer = wx.BoxSizer(wx.VERTICAL)
        if self.name:
            txt_name = wx.StaticText(self, label=self.name)
            f = txt_name.GetFont()
            f.SetPointSize(f.GetPointSize()*2)
            f.SetWeight(wx.FONTWEIGHT_BOLD)
            txt_name.SetFont(f)
            
            sizer.Add(txt_name, border=5, flag=wx.ALL)
        if self.fullname:
            txt_fullname = wx.StaticText(self, label=self.fullname)
            sizer.Add(txt_fullname, border=5, flag=wx.ALL)
        if self.model.width <= 16:
            ctrl = BitFieldControl(self, self.model)
            sizer.Add(ctrl, border=5, flag=wx.ALL)
            
        self.SetSizerAndFit(sizer)
        
    @staticmethod
    def show(parent, model, name=None, fullname=None):
        dlg = RegisterEditDialog(parent, model, name, fullname)
        return dlg.ShowModal()
        
        
        
        
if __name__ == "__main__":
    bitfield = BitField(16)
    bit_names = []
    bitfield.set_bit("EN1",0)
    bitfield.set_bit("BOFF1",1)
    bitfield.set_bit("TEN1",2)
    #bitfield.set_field(3,3, "TSEL")
    bitfield.set_field("WAVE1",6,2)
    bitfield.set_field("MAMP1",8,2)
    bitfield.set_bit( "DMAEN1",12)
    
    app = wx.PySimpleApp()
    frame = wx.Frame(None)
    frame.Show()
    RegisterEditDialog.show(frame, bitfield, "DAC_CR", "DAC Control Register")
    app.MainLoop()
    
