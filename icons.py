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
        '.script': 'file_gear.png' }

def get_file_icon(filename):
    ext = ""
    try:
        fn, ext = os.path.splitext(filename)
    except:
        pass
    finally:
        return  bindings.get(ext.lower(), 'file_white.png')


