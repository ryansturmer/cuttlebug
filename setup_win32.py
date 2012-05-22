import os
import pickle
import datetime
import sys
import py2exe

#import pkg_resources
from distutils.core import setup

# Don't require the command line argument.
sys.argv.append('py2exe')

MANIFEST = '''
<assembly xmlns="urn:schemas-microsoft-com:asm.v1"
manifestVersion="1.0">
  <assemblyIdentity
    version="2.0.0.0"
    processorArchitecture="x86"
    name="Assay Development Environment"
    type="win32"
  />
  <description>Assay Development Environment 1.0</description>
  <trustInfo xmlns="urn:schemas-microsoft-com:asm.v3">
    <security>
      <requestedPrivileges>
        <requestedExecutionLevel
          level="asInvoker"
          uiAccess="false"
        />
      </requestedPrivileges>
    </security>
  </trustInfo>
  <dependency>
    <dependentAssembly>
      <assemblyIdentity
        type="win32"
        name="Microsoft.VC90.CRT"
        version="9.0.21022.1"
        processorArchitecture="x86"
        publicKeyToken="1fc8b3b9a1e18e3b"
      />
    </dependentAssembly>
  </dependency>
  <dependency>
    <dependentAssembly>
      <assemblyIdentity
        type="win32"
        name="Microsoft.Windows.Common-Controls"
        version="6.0.0.0"
        processorArchitecture="x86"
        publicKeyToken="6595b64144ccf1df"
        language="*"
      />
    </dependentAssembly>
  </dependency>
</assembly>
'''

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
    data_files += tree('./extras')
    data_files += tree('./templates')
    data_files += tree('./targets')
    data_files += tree('./Microsoft.VC90.CRT')
    return data_files
    
# Build the distribution.
setup(
    options = {"py2exe":{
        "compressed": 1,
        "optimize": 1,
        "bundle_files": 1,
        "includes": ['encodings', 'encodings.cp437'],
        #"excludes": ['dummy'],
        "packages": ['lxml', 'gzip'],
        "excludes": ['Tkconstants', 'Tkinter', 'tcl'],
        "dll_excludes": [
            'msvcp90.dll',
            'mswsock.dll',
            'API-MS-Win-Core-LocalRegistry-L1-1-0.dll',
            'API-MS-Win-Core-ProcessThreads-L1-1-0.dll',
            'API-MS-Win-Security-Base-L1-1-0.dll',
            'POWRPROF.dll',
            'Secur32.dll',
            'SHFOLDER.dll',
            ],
    }},
    windows = [{
        "script": "main.py",
        "dest_base": "cuttlebug",
       # "icon_resources": [(1, "icons/analyzer.ico")],
        "other_resources": [(24, 1, MANIFEST)],
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
