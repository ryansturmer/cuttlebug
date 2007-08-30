import wx
import wx.stc as stc
import controls, styles
import view
import re

class BuildPortalControl(stc.StyledTextCtrl):
    def __init__(self, *args, **kwargs):
        self.controller = kwargs.pop('controller')
        super(BuildPortalControl, self).__init__(*args, **kwargs)
        self.manager = self.controller.style_manager
        self.SetLexer(stc.STC_LEX_CONTAINER)
        self.apply_styles(self.manager.build_styles)
        self.SetReadOnly(False)
        self.SetCaretPeriod(0)
        self.SetCaretForeground(self.GetBackgroundColour())
        self.styler = BuildStyler()
        self.Bind(wx.EVT_LEFT_DOWN, self.on_click)
        
    def apply_styles(self, styles):
        for style in styles:
            self.apply_style(style)

    def apply_style(self, style):
        s = style
        id = s.number
        self.StyleSetFontAttr(id, s.size, s.font, s.bold, s.italic, s.underline)
        self.StyleSetBackground(id, s.create_background())
        self.StyleSetForeground(id, s.create_foreground())        

    def update(self, text):
        self.SetReadOnly(False)
        self.AddStyledText(self.styler.style(text))
        self.SetReadOnly(True)
        
    def clear(self):
        self.styler.reset()
        self.SetReadOnly(False)
        self.ClearAll()
        self.SetReadOnly(True)
        
    def on_click(self, event):
        point=event.GetPosition()
        pos = self.PositionFromPoint(point)
        location = self.styler.hit_test(pos)
        if location:
            self.controller.goto(*location)
        event.Skip()
        
class BuildStyler(object):
    
    def __init__(self):
        self.re_warning = re.compile('.*\swarning\:.*')
        self.re_error = re.compile('.*\serror\:.*')
        self.re_link = re.compile('\A(.*)\:([0-9]+)')
        self.reset()
        
    def reset(self):
        self.idx = 0
        self.link_ranges = {}
        
    def __add_style_bytes(self, txt, byte):
        string = []
        style_char = chr(byte)
        for char in txt:
            string.append(char)
            string.append(style_char)
        return string
    
    def __update_style_bytes(self, txt, byte, start, end):
        for i in range(start, end):
            txt[i*2 + 1] = chr(byte)
        return txt
    
    def __search(self, regexp, text):
        i = regexp.finditer(text)
        return [(match.start(), match.end()) for match in i]
            
    def hit_test(self, pos):
        link_ranges = self.link_ranges
        for (a,b), location in link_ranges.iteritems():
            if pos >= a and pos <= b:
                return location
        return None
    
    def style(self, txt):
        # Style ranges to be applied, in order
        s = []
        # Classify the whole line as either a warning, an error, or neither
        if self.re_warning.match(txt):
            s.append((styles.STYLE_BUILD_WARNING, self.__search(self.re_warning, txt)))
        elif self.re_error.match(txt):
            s.append((styles.STYLE_BUILD_ERROR, self.__search(self.re_error, txt)))

        # Find links
        matches = self.re_link.finditer(txt)
        idx = self.idx
        link_ranges = []
        hittest_ranges = self.link_ranges
        for match in matches:
            a,b = match.start(), match.end()
            link_ranges.append((a, b))
            hittest_ranges[(a+idx, b+idx)] = (match.group(1), int(match.group(2)))
            
        s.append((styles.STYLE_BUILD_LINK, link_ranges))
        
        exp_txt = self.__add_style_bytes(txt, styles.STYLE_BUILD_DEFAULT)
        for byte, ranges in s:
            for range in ranges:
                exp_txt = self.__update_style_bytes(exp_txt, byte, *range)
        self.idx += len(txt)
        return ''.join(exp_txt)
    
class BuildView(wx.Panel):

    def __init__(self, parent, controller):
        super(BuildView, self).__init__(parent, -1, style=wx.BORDER_STATIC, size=(800,150))
        self.controller = controller
        self.txt = BuildPortalControl(self, -1, controller=self.controller)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.txt, 1, wx.EXPAND)
        self.SetSizer(sizer)
        
    def update(self, new_text):
        self.txt.update(new_text)
    
    def clear(self):
        self.txt.clear()


if __name__ == "__main__":
    import test
    test.test_view(BuildView)
