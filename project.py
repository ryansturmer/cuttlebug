import pickle, os 
from odict import OrderedDict

class Category(object):

    def __init__(self, name=''):
        # TODO ordered dict later?
        self.items = dict()
        self.name = str(name)

    def __getstate__(self):
        return self.__dict__

    def __getattr__(self, attr):
        return self.items[str(attr)]

    #def __setattr__(self, attr, val):
    #    self.items[str(attr)] = val
    
    def __getitem__(self, idx):
        names = idx.split(".")
        if len(names) == 1:
            return self.items[idx]
        else:
            next = self.items[names[0]]
            return names[".".join(names[1:])]

    def __setitem__(self, idx, val):
        names = idx.split(".")
        if len(names) == 1:
            self.items[idx] = val
        else:
            next = self.items[names[0]]
            next[".".join(names[1:])] = val

    def add_category(self, name):
        if name in self:
            raise ProjectError("Already a category called '%s'" % name)
        self[name] = Category(name)

    def __iter__(self):
        return iter(self.items)

class Project(Category):

    def __init__(self, project_name="Untitled Project"):
        super(Project, self).__init__()

        # Overview
        self["project_name"] = project_name
        self["files"] = []
        
        # Build Commands
        self.add_category('build')
        self["build.build_cmd"] = "make"
        self["build.clean_cmd"] = "make clean"
        self["build.rebuild_cmd"]= "make clean; make"
        self["build.target"] = "build/main.elf"
        
         
    def fullpath(self, relpath):
        project_path = os.path.dirname(os.path.abspath(self.filename))
        return os.path.join(project_path, relpath)

    def save(self, path=None):
        if not path: path = self.filename
        fp = open(path,'w')
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

    
