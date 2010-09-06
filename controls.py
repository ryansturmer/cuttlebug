import wx
import util
import wx.lib.mixins.listctrl as listmix
from odict import OrderedDict

EVT_BITFIELD_CHANGED = wx.PyEventBinder(wx.NewEventType())

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
    
    def __init__(self, width, start=0, value=0):
        self.width = width
        self.start = start
        value=value
        self.fields = {}
        
    def set_bit(self, name, bit, value=0):
        self.set_field(name, bit, value=value)
        
    def set_field(self, name, start, length=1, value=0):
        if start < self.start or (start+length) > self.width:
            raise ValueError("Cannot set bit %d of a %d bit field.") % (start+length, self.width)
        self.fields[(start, length)] = (name, 0)
        self.set_field_value(start, length, value)

    def set_field_value(self, start, length, val):
        n, v = self.fields[(start, length)]
        val = ((1 << length) -1) & val 
        self.fields[(start, length)] = (n, val)

    def get_field_value(self, start, length):
        return self.fields[(start, length)][1]
    def get_field_name(self, start, length):
        return self.fields[(start, length)][0]

    @property             
    def empty_slots(self):
        full_slots = set()
        for (start, length), (name, value) in self.fields.items():
            for i in range(start, start+length):
                full_slots.add(i)
        return set(range(self.width)) - full_slots
    
        
    @property
    def value(self):
        v = 0
        for (start, length), (name, value) in self.fields.items():
            v |= int(value) << start
        return v
    
    
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
               
DEC = 0
HEX = 1
BIN = 2

class BitFieldCell(Cell):
    def __init__(self, parent, model, label=None, sides=wx.ALL, bgcolor=wx.WHITE):
        Cell.__init__(self, parent, type=sides)
        self.display_type = DEC

        self.label = label
        self.bgcolor = bgcolor
        p = wx.Panel(self)
        if bgcolor:
            p.SetBackgroundColour(bgcolor)
        self.panel = p
        st = wx.StaticText(p, label=label if not model else '')
        tc = wx.TextCtrl(p, style=wx.TE_PROCESS_ENTER | wx.TE_CENTRE | wx.BORDER_NONE)
        self._edit_mode = False
        if model:
            p.Bind(wx.EVT_LEFT_DOWN, self.on_click)
            st.Bind(wx.EVT_LEFT_DOWN, self.on_click)
            if model.length > 1:
                p.Bind(wx.EVT_RIGHT_DOWN, self.on_right_click)
                st.Bind(wx.EVT_RIGHT_DOWN, self.on_right_click)
                self.make_menu()

            tc.Bind(wx.EVT_TEXT_ENTER, self.on_enter)
            tc.Bind(wx.EVT_KILL_FOCUS, self.on_lost_focus)

        self.text = st
        self.ctrl = tc
        tc.Hide()
        s = wx.BoxSizer(wx.HORIZONTAL)
        s.AddStretchSpacer(1)
        s.Add(st, 0, wx.CENTER | wx.ALIGN_CENTRE_VERTICAL)
        s.Add(tc, 0, wx.CENTER | wx.ALIGN_CENTRE_VERTICAL)
        s.AddStretchSpacer(1)
        p.SetSizerAndFit(s)
        
        self.model = model
        
        self.max_height = tc.GetSize()[1] if model else st.GetSize()[1] 
        self.set_child(p)
        self.update()
    
    def make_menu(self):
        self.menu = wx.Menu()
        util.menu_item(self, self.menu, "Decimal", self.on_dec)
        util.menu_item(self, self.menu, "Hex", self.on_hex)
        util.menu_item(self, self.menu, "Bin", self.on_bin)
    
    def on_dec(self, evt):
        self.display_type = DEC
        self.update()

    def on_hex(self, evt):
        self.display_type = HEX
        self.update()

    def on_bin(self, evt):
        self.display_type = BIN
        self.update()
        
    def edit(self):
        self.Freeze()
        self.update()
        self.text.Hide()
        self.ctrl.Show()
        self.ctrl.SetFocus()
        self.ctrl.SetValue(self.text.GetLabel())
        self.ctrl.SelectAll()
        self.Layout()
        self.Thaw()

    def unedit(self):
        self.Freeze()
        self.update()
        self.ctrl.Hide()
        self.text.Show()
        self.Layout()
        self.Thaw()

    def update(self):
        if self.model:
            value = self.model.get_value()
            
            if self.display_type == HEX:
                s = "0x%x" % value
            elif self.display_type == BIN:
                s = self.bin(value)
            else:
                s = str(value)
                
            self.text.SetLabel(s)
        else:
            self.text.SetLabel(self.label)
        self.Layout()

    def get_value(self):
        return self.model.get_value()

    def set_value(self, x):
        try:
            self.GetParent().cell_changed(self)
        except:
            raise
        self.model.set_value(x)
    def on_click(self, evt):
        if self.model.length == 1:
            self.set_value(0 if self.get_value() else 1)
            self.update()
        else:
            self.edit()

    def on_enter(self, evt):
        try:
            self.set_value(self.convert_int(self.ctrl.GetValue()))
        except:
            pass
        self.unedit()

    def convert_int(self, s):
        if 'x' in s:
            return int(s, 16)
        elif 'b' in s:
            return int(s, 2)
        else:
            return int(s)
        
    def bin(self, x):
        s = ''
        while x:
            s = ('1' if x & 1 else '0') + s
            x >>= 1
        if not s:
            return '0b0'
        else:
            return '0b%s' % s
        
    def on_lost_focus(self, evt):
        self.unedit()
        
    def on_right_click(self, evt):
        self.PopupMenu(self.menu)
        
class BitFieldControl(wx.Panel):
    
    def __init__(self, parent, value=None, show_bit_numbers=True):
        super(BitFieldControl, self).__init__(parent, -1)
        self.__set_value(value)

    def cell_changed(self, cell):
        event = util.Event(self, EVT_BITFIELD_CHANGED)
        wx.PostEvent(self, event)

    def __set_value(self, value):
        self.value = value
        sizer = wx.GridBagSizer()
        #sizer.AddGrowableRow(0)        
        nums = []
        for i in range(value.width):
            cell = BitFieldCell(self, None, label=str(i), sides=0, bgcolor=None) 
            sizer.Add(cell, pos=(0,value.width-i-1), flag=wx.EXPAND)
            if i != 0:
                sizer.AddGrowableCol(value.width-i-1)
            nums.append(cell)

        sizer.AddGrowableRow(1)                    
        sizer.AddGrowableRow(2)                    
        field_cells = []
        mh = 0
        mw = 0
        for field in value.fields:
            start = field.start
            length = field.length
            name = field.name
            pos = value.width-start-length
            span = length
            sides = wx.TOP | wx.BOTTOM | wx.RIGHT
            if pos == 0:
                sides |= wx.LEFT
            cell = BitFieldCell(self, None,label=name, sides=sides, bgcolor=wx.WHITE) 
            #cell = text_cell(self, label=name, sides=sides, bgcolor=wx.WHITE)
            sizer.Add(cell, pos=(1, pos), span=(1, span), flag=wx.EXPAND)
            w, h = cell.GetSize()
            if w > mw:
                mw = w
            sides &= ~wx.TOP
            cell = BitFieldCell(self, field,sides=sides, bgcolor=wx.WHITE) 
            field_cells.append(cell)
            mh = cell.max_height
            sizer.Add(cell, pos=(2, pos), span=(1, span), flag=wx.EXPAND)

        for cell in nums:
            sizer.SetItemMinSize(cell, (mw+10, mh))
        for cell in field_cells:
            sizer.SetItemMinSize(cell, (mw+10, mh))

        def empty_slots(reg):
            full_slots = set()
            for field in reg.fields:
                for i in range(field.start, field.start+field.length):
                    full_slots.add(i)
            return set(range(reg.width)) - full_slots

        for bit in empty_slots(self.value):
            pos = value.width-bit-1
            sides = wx.TOP | wx.BOTTOM | wx.RIGHT
            if pos == 0:
                sides |= wx.LEFT
            cell = BitFieldCell(self, None, label=' ', sides=sides, bgcolor=wx.WHITE)
            sizer.Add(cell, pos=(1, value.width-bit-1), flag=wx.EXPAND)
            sides &= ~wx.TOP
            cell = BitFieldCell(self, None, label='X', sides=sides, bgcolor=wx.WHITE)
            sizer.Add(cell, pos=(2, value.width-bit-1), flag=wx.EXPAND)
        
        self.SetSizerAndFit(sizer)
        
class RegisterEditDialog(wx.Dialog):
    def __init__(self, parent, model):
        wx.Dialog.__init__(self, parent)
        self.model = model
        self.name = model.name
        self.fullname = model.fullname
        self.SetTitle(self.fullname if self.fullname else name)
        self.setup()
        
    def setup(self):
        sizer = wx.BoxSizer(wx.VERTICAL)
        if self.name:
            txt_name = wx.StaticText(self, label=self.name)
            f = txt_name.GetFont()
            f.SetPointSize(f.GetPointSize()*1.5)
            f.SetWeight(wx.FONTWEIGHT_BOLD)
            txt_name.SetFont(f)
            
            sizer.Add(txt_name, border=5, flag=wx.ALL)
        self.txt_value = wx.StaticText(self)
        self.set_value()
        f = self.txt_value.GetFont()
        f.SetWeight(wx.FONTWEIGHT_BOLD)
        self.txt_value.SetFont(f)
        sizer.Add(self.txt_value, border=5, flag=wx.ALL)

        if self.fullname:
            txt_fullname = wx.StaticText(self, label=self.fullname)
            sizer.Add(txt_fullname, border=5, flag=wx.ALL)
            
        ctrl = BitFieldControl(self, self.model)
        sizer.Add(ctrl, border=10, flag=wx.ALL)
           
        p = wx.Panel(self)
        ps = wx.BoxSizer(wx.HORIZONTAL)
        ps.AddStretchSpacer(1)
        cancel = wx.Button(p, wx.ID_CANCEL)
        ps.Add(cancel, 0, border=5, flag=wx.ALL)
        ok = wx.Button(p, wx.ID_OK)
        ok.SetDefault()
        ps.Add(ok, 0, border=5, flag=wx.ALL)
        p.SetSizer(ps)
        sizer.Add(p, flag=wx.EXPAND)
        ctrl.Bind(EVT_BITFIELD_CHANGED, self.on_bitfield_changed)
        self.SetSizerAndFit(sizer)
        
    @staticmethod
    def show(parent, model, name=None, fullname=None):
        dlg = RegisterEditDialog(parent, model)
        return dlg.ShowModal()

    def set_value(self):
        fmt = "Value: 0x%%0%dx" % (self.model.width/4)
        self.txt_value.SetLabel(fmt % self.model.value)
        
    def on_bitfield_changed(self, evt):
        self.set_value()
        
        
if __name__ == "__main__":
    
    import project
    print "Loading target file to test register editor:" 
    target = project.Target.load('targets/stm32f103.xml')
    
    usb_peripheral = target.find_by_name('USB')
    for register in usb_peripheral.registers:
        if register.name == 'FNR':
            break
    print register
    for field in register.fields:
        print field

    print "Initial Register Value: 0x%x" % register.value
    app = wx.PySimpleApp()
    frame = wx.Frame(None)
    RegisterEditDialog.show(frame, register)
    print "0x%x" % register.value
    app.Exit()
    app.MainLoop()
