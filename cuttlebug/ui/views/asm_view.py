from cuttlebug.ui.controls import ListControl
import view
import wx
import cuttlebug.settings as settings
import cuttlebug.app as app
import cuttlebug.gdb as gdb

def tabify(s):
    TAB_STOP = 5
    retval = []
    for c in s:
        if c != '\t': 
            retval.append(c)
        else: 
            retval.extend([' ']*(TAB_STOP-(len(retval)%TAB_STOP)))
    return ''.join(retval)

class DisassemblyView(view.View):
    def __init__(self, *args, **kwargs):
        super(DisassemblyView, self).__init__(*args, **kwargs)
        self.list = ListControl(self)
        self.list.set_columns(['address', 'instruction'])
        self.list.SetFont(wx.Font(8, wx.FONTFAMILY_MODERN, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
#        self.list.auto_size()
        try:
            self.load_positions()
        except:
            self.list.auto_size()
        self.list.Bind(wx.EVT_LIST_COL_END_DRAG, self.on_col_resize)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.list, 1, wx.EXPAND)
        self.SetSizer(sizer)
 
        self.controller.Bind(app.EVT_APP_TARGET_HALTED, self.on_target_halted)
        self.controller.Bind(app.EVT_APP_TARGET_DISCONNECTED, self.on_gdb_finished)
    
    def on_col_resize(self, evt):
        self.save_positions()
        evt.Skip()
        
    def save_positions(self):
        cols = self.list.GetColumnCount()
        widths = [self.list.GetColumnWidth(i) for i in range(cols)]
        settings.session_set('asm_view_col_widths', widths)

    def load_positions(self):
        widths = settings.session_get('asm_view_col_widths')
        cols = self.list.GetColumnCount()
        if cols != len(widths):
            raise Exception("Wrong number of saved column widths.")
        for i, width, in enumerate(widths):
            self.list.SetColumnWidth(i, width)

    def set_model(self, model):
        self.model = model
        self.model.Bind(gdb.EVT_GDB_FINISHED, self.on_gdb_finished)
    
    def on_gdb_finished(self, evt):
        self.clear()
        evt.Skip()
        
    def on_target_halted(self, evt):
        self.save_positions()
        if self.model:
            self.model.data_disassemble(start_addr="$pc-8", end_addr="$pc+8", callback=self.on_disassembled_data)
        evt.Skip()
        
    def update_assembly(self, instructions):
        self.list.Freeze()
        self.list.clear()
        for i, instruction in enumerate(instructions):
            addr = instruction.address
            inst = tabify(instruction.inst.replace("\\t", "\t"))
            
            self.list.add_item((addr, inst), bgcolor=wx.Colour(255, 255, 0) if i == len(instructions)/2 else wx.WHITE)
        self.list.Thaw()
        
    def on_disassembled_data(self, dat):
        if dat.cls == 'done':
            instructions = dat['asm_insns']
            wx.CallAfter(self.update_assembly, instructions)
    
    def clear(self):
        self.list.clear()
            
if __name__ == "__main__":
    print tabify('abc\tde\tf\tghijkl')
    print tabify('a\t\tbcde\tfg\thi\tjklmnop\tq')