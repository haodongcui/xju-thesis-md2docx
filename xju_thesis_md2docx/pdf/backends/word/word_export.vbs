Option Explicit

Dim objWord, doc
Dim inputPath, outputPath, updateFields
Dim rawUpdateFields, toc

If WScript.Arguments.Count < 2 Then
    WScript.Echo "USAGE: cscript //nologo word_export.vbs input.docx output.pdf [updateFields]"
    WScript.Quit 64
End If

inputPath = WScript.Arguments.Item(0)
outputPath = WScript.Arguments.Item(1)
updateFields = True

If WScript.Arguments.Count >= 3 Then
    rawUpdateFields = LCase(Trim(WScript.Arguments.Item(2)))
    If rawUpdateFields = "0" Or rawUpdateFields = "false" Or rawUpdateFields = "no" Then
        updateFields = False
    End If
End If

Set objWord = CreateObject("Word.Application")
objWord.Visible = False
objWord.DisplayAlerts = 0

On Error Resume Next
Set doc = objWord.Documents.Open(inputPath, False, True, False, "", "", False, "", "", 0, 0, False, True, 0, True, "")

If (doc Is Nothing) Or (Err.Number <> 0) Then
    WScript.Echo "OPEN_ERROR:" & Err.Number & ":" & Err.Description
    objWord.Quit
    WScript.Quit 2
End If

Err.Clear
If updateFields Then
    doc.Fields.Update
    For Each toc In doc.TablesOfContents
        toc.Update
    Next
    doc.Repaginate
    Err.Clear
End If

doc.ExportAsFixedFormat outputPath, 17
If Err.Number <> 0 Then
    WScript.Echo "EXPORT_ERROR:" & Err.Number & ":" & Err.Description
    doc.Close False
    objWord.Quit
    WScript.Quit 3
End If

doc.Close False
objWord.Quit
