import os 
import util
from options import *
from jinja2 import Environment, PackageLoader
from lxml import etree

SIZES = {'byte':1, 'short':2, 'int':4, '1':1,'2':2,'4':4}

def str2int(s):
    return int(s, 16) if 'x' in s else int(s)

class Group(object):
    def __init__(self, name, items=None):
        self.name=name
        self.items = items or []
    def add_item(self, item):
        self.items.append(item)
                    
class Target(Group):
    @staticmethod
    def load(filename):
        path = os.path.abspath(filename)
        fp = open(path, 'r')
        tree = etree.parse(fp)
        peripherals = Target.__get_peripherals(tree.getroot())
        return Target.__get_target(tree.getroot(), peripherals)
    
    @staticmethod
    def __get_peripherals(root):
        peripherals = {}
        for item in root.iter('peripheral'):
            peripheral_name = item.get('name')
            peripheral = Peripheral()
            for reg in item.iter('reg'):
                print reg
                name, fullname, offset, size = reg.get('name'), reg.get('fullname'), str2int(reg.get('offset')), reg.get('as')
                size = SIZES.get(size.strip().lower(), 4)
                register = SpecialFunctionRegister(name, fullname, offset, size, 'rw')
                peripheral.add_register(register)
            peripherals[peripheral_name] = peripheral
        return peripherals
    
    @staticmethod
    def __get_target(root, peripherals):
        for target_item in root.iter('target'):
            name = target_item.get('name')
            target = Target(name)
            for item in target_item:
                target.add_item(Target.__walk(item, peripherals))
            break
        return target
    @staticmethod
    def __walk(item, peripherals):
        if item.tag == 'group':
            retval = Group(item.get('name'))
            for child in item:
                retval.add_item(Target.__walk(child, peripherals))
        elif item.tag == 'invoke':
            peripheral = peripherals.get(item.get('peripheral'), None)
            if peripheral:
                retval = peripheral.instantiate(item.get('name'), str2int(item.get('base')))
        
        return retval
            
class Peripheral(object):
    def __init__(self, name='', registers=None):
        self.name=name    
        self.registers = registers or []
        
    def add_register(self, register):
        self.registers.append(register)

    def instantiate(self, name, base_addr):
        return Peripheral(name, [register.instantiate(base_addr) for register in self.registers])
        
    def pretty(self):
        retval = "Peripheral '%s'\n" % self.name
        for register in self.registers:
            retval += "%s\n" % register
        return retval

class SpecialFunctionRegister(object):
    def __init__(self, name, fullname, address, size, permissions):
        self.name = name
        self.fullname = fullname or name
        self.address = address
        self.size = size
        self.permissions = permissions
        
    def instantiate(self, base_address):
        return SpecialFunctionRegister(self.name, self.fullname, base_address+self.address, self.size, self.permissions)

    @property
    def expression(self):
        size = {1:"char",2:"short",4:"int"}[self.size]
        return "*((%s*)0x%x)" % (size, self.address)
    
    def __str__(self):
        return '<SFR name="%s" %s0x%x %d %s>' % (self.name, '' if self.fullname == self.name else 'fullname="%s" ' % self.fullname, self.address, self.size, self.permissions)
    
class Project(util.Category):

    def __init__(self, *args, **kwargs):
        '''
        Don't call the constructor directly.  Use Project.create(filename) instead.
        '''
        super(Project, self).__init__(*args, **kwargs)
        self.filename = ''
        # Overview
        general = self.add_category('general')
        general.add_item('project_name', 'Untitled Project')
        general.add_item('project_description', '')
        general.add_item('project_files', [])
        general.add_item('target', '')
        
        # Build
        build = self.add_category('build')
        build.add_item('build_cmd', 'make')
        build.add_item('clean_cmd', 'clean')
        #build.add_item('rebuild_cmd', '"make clean"; make')
        
        # Debug
        debug = self.add_category('debug')
        debug.add_item("gdb_executable","arm-elf-gdb")
        debug.add_item("attach_cmd", "target remote localhost:3333")
        debug.add_item("detach_cmd", "")
        debug.add_item("post_attach_cmd", "monitor_halt")
        debug.add_item("pre_detach_cmd", "")
        debug.add_item("reset_cmd", "monitor reset")
        
        # Program
        program = self.add_category('program')
        program.add_item("target", "build/main.elf")
        program.add_item('entry_point', '_start')
        program.add_item('break_at_main', True)
                
    @staticmethod
    def load(filename):
        path = os.path.abspath(filename)
        fp = open(path, 'r')
        tree = etree.parse(fp)
        project = Project()
        project.filename = path
        project.modified = False
        def walk(current_cat, element):
            for item in element:
                if item.tag == "category":
                    name = item.get('name')
                    if name not in current_cat:
                        cat = current_cat.add_category(name)
                    else:
                        cat = current_cat[name]
                    walk(cat, item)
                elif item.tag == "item":
                    name, value = item.get('name'), item.text.strip()
                    if name not in current_cat:
                        current_cat.add_item(name, eval(value))
                    else:
                        current_cat.add_item(name, eval(value))
                else:
                    pass # We could log an error here or something
        walk(project, tree.getroot())
        project.modified = False
        return project
    
    @staticmethod
    def create(filename):
        project = Project()
        project.filename = os.path.abspath(filename)
        project.save()
        return project
    
    def __get_directory(self):
        return os.path.abspath(os.path.dirname(self.filename))
    directory = property(__get_directory)

    def relative_path(self, dir):
        if not os.path.isabs(dir): return dir
        dir = os.path.abspath(dir)
        project_dir = self.directory
        return util.relpath(dir, project_dir)

    def absolute_path(self, file):
        if os.path.isabs(file): return file
        return os.path.join(self.directory, file)

    def save(self):
        fp = open(self.filename,'wb')
        fp.write(util.project_template.render(category=self))
        fp.close()
        self.modified = False

class ProjectOptionsDialog(OptionsDialog):

    def __init__(self, parent, title="Project Options", size=(600,400), project=None):
        OptionsDialog.__init__(self, parent, title=title, size=size, data=project, icons=["brick.png", "bug.png", "application_view_list.png"])
        self.create_general_panel()
        self.create_build_panel()
        self.create_debug_panel()
        self.create_program_panel()
        
    def create_general_panel(self):
        panel = OptionsPanel(self, "General")
        panel.add("Informations", "Project Name", TextWidget, key="general.project_name")
        self.add_panel(panel, icon='application_view_list.png')
    
    def create_build_panel(self):
        panel = OptionsPanel(self, "Build")
        panel.add("Commands", "Build", TextWidget, key="build.build_cmd")
        panel.add("Commands", "Clean", TextWidget, key="build.clean_cmd")
        #panel.add("Commands", "Rebuild", TextWidget, key="build.rebuild_cmd")
        self.add_panel(panel, icon='brick.png')

    def create_debug_panel(self):
        panel = OptionsPanel(self, "Debug")
        panel.add("General", "GDB Executable", TextWidget, key="debug.gdb_executable")
        panel.add("Commands", "Attach", TextWidget, key="debug.attach_cmd")
        panel.add("Commands", "Detach", TextWidget, key="debug.detach_cmd")
        panel.add("Commands", "Post-Attach", TextWidget, key="debug.post_attach_cmd")
        panel.add("Commands", "Pre-Detach", TextWidget, key="debug.pre_detach_cmd")
        self.add_panel(panel, icon='bug.png')

    def create_program_panel(self):
        panel = OptionsPanel(self, "Program")
        panel.add("Code", "Target Executable", TextWidget, key="program.target")
        panel.add("Locations", "Entry Point", TextWidget, key="program.entry_point")
       # panel.add("Locations", "Break on Main", CheckboxWidget, key="program.break_at_main")
        self.add_panel(panel, icon='chip.png')
        
    @staticmethod
    def show(parent, project=None):
        dialog = ProjectOptionsDialog(parent, project=project)
        dialog.Centre()
        dialog.ShowModal() 

class Session(object):
    def __init__(self):
        self.project_filename = None

if __name__ == "__main__":
    target = Target.load('targets/stm32f103.xml')
    print target.items[0].items