on open location this_URL
	try
		set py to "/usr/bin/python3"
		set scriptPath to (POSIX path of (path to home folder)) & "Library/Application Support/PrintQueueBridge/handler.py"
		do shell script quoted form of py & " " & quoted form of scriptPath & " " & quoted form of this_URL
	on error errMsg
		display notification errMsg with title "Print Queue Bridge"
	end try
end open location
