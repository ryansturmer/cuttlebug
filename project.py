import pickle, os 
from odict import OrderedDict
import util

class Category(object):

    def __init__(self, name='', parent=None):
        # TODO ordered dict later?
        self.items = dict()
        self.name = str(name)
        #self.parent = parent
        self.__modified = False
        self.modified = False
    '''
    def __get_modified(self):
        return self.__modified

    def __set_modified(self, x):
        self.__modified = bool(x)
        if self.modified and self.parent:
            self.parent.modified = True
    modified = property(__get_modified, __set_modified)
    '''

    def reset(self):
        self.modified = False
    
    #def __getstate__(self):
    #    return self.__dict__

    def __getattr__(self, attr):
        try:
            return self.items[str(attr)]
        except:
            raise AttributeError()
    
    #def __setattr__(self, attr, val):
    #    self.items[str(attr)] = val
    
    def __getitem__(self, idx):
        names = idx.split(".")
        if len(names) == 1:
            return self.items[idx]
        else:
            next = self.items[names[0]]
            return next[".".join(names[1:])]

    def __setitem__(self, idx, val):
        names = idx.split(".")
        if len(names) == 1:
            self.items[idx] = val
            self.modified = True
        else:
            next = self.items[names[0]]
            next[".".join(names[1:])] = val

    def add_category(self, name):
        if name in self:
            raise ProjectError("Already a category called '%s'" % name)
        self[name] = Category(name)
        self.modified = True

    def __iter__(self):
        return iter(self.items)

class Project(Category):

    def __init__(self):
        super(Project, self).__init__()
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
        self.add_category('debug_session')
        self["debug_session.gdb_executable"] = "arm-elf-gdb"
        self["debug_session.attach_cmd"] = "target remote localhost:3333"
        self["debug_session.detatch_cmd"] = ""
    
    @staticmethod
    def load(filename):
        path = os.path.abspath(filename)
        fp = open(path, 'r')
        object = pickle.load(fp)
        fp.close()
        if not isinstance(object, Project):
            raise Exception("Could not load %s.  It does not appear to be a project file." % filename)
        object.filename = path
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

    def save(self):
        fp = open(self.filename,'w')
        pickle.dump(self, fp)
        fp.close()

class Session(object):

    def __init__(self):
        self.project_filename = None
        self.perspective = None


def save(object, filename):
        try:
            del(object.filename)
        except:
            pass
        fp = open(os.path.abspath(filename),'w')
        pickle.dump(object, fp)
        fp.close()

def load(filename):
    path = os.path.abspath(filename)
    fp = open(path, 'r')
    object = pickle.load(fp)
    fp.close()
    object.filename = path
    return object 
