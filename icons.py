import os
bindings = {
        '.c': 'file_c.png',        
        '.s': 'file_s.png',
        '.ld': 'file_link.png',
        '.cmd': 'file_link.png',
        '.bz2': 'file_archive.png',
        '.gz': 'file_archive.png',
        '.zip': 'file_archive.png',
        '.tar': 'file_archive.png',
        '.ini': 'file_wrench.png',
        '.cfg': 'file_wrench.png',
        '.py': 'file_py.png',
        '.h': 'file_h.png',
        '.png': 'file_picture.png',
        '.jpg': 'file_picture.png',
        '.gif': 'file_picture.png',
        '.tif': 'file_picture.png',
        '.tiff': 'file_picture.png',
        '.sh': 'file_gear.png',
        '.script': 'file_gear.png', 
        '.xml' : 'file_markup.png',
        '.html' : 'file_world.png',
        '.htm' : 'file_world.png',
        '.xhtml' : 'file_world.png',
        '.sgml' : 'file_markup.png',
        '.pdf': 'file_acrobat.png',
        '.java' : 'file_java.png',
        '.doc': 'file_word.png' ,
        '.rtf': 'file_word.png' }

def get_file_icon(filename):
    ext = ""
    try:
        file = os.path.split(filename)[1]
        if file.strip().lower() == "makefile":
            return "file_gear.png"
        fn, ext = os.path.splitext(file)
        return bindings.get(ext.lower(), 'file_white.png')
    except:
        return 'file_white.png'


