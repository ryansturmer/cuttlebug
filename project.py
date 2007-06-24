import pickle, os

class Project(object):

    def __init__(self, name="Untitled Project"):
        # Overview
        self.name = name
        self.filename= None
        
        # GDB Commands
        self.build_command = "make"
        self.clean_command = "make clean"
        self.rebuild_command = "make clean; make"

        # Project Infos
        self.files = []
        self.target = None

        # UI Stuff
        self.perspective = None

    def save(self):
        fp = open(self.filename,'w')
        pickle.dump(self, fp)
        fp.close()

class Session(object):

    def __init__(self):
        self.filename = None
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

    
