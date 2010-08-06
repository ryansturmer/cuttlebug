import os

class Node(object): pass

class FileTree(object):

    def __init__(self, path):
        self.path = self.scrub(path)
        self.path_registry = {}
        self.root = self.create_node(self.path)
        self.expand_directory(self.root)

    def list_dir(self, dir):
        retval = os.listdir(dir)
        return [self.scrub(os.path.join(dir, entry)) for entry in retval]

    def pretty(self, node=None, indent=0):
        node = node or self.root
        if node.is_dir:
            retval = ""
            base, fn = os.path.split(node.path)
            retval += " "*indent + fn + "\n"
            for child in node.children:
                retval += self.pretty(child, indent+3)
            return retval
        else:
            base, fn = os.path.split(node.path)
            return (" "*indent) + fn + "\n"
    
    def walk(self, top=None, topdown=True, onerror=None, followlinks=False):
        node = top or self.root
        node = self.get_node(node)
        directories = [child for child in  node.children if child.is_dir]
        files = [child for child in node.children if child.is_file]
        yield (node.path, [os.path.split(d.path)[1] for d in directories], [os.path.split(f.path)[1] for f in files])
        for node in directories:
            if node.children:
                for item in self.walk(node, topdown=topdown, onerror=onerror, followlinks=followlinks):
                    yield item

    def get_tree_changes(self, node=None):
        additions,deletions = self.__get_tree_changes(node)
        return ([a.path for a in additions], [d.path for d in deletions])
    
    def __get_tree_changes(self, node=None):
        node = node or self.root
        deletions = []
        for entry in node.children:
            if not os.path.exists(entry.path):
                deletions.append(entry)
        for deletion in deletions:
            node.children.remove(deletion)

        additions = []
        if node.children:
            for path in self.list_dir(node.path):
                if path not in [child.path for child in node.children]:
                    child_node = self.create_node(path)
                    node.children.append(child_node)
                    additions.append(child_node)

        # Do the recursive thing
        for child in node.children:
            if child.is_dir:
                a, d = self.__get_tree_changes(child)
                additions.extend(a)
                deletions.extend(d)

        return (additions, deletions)

    def create_node(self, path):
        node = Node()
        node.path = path
        node.is_dir = os.path.isdir(path)
        node.is_file = not node.is_dir
        node.children = []
        self.path_registry[path] = node
        return node

    def expand_all(self, node=None):
        node = node or self.root
        if node.is_dir:
            self.expand_directory(node)
            for child in node.children:
                self.expand_all(child)
    def expand_directory(self, node):
        node = self.get_node(node)
        if node.children or not node.is_dir: return
        for entry in self.list_dir(node.path):
            child_node = self.create_node(entry)
            node.children.append(child_node)

    def collapse_directory(self, node):
        node = self.get_node(node)
        node.children = []
        # TODO DELETE FROM PATH REGISTRY HERE.

    def scrub(self, path):
        return os.path.normpath(os.path.abspath(path))

    def parent(self, path):
        return os.path.split(path)[0]

    def get_node(self, path):
        if isinstance(path, Node): return path
        path = self.scrub(path) 
        return self.path_registry[path] 






















