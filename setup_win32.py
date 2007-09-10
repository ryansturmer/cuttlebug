import os
import pickle
import datetime
import py2exe
import sys
from distutils.core import setup

# Don't require the command line argument.
sys.argv.append('py2exe')

# Include these data files.
def get_data_files():
    def filter_files(files):
        def match(file):
            #extensions = ('.dat',)
            #for extension in extensions:
            #    if file.endswith(extension):
            #        return True
            return False
        return tuple(file for file in files if not match(file))
    def tree(src):
        return [(root, map(lambda f: os.path.join(root, f), filter_files(files))) for (root, dirs, files) in os.walk(os.path.normpath(src)) if '.svn' not in root and '.svn' in dirs]
    def include(src):
        result = tree(src)
        result = [('.', item[1]) for item in result]
        return result
    data_files = ['default-styles.dat']
    data_files += tree('./tests')
    data_files += tree('./icons')
    return data_files
    
# Build the distribution.
setup(
    options = {"py2exe":{
        "compressed": 1,
        "optimize": 2,
        "bundle_files": 3,
        "includes": ['encodings', 'encodings.cp437'],
        "packages": [],
    }},
    windows = [{
        "script": "main.py",
        "dest_base": "cuttlebug",
       # "icon_resources": [(1, "icons/analyzer.ico")],
    }],
    data_files = get_data_files(),
)

# Build Information
def get_revision():
    try:
        import pysvn
        client = pysvn.Client()
        entry = client.info('.')
        return entry.revision.number
    except Exception:
        return -1
        
def get_timestamp():
    now = str(datetime.datetime.now())
    return now[:now.rfind('.')]
    
def save_build_info():
    revision = get_revision()
    timestamp = get_timestamp()
    info = {
        'revision': revision,
        'timestamp': timestamp,
    }
    path = './dist/version.dat'
    output = open(path, 'w')
    pickle.dump(info, output)
    output.close()
    print
    print 'Saved build info %s to %s' % (info, path)
    
#save_build_info()
