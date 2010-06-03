from memory_view import MemoryView
from log_view import LogView
from var_view import LocalsView
#from build_view import BuildView
from editor_view import EditorView, QuickFindBar
from project_view import ProjectView, ProjectViewEvent, EVT_PROJECT_DCLICK_FILE
from breakpoint_view import BreakpointView
from runtime_view import RuntimeView, GDBDebugView
from asm_view import DisassemblyView

from view import ViewEvent, EVT_VIEW_REQUEST_UPDATE, EVT_VIEW_POST_UPDATE 
