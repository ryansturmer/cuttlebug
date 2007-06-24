/*
 * GDB Machine Interface Grammar for Python
 * Ryan Sturmer
 * 2009/04/20
 */
grammar GDBMI;

options {
	language=Python;
	output=AST;
	k=2;
	ASTLabelType=CommonTree;
}

@header {
DONE = 1
RUNNING = 2
ERROR = 3
CONNECTED = 4
EXIT = 5 
STOPPED = 6

class GDBMITuple(dict):
	def __getattr__(self, key):
		return self[key]
		
class GDBMIResultRecord(GDBMITuple):
	def __init__(self):
		super(GDBMIResultRecord, self).__init__(self)
		self.token = None
		self.cls = None
	def __str__(self):
		return "<GDBMIRresultRecord token=\%s class=\%s \%s>" \% (self.token, self.cls, super(GDBMIResultRecord, self).__str__())
		
class GDBMIResponse(object):
	def __init__(self):
		self.console = []
		self.target = []
		self.log = []
		self.exc = None
		self.status = None
		self.notify = None
		self.result = None
	def __str__(self):
		return "<GDBMIResponse console=\%s target=\%s log=\%s result=\%s>" \% (self.console, self.target, self.log, self.result)		

}


result_record returns [val]
	@init {
		$val = GDBMIResultRecord()
	}
	: (TOKEN {$val.token = int($TOKEN.text)})? RESULT 
	   RESULT_CLASS {$val.cls = str($RESULT_CLASS.text)} 
	  (COMMA result {$val[$result.key] = $result.val})* NL;
	
output returns [response]
	@init {
	$response = GDBMIResponse()	
	}
	// Newline added for debugging
	: (out_of_band_record NL{
		if $out_of_band_record.console:
			$response.console.append($out_of_band_record.console)
		if $out_of_band_record.target:
			$response.target.append($out_of_band_record.target)
		if $out_of_band_record.log:
			$response.log.append($out_of_band_record.log)
		if $out_of_band_record.exc:
			$response.exc = $out_of_band_record.exc
		if $out_of_band_record.status:
			$response.status = $out_of_band_record.status
		if $out_of_band_record.notify:
			$response.notify = $out_of_band_record.notify
			
	})*  result_record? {
	$response.result=$result_record.val
	} EOM WS*;

async_record returns [exc,status,notify]
	@init {
	$exc = None
	$status = None
	$notify = None
	}
	:exec_async_output {$exc = $exec_async_output.val} | 
	status_async_output {$status = $status_async_output.val} | 
	notify_async_output {$notify = $notify_async_output.val};

out_of_band_record returns [exc,status,notify,target,console,log]
	@init {
	$exc = $status = $notify = None
	$target = $console = $log = None
	}
	: async_record {
	if $async_record.exc: $exc = $async_record.exc
	if $async_record.status: $status = $async_record.status
	if $async_record.notify: $notify = $async_record.notify
	} | 
	stream_record {
	if $stream_record.target: $target = $stream_record.target
	if $stream_record.console: $console = $stream_record.console
	if $stream_record.log: $log = $stream_record.log
	};

exec_async_output returns [val]
	: (TOKEN)? EXEC async_output {$val = $async_output.val};
	
status_async_output returns [val]
	: (TOKEN)? STATUS async_output {$val = $async_output.val};
	
notify_async_output returns [val]
	: (TOKEN)? NOTIFY async_output {$val = $async_output.val};
	
async_output returns [val]
	@init {
		$val = GDBMIResultRecord()
	}
	: ASYNC_CLASS (COMMA result {$val[$result.key] = $val.val})* NL;
	

var	returns [txt] 
	: STRING {$txt = str($STRING.text)};

result returns [key,val]
	: (var '=' value) {
	$key=str($var.txt)
	$val=$value.val
	};
	
value	returns [val] : const {$val=str($const.txt)} | tuple {$val=$tuple.items} | list {$val=$list.items};
	
const	returns [txt]
	: C_STRING {$txt=$C_STRING.text[1:-1]};
	
tuple	returns [items]
	@init { $items = GDBMITuple() }
	: '{}' 
	| '{' a=result {$items[a.key] = a.val} (COMMA b=result {$items[b.key] = b.val})* '}';
	

stream_record returns [console, target, log]
	@init {
	$console = None
	$target = None
	$log = None
	}
	: console_stream_output {$console = $console_stream_output.txt}
	| target_stream_output {$target = $target_stream_output.txt}
	| log_stream_output {$log = $log_stream_output.txt};
	
list	returns [items]
	@init { $items=[] }
	: '[]' 
	| '[' a=value {$items.append(a.val)} (COMMA b=value {$items.append(b.val)})* ']'
	| '[' c=result {$items.append(dict( ((c.key,c.val),) ))} (COMMA d=result {$items.append(dict( ((d.key,d.val),) ))})* ']';

console_stream_output returns [txt]
	: CONSOLE C_STRING {$txt = str($C_STRING.text[1:-1]).decode('string_escape')};

target_stream_output returns [txt]
	: TARGET C_STRING {$txt = str($C_STRING.text[1:-1]).decode('string_escape')};

log_stream_output returns [txt]
	: LOG C_STRING {$txt = str($C_STRING.text[1:-1]).decode('string_escape')};


// LEXER

// Can't use the omission (!) operator here for some reason... weird.
C_STRING		
	: '"' ('\\''"' | ~('"' |'\n'|'\r'))* '"';

ASYNC_CLASS
	: 'stopped';

RESULT_CLASS
	: 'done'
	| 'running'
	| 'connected'
	| 'error'
	| 'exit';

STRING
	: ('_' | 'A'..'Z' | 'a'..'z')('-' | '_' | 'A'..'Z' | 'a'..'z'|'0'..'9')*;

NL			
	: ('\r')?'\n';

WS
	: (' ' | '\t');
TOKEN 			
	: ('0'..'9')+;

COMMA	: ',';

EOM	: '(gdb)';	
	
CONSOLE : '~';
TARGET 	: '@';
LOG 	: '&';

EXEC 	: '*';
STATUS  : '+';
NOTIFY  : '=';

RESULT	: '^';
