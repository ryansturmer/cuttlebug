import pickle, os 
from odict import OrderedDict
import util
from options import *

class Project(util.Category):

    def __init__(self, *args, **kwargs):
        super(Project, self).__init__(*args, **kwargs)
        self.filename = ''
        # Overview
        self.add_category('general')
        self["general.project_name"] = "Untitled Project"
        self["general.project_description"] = ""
        self["general.files"] = []
        
        # Build
        self.add_category('build')
        self["build.build_cmd"] = "make"
        self["build.clean_cmd"] = "make clean"
        self["build.rebuild_cmd"]= "make clean; make"
        
        # Debug
        self.add_category('debug')
        self["debug.gdb_executable"] = "arm-elf-gdb"
        self["debug.attach_cmd"] = "target async localhost:3333"
        self["debug.detach_cmd"] = ""
        self["debug.post_attach_cmd"] = "monitor halt"
        self["debug.pre_detach_cmd"] = ""
        self["debug.target"] = "build/main.elf"
        
    @staticmethod
    def load(filename):
        path = os.path.abspath(filename)
        fp = open(path, 'r')
        object = pickle.load(fp)
        fp.close()
        if not isinstance(object, Project):
            raise Exception("Could not load %s.  It does not appear to be a project file." % filename)
        object.filename = path
        object.modified = False
        return object
    
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
        pickle.dump(self, fp)
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

 
