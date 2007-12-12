import pickle, os 
from odict import OrderedDict
import util
from options import *
from jinja2 import Environment, PackageLoader
from lxml import etree

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
        
        # Build
        build = self.add_category('build')
        build.add_item('build_cmd', 'make')
        build.add_item('clean_cmd', 'clean')
        build.add_item('rebuild_cmd', '"make clean"; make')
        
        # Debug
        debug = self.add_category('debug')
        debug.add_item("gdb_executable","arm-elf-gdb")
        debug.add_item("attach_cmd", "target async localhost:3333")
        debug.add_item("detach_cmd", "")
        debug.add_item("post_attach_cmd", "monitor_halt")
        debug.add_item("pre_detach_cmd", "")
        debug.add_item("target", "build/main.elf")
                
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
                        current_cat[name] = eval(value)
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

    def create_general_panel(self):
        panel = OptionsPanel(self, "General")
        panel.add("Informations", "Project Name", TextWidget, key="general.project_name")
        self.add_panel(panel, icon='application_view_list.png')
    
    def create_build_panel(self):
        panel = OptionsPanel(self, "Build")
        panel.add("Commands", "Build", TextWidget, key="build.build_cmd")
        panel.add("Commands", "Clean", TextWidget, key="build.clean_cmd")
        panel.add("Commands", "Rebuild", TextWidget, key="build.rebuild_cmd")
        self.add_panel(panel, icon='brick.png')

    def create_debug_panel(self):
        panel = OptionsPanel(self, "Debug")
        panel.add("General", "GDB Executable", TextWidget, key="debug.gdb_executable")
        panel.add("General", "Target", TextWidget, key="debug.target")
        panel.add("Commands", "Attach", TextWidget, key="debug.attach_cmd")
        panel.add("Commands", "Detach", TextWidget, key="debug.detach_cmd")
        panel.add("Commands", "Post-Attach", TextWidget, key="debug.post_attach_cmd")
        panel.add("Commands", "Pre-Detach", TextWidget, key="debug.pre_detach_cmd")
        self.add_panel(panel, icon='bug.png')

    @staticmethod
    def show(parent, project=None):
        dialog = ProjectOptionsDialog(parent, project=project)
        dialog.Centre()
        dialog.ShowModal() 

class Session(object):
    def __init__(self):
        self.project_filename = None

if __name__ == "__main__":
	Project.create('test_project.xml') 
