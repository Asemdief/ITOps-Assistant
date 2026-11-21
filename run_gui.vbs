' Launch ITOps Command without a console window
Set sh = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
folder = fso.GetParentFolderName(WScript.ScriptFullName)
' Prefer pythonw (no console). Fallback to py -3
cmd = "pythonw.exe """ & folder & "\gui.py"""
rc = sh.Run(cmd, 0, False)
If rc = 0 Then
  ' Run returns immediately with window style 0; errors are hard to detect.
End If
