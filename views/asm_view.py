from controls import ListControl
import view
import wx
class DisassemblyView(view.View):
    def __init__(self, *args, **kwargs):
        super(DisassemblyView, self).__init__(*args, **kwargs)
        self.list = ListControl(self)
        self.list.set_columns(['address', 'instruction'])
        self.list.SetFont(wx.Font(8, wx.FONTFAMILY_MODERN, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
        self.list.auto_size()
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.list, 1, wx.EXPAND)
        self.SetSizer(sizer)

    def set_model(self, model):
        self.model = model

    def on_target_halted(self, a, b):
        print a
        print b
        if self.model:
            self.model.data_disassemble(start_addr="$pc-8", end_addr="$pc+8", callback=self.on_disassembled_data)
         
    def update_assembly(self, instructions):
        self.list.Freeze()
        self.list.clear()
        for i, instruction in enumerate(instructions):
            addr = instruction.address
            inst = instruction.inst.replace("\\t", "\t")
            self.list.add_item((addr, inst), bgcolor=wx.Colour(255, 255, 0) if i == len(instructions)/2 else wx.WHITE)
        self.list.Thaw()
        
    def on_disassembled_data(self, dat):
        if dat.cls == 'done':
            instructions = dat['asm_insns']
            wx.CallAfter(self.update_assembly, instructions)