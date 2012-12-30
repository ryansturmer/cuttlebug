import wx
import util
import wx.lib.mixins.listctrl as listmix
from odict import OrderedDict
import functools

EVT_BITFIELD_CHANGED = wx.PyEventBinder(wx.NewEventType())

'''
def show_busy(parent, message, func, *args):
    frame = BusyFrame(parent, message, wx.Bitmap('icons/analyzer_refresh.png'))
    frame.Show()
    def thread_main():
        try:
            func(*args)
        except Exception as exception:
            wx.CallAfter(util.show_exception, parent, exception)
        finally:
            wx.CallAfter(frame.Close)
    util.start_thread(thread_main)
'''

class ModalFrame(wx.Frame):
    def __init__(self, parent):
        style = wx.FRAME_TOOL_WINDOW | wx.BORDER_RAISED
        style |= wx.FRAME_FLOAT_ON_PARENT if parent else wx.STAY_ON_TOP
        super(ModalFrame, self).__init__(parent, -1, '', style=style)
        self.SetBackgroundColour(wx.SystemSettings_GetColour(wx.SYS_COLOUR_BTNFACE))

class BusyFrame(ModalFrame):
    def __init__(self, parent, message, bitmap=None):
        super(BusyFrame, self).__init__(parent)
        self.Bind(wx.EVT_CLOSE, self.on_close)
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        if bitmap:
            bitmap = wx.StaticBitmap(self, -1, bitmap)
            sizer.Add(bitmap, 0, wx.RIGHT|wx.ALIGN_CENTER_VERTICAL, 15)
        
        #bitmap = throb.Throbber(self, -1, util.get_icon('download_anim.png'), frames=8, frameWidth=48, frameDelay=0.1)
        #bitmap.Start()
        #sizer.Add(bitmap, 0, wx.RIGHT|wx.ALIGN_CENTER_VERTICAL, 15)
        
        text = wx.StaticText(self, -1, message)
        text.Wrap(300)
        sizer.Add(text, 0, wx.ALIGN_CENTER_VERTICAL)
        wrapper = wx.BoxSizer(wx.VERTICAL)
        wrapper.Add(sizer, 1, wx.EXPAND|wx.ALL, 15)
        self.SetSizerAndFit(wrapper)
        self.CenterOnParent()
        if parent:
            parent.Disable()
    def on_close(self, event):
        event.Skip()
        parent = self.GetParent()
        if parent:
            parent.Enable()

class BusyMenuBar(wx.MenuBar):
    pass

class StatusBar(wx.StatusBar):
    ICON = 0
    TEXT = 1
    LINE = 2
    STATE = 3
    GAUGE = 4
    
    NONE = "blank.png"
    CONNECTED = "status_connected.png"
    RUNNING = "status_running.png"
    DISCONNECTED = "status_disconnected.png"
    
    def __init__(self, *args, **kwargs):
        super(StatusBar, self).__init__(*args, **kwargs)
        self.SetFieldsCount(5)
        self.SetStatusWidths([18, -24,-2,-8,-8])
        self.staticbmp = None
        self.load_icons()
        
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

    def load_icons(self):
        self.icon_names = [StatusBar.NONE, StatusBar.CONNECTED, StatusBar.DISCONNECTED, StatusBar.RUNNING]
        self.icons = dict([(key,util.get_icon(key)) for key in self.icon_names])
        self.staticbmps = {}
        for key in self.icon_names:
            self.staticbmps[key] = wx.StaticBitmap(self, -1, self.icons[key])
            self.staticbmps[key].Hide()

    def __set_line(self, line=0):
        if line:
            self._line = int(line)
            if self._line < 0:
                line = "???"
            wx.CallAfter(self.SetStatusText, str(line), self.LINE)
        else:
            self._line = 0
            wx.CallAfter(self.SetStatusText,'', self.LINE)
            
    def __get_line(self): return self._line
    line = property(__get_line, __set_line)
    
    def set_icon(self, key):
        if self.staticbmp:
            self.staticbmp.Hide()
        self.staticbmp = self.staticbmps[key]
        wx.CallAfter(self.staticbmp.Show()) 
        wx.CallAfter(self.Reposition)


    def set_state(self, text, blink=False, color=wx.BLACK):
        #TODO Put COLOR support in here
        self._state = text
        if text and blink:
            self.state_timer.Start(500)
        else:
            self.state_timer.Stop()
        wx.CallAfter(self.SetStatusText, text, self.STATE)
        
    def get_state(self): return self._state
    
    def __set_text(self, text):
        self.__text = text
        wx.CallAfter(self.SetStatusText,str(text), self.TEXT)
    def __get_text(self):
        return self.__text
    text = property(__get_text, __set_text)

    def __set_working(self, working):
        self.__working = bool(working)
        if self.__working: 
            wx.CallAfter(self.gauge.Pulse)
            wx.CallAfter(self.work_timer.Start,100)
        else:
            pass
            #wx.CallAfter(self.work_timer.Stop)
            #wx.CallAfter(self.gauge.SetValue,0)
    
    def __get_working(self):
        return self.__working
    working = property(__get_working, __set_working)

    def on_work_timer(self, evt):
        if self.__working:
            self.gauge.Pulse()
        else:
            print "stopped timer"
            self.gauge.SetValue(0)
            self.gauge.Pulse()
            self.work_timer.Stop()
            
            
    def on_state_timer(self, evt):
        if self.state_on:
            self.state_on = False
            self.SetStatusText(self._state, self.STATE)
        else:
            self.state_on = True
            self.SetStatusText("", self.STATE)
            
    def on_idle(self, evt):
        pass
        #if self.size_changed:
        #    self.Reposition()

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
        self.staticbmp.SetSize((rect.height-4, rect.height-4))
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
        
        if self.model and self.model.fullname and self.model.fullname != self.model.name:
            self.SetToolTipString(self.model.fullname)
        self.update()
    
    def make_menu(self):
        self.menu = wx.Menu()
        util.menu_item(self, self.menu, "Decimal", functools.partial(self.on_change_display_type, type=DEC))
        util.menu_item(self, self.menu, "Hex", functools.partial(self.on_change_display_type, type=HEX))
        util.menu_item(self, self.menu, "Bin", functools.partial(self.on_change_display_type, type=BIN))
    
    def on_change_display_type(self, evt, type=DEC):
        self.display_type = type
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

    def render_value(self):
        v = self.model.get_value()
        if self.display_type == HEX:
            return ("0x%x" % v) if v else '0'
        elif self.display_type == BIN:
            s = ''
            while v:
                s = ('1' if v & 1 else '0') + s
                v >>= 1
            return '0b%s' % s if s else '0'
        else:
            return str(v)

    def update(self):
        if self.model:
            self.text.SetLabel(self.render_value())
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
            self.SetFocus()
            self.set_value(0 if self.get_value() else 1)
            self.update()
        else:
            self.edit()

    def on_enter(self, evt):
        try:
            self.set_value(util.str2int(self.ctrl.GetValue()))
        except:
            pass
        self.unedit()

    def on_lost_focus(self, evt):
        self.unedit()
        
    def on_right_click(self, evt):
        self.PopupMenu(self.menu)
   
PADDING = 10     
class BitFieldControl(wx.Panel):
    
    def __init__(self, parent, value, start=0, width=None, show_bit_numbers=True):
        super(BitFieldControl, self).__init__(parent, -1)
        self.number_cells = []
        self.field_cells = []
        self.entry_cells = []
        self.default_min_cell_width = 0
        self.width = value.width if width == None else width
        self.start = start
        self.__setup(value)
        
    def cell_changed(self, cell):
        event = util.Event(self, EVT_BITFIELD_CHANGED)
        wx.PostEvent(self, event)

    def bit2cell(self, x):
        r = self.width-(x-self.start)-1
        return r
    
    def update(self):
        for cell in self.entry_cells:
            cell.update()
    
    def __compute_field_positions(self):
        value = self.value
        retval = {}
        bits = set(range(self.start, self.start+self.width))
        for field in value.fields:
            start = field.start
            length = field.length
            # Adjust the length of the field if part of it is outside the range we're displaying
            field_bits = set(range(start, start+length))
            field_bits_in_this_reg = field_bits.intersection(bits)
            if len(field_bits_in_this_reg) != len(field_bits): 
                if not field_bits_in_this_reg: continue   
                start, end = min(field_bits_in_this_reg), max(field_bits_in_this_reg)
                length = len(field_bits_in_this_reg)
            pos = self.width-(start-self.start)-length
            span = length
            retval[field] = (pos, span)
        return retval
    
    def __compute_field_sizes(self):
        mw,mh = 0,0
        for cell in self.number_cells + self.field_cells + self.entry_cells:
            w,h = cell.GetSize()
            mw = (w+PADDING) if (w+PADDING) > mw else mw
            mh = h if h > mh else mh
        return mw, mh
    
    def __setup(self, value):
        self.value = value
        sizer = wx.GridBagSizer()
        sizer.AddGrowableRow(1)                    
        sizer.AddGrowableRow(2)                    

        mh = 0
        mw = 0
        for i in range(self.start, self.start+self.width):
            cell = BitFieldCell(self, None, label=str(i), sides=0, bgcolor=None) 
            sizer.Add(cell, pos=(0,self.bit2cell(i)), flag=wx.EXPAND)
            if i != 0:
                sizer.AddGrowableCol(self.bit2cell(i))
            self.number_cells.append(cell)

        for field, (pos, span) in self.__compute_field_positions().items():
            sides = wx.TOP | wx.BOTTOM | wx.RIGHT
            if pos == 0:
                sides |= wx.LEFT
            cell = BitFieldCell(self, None,label=field.name, sides=sides, bgcolor=wx.WHITE) 
            sizer.Add(cell, pos=(1, pos), span=(1, span), flag=wx.EXPAND)
            self.field_cells.append(cell)
            if field.fullname and field.fullname != field.name:
                cell.SetToolTipString(field.fullname)

            sides &= ~wx.TOP
            cell = BitFieldCell(self, field,sides=sides, bgcolor=wx.WHITE) 
            sizer.Add(cell, pos=(2, pos), span=(1, span), flag=wx.EXPAND)
            self.entry_cells.append(cell)
            mh = cell.max_height

        mw, xx = self.__compute_field_sizes()
        
        for cell in self.number_cells:
            sizer.SetItemMinSize(cell, (mw, -1))
        for cell in self.field_cells + self.entry_cells:
            sizer.SetItemMinSize(cell, (mw, mh))

        def empty_slots(reg, start, width):
            full_slots = set()
            for field in reg.fields:
                for i in range(field.start, field.start+field.length):
                    full_slots.add(i)
            return set(range(start, start+width)) - full_slots

        for bit in empty_slots(self.value, self.start, self.width):
            pos = self.bit2cell(bit)
            sides = wx.TOP | wx.BOTTOM | wx.RIGHT
            if pos == 0:
                sides |= wx.LEFT
            cell = BitFieldCell(self, None, label=' ', sides=sides, bgcolor=wx.WHITE)
            sizer.Add(cell, pos=(1, self.bit2cell(bit)), flag=wx.EXPAND)
            
            sides &= ~wx.TOP
            cell = BitFieldCell(self, None, label='X', sides=sides, bgcolor=wx.WHITE)
            sizer.Add(cell, pos=(2, self.bit2cell(bit)), flag=wx.EXPAND)
        
        self.SetSizerAndFit(sizer)
        
class RegisterEditDialog(wx.Dialog):
    def __init__(self, parent, model, max_width=16):
        wx.Dialog.__init__(self, parent)
        self.model = model
        self.name = model.name
        self.fullname = model.fullname
        self.max_width = max_width
        self.SetTitle(self.fullname if self.fullname else self.name)
        self.setup()
        
    def setup(self):
        sizer = wx.BoxSizer(wx.VERTICAL)

        # Text
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
        
        # Bit Fields
        if self.max_width:
            fields = self.model.width/self.max_width or 1
        else:
            fields = 1
        ctrls = []
        for i in reversed(range(fields)):
            ctrl = BitFieldControl(self, self.model, start=i*self.max_width, width=self.model.width/fields)
            sizer.Add(ctrl, border=10, flag=wx.ALL | wx.CENTER | wx.EXPAND)
            ctrl.Bind(EVT_BITFIELD_CHANGED, self.on_bitfield_changed)
            ctrls.append(ctrl)
        self.ctrls = ctrls
        
        # Buttons
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
        self.SetSizerAndFit(sizer)
        self.CenterOnParent()
        
    @staticmethod
    def show(parent, model, max_width=16):
        top_parent = parent
        while top_parent.GetParent():
            top_parent = top_parent.GetParent()
        
        dlg = RegisterEditDialog(top_parent, model, max_width)
        return dlg.ShowModal()

    def set_value(self):
        if hasattr(self.model, 'address'):
            s = "Value: 0x%0*x (@ 0x%0*x)" % (self.model.width/4, self.model.value, 8, self.model.address)
        else:
            s = "Value: 0x%0*x" % (self.model.width/4, self.model.value)
        self.txt_value.SetLabel(s)

    def set_address(self):
        fmt = "(0x%0*d)" % (8, self.model.address)
        self.txt_address.SetLabel(fmt)
        
    def on_bitfield_changed(self, evt):
        for ctrl in self.ctrls:
            ctrl.update()
        self.set_value()
        
        
if __name__ == "__main__":
    '''
    import project
    
    print "Loading target file to test register editor:" 
    
    target = project.Target.load('targets/stm32f103.xml')
    
    usb_peripheral = target.find_by_name('GPIOA')
    for register in usb_peripheral.registers:
        if register.name == 'FNR':
            break
    print register
    for field in register.fields:
        print field
    
    register = project.SpecialFunctionRegister("SMPR", "Sample Register", 0x1000, 4, 'rw')
    
    register.add_field(project.Field(0, 3, "FA", "Field A"))
    register.add_field(project.Field(3, 10, "FB", "Field B"))
    register.add_field(project.Field(13, 1, "FC", "Field C"))
    register.add_field(project.Field(14, 8, "FD", "Field D"))
    
    register = project.CPURegister("CPSR", "Current program status register", 4)
    register.add_field(project.Field(0, 3, "FA", "Field A"))
    register.add_field(project.Field(3, 10, "FB", "Field B"))
    register.add_field(project.Field(13, 1, "FC", "Field C"))
    register.add_field(project.Field(14, 8, "FD", "Field D"))
    
    print "Initial Register Value: 0x%x" % register.value
    app = wx.PySimpleApp()
    frame = wx.Frame(None)
    RegisterEditDialog.show(frame, register)
    print "Final Register Value 0x%x" % register.value
    frame.Close()
    app.MainLoop()
    '''
    app = wx.PySimpleApp()
    frame = BusyFrame(None, 'This is a modal frame for presenting information to the user during a long-running task.', wx.ArtProvider_GetBitmap(wx.ART_INFORMATION))
    frame.Show()
    app.MainLoop()
