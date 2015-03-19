



# Codimension Key Binding #

Codimension version: 2.0.1

## Tools ##

| **Key**       | **Description** |
|:--------------|:----------------|
| Ctrl+L      |Running pylint for the current buffer. |
| Ctrl+K      | Running pymetrics for the current buffer. |
| Alt+Shift+S | Search a name in the project. |
| Alt+Shift+O | Search a file in the project. |
| Ctrl+I      | Open import or select import to open for the current buffer. |



## IDE ##

| **Key**       | **Description** |
|:--------------|:----------------|
| ESC         | The action depends on a context. It may close a dialogue window (as 'cancel' button was clicked) or it may hide a tooltip or remove highlights in the text editor or hide incremental search panel etc. |
| Ctrl+Shift+N | Create a new project. |
| Ctrl+Shift+O | Open a project using the OS file selection dialogue. |
| Ctrl+N       | Create a new tab with a text editor for a new file. If the 'template.py' is found for the current project then its content is loaded after performing macro substitutions.<br>The supported macros are: $creationdate, $author, $license, $copyright, $version, $email, $description. The values are taken from the project properties. <br>
<tr><td> Ctrl+O       </td><td> Open a file using the OS file selection dialogue. </td></tr>
<tr><td> Ctrl+S       </td><td> Save the current buffer. </td></tr>
<tr><td> Ctrl+Shift+S </td><td> Save the current buffer using the OS file save as dialogue. </td></tr>
<tr><td> F11          </td><td> Shrink side bars. </td></tr>
<tr><td> Ctrl+F4      </td><td> Close the current tab. </td></tr>
<tr><td> Ctrl+Shift+F </td><td> Search in files. The search results are shown in the bottom tabbed window. </td></tr>
<tr><td> F1           </td><td> Open a tab with a short hot keys reference. </td></tr>
<tr><td> Ctrl+TAB     </td><td> Switching between two recent tabs. </td></tr>
<tr><td> Ctrl+PgUp    </td><td> Switch to the previous visible tab. </td></tr>
<tr><td> Ctrl+PgDown  </td><td> Switch to the next visible tab. </td></tr>
<tr><td> Alt+PgUp     </td><td> Forward in editing history. </td></tr>
<tr><td> Alt+PgDown   </td><td> Back in editing history. </td></tr>
<tr><td> Alt+F4       </td><td> Close codimension. </td></tr></tbody></table>

<h2>Buffer ##

| **Key**        | **Description** |
|:---------------|:----------------|
| Arrow keys   | Move the cursor one character left or right / one line up or down. |
| PgUp         | Move the cursor one page up. |
| PgDown       | Move the cursor one page down. |
| Home         | Move the cursor to the beginning of a visible line. |
| End          | Move the cursor to the end of a visible line. |
| Insert       | Switching between insert and replace modes. |
| Delete       | Delete the symbol under the cursor. |
| Ctrl+Left    | Move the cursor one word left. |
| Ctrl+Right   | Move the cursor one word right. |
| Ctrl+Up      | Scroll one line up without moving the cursor. |
| Ctrl+Down    | Scroll one line down without moving the cursor. |
| Ctrl+Home    | Move the cursor to the beginning of the buffer. |
| Ctrl+End     | Move the cursor to the end of the buffer. |
| Ctrl+Insert  | Copy selected if there is a selection. Copy the current line otherwise. |
| Ctrl+Del     | Delete till the end of the word. |
| Alt+Left     | Move the cursor one word part left. |
| Alt+Right    | Move the cursor one word part right. |
| Alt+Up       | Move the cursor one paragraph up. |
| Alt+Down     | Move the cursor one paragraph down. |
| Alt+Home     | Synonym for Home |
| Alt+End      | Synonym for End |
| Shift+Left   | Select one character left. |
| Shift+Right  | Select one character right. |
| Shift+Up     | Select one line up. |
| Shift+Down   | Select one line down. |
| Shift+PgUp   | Select one page up. |
| Shift+PgDown | Select one page down. |
| Shift+Home   | Select till the beginning of the visible line. |
| Shift+End    | Select till the end of the visible line. |
| Shift+Insert | Paste. |
| Shift+Del   | Delete the selected text (if so) or the line and have a copy in the exchange buffer. |
| Ctrl+C       | Copy selected if there is a selection. Copy the current line otherwise. |
| Ctrl+V       | Paste. |
| Ctrl+X       | Synonym for Shift+Del. |
| Ctrl+A       | Select all. |
| Ctrl+Shift+Left  | Select till the beginning of the current word. |
| Ctrl+Shift+Right | Select till the end of the current word. |
| Ctrl+Shift+Home  | Select till the beginning of the current visible line. |
| Ctrl+Shift+End   | Select till the end of the current visible line. |
| Ctrl+Shift+Up     | Select till the beginning of the current paragraph. |
| Ctrl+Shift+Down   | Select till the end of the the current paragraph. |
| Ctrl+Z           | Undo. |
| Ctrl+Shift+Z     | Redo. |
| Ctrl+=           | Zoom in. |
| Ctrl+-           | Zoom out. |
| Ctrl+0           | Reset zoom. |
| Ctrl+G           | Open the 'go to line' panel. |
| Ctrl+F           | Open incremental search panel. |
| Ctrl+R           | Open incremental replace panel. |
| Ctrl+'           | Highlight matches of the current word and save the current word as the criteria for quick cursor moving. Subsequent Ctrl+' will move the cursor to the next match if the word where the cursor is stays the same. |
| Ctrl+,           | Move the cursor to the previous match of a word memorized on the Ctrl+' click. If no such word is memorized the cursor stays where it was. |
| Ctrl+.           | Move the cursor to the next match of a word memorized on the Ctrl+' click. If no such word is memorized the cursor stays where it was. |
| Ctrl+M           | Comment or uncomment a line or selected lines. If the first character in the first selected line is '#' then the selected lines will be uncommented. If not then they will be commented. |
| F3               | Move the cursor to the next match of the last search or replace. |
| Shift+F3         | Move the cursor to the previous match of the last search or replace. |
| Ctrl+Space       | Complete the current word from the cursor position. If there are more than one options a list will be brought up. |
| TAB              | If the text cursor is at the very beginning of the line or the previous character is a space then spaces are inserted. If a previous character is not a space then code completion is triggered as desribed for Ctrl+Space. |
| Ctrl+F1          | The buffer tag under the text cursor is analysed. If it is a function call or a class then its docstring and a calltip are searched. If the information is found it is displayed at a browser at the bottom. |
| Ctrl+backslash   | The buffer tag under the text cursor is analysed and the cursor jumps to its definition regardless whether the definition is in the same buffer or in another file. |
| Ctrl+F3          | Initiate incremental search of the current word or selection without bringing up the incremental search panel. |
| Ctrl+]           | Find occurrences of the current word. |
| Alt+U            | Jump to the beginning of the current function or class. |
| Ctrl+/           | Show or hide a calltip. |
| Ctrl+\           | Find the current word definition. If found then the cursor jumps to the definition. |
| Ctrl+Shift+T     | Move the cursor to the first visible line. |
| Ctrl+Shift+M     | Move the cursor to the line in a middle of the visible lines. |
| Ctrl+Shift+B     | Move the cursor to the last visible line. |
| Alt+Shift+Left   | Rectangular selection - adding one character wide column to the left of the cursor to the current selection. |
| Alt+Shift+Right  | Rectangular selection - adding one character wide column to the right of the cursor to the current selection. |
| Alt+Shift+Up   | Rectangular selection - adding one line above the cursor to the current selection. |
| Alt+Shift+Down  | Rectangular selection - adding one line below the cursor to the current selection. |
| Ctrl+mouse selection | Rectangular selection. |


## Debugger ##

| **Key**         | **Description** |
|:----------------|:----------------|
| Shift+F5      | Start debugging the project main script with saved settings. |
| F5            | Start debugging the current tab script with saved settings. |
| Ctrl+Shift+F5 | Edit debugger settings and start debugging the project main script. The settings are saved to be used when the script is debugged again. |
| Ctrl+F5       | Edit debugger settings and start debugging the current tab script. The settings are saved to be used when the script is debugged again. |
| Ctrl+F10      | Stop the debugging session and kill the i/o console. |
| F10           | Stop the debugging session and keep the i/o console. |
| F4            | Restart the debugging session. |
| F6            | Continue. |
| F7            | Step in. |
| F8            | Step over. |
| F9            | Step out. |
| Shift+F6      | Run to cursor. |
| Ctrl+W        | Show the current debugger line. |




## Other ##

| **Key**       | **Description** |
|:--------------|:----------------|
| Create a new project | Select Project->New project main menu item and fill the fields in the appeared dialogue. |
| Unload the project | Click on the 'red cross' icon in the project tab. |
| View or edit project properties | Click on the blue 'i' icon in the project tab. |
| Generate imports diagram for the current project | Click on the 'folder' icon on the buttons bar. |
| Generate imports diagram for the buffer | Click on the 'folder' icon on the buffer toolbar on the right. |
| Running pylint for the current project | Click on the 'red book' icon on the buttons bar. |
| Running pylint recursively for a directory | Click right mouse button on the required directory in the project browser and select the corresponding menu item. |
|Running pymetrics for the current project | Click on the 'sigma' icon on the buttons bar. |
| Running pymetrics recursively for a directory | Click right mouse button on the required directory in the project browser and select the corresponding menu item. |
| Running simple metrics for a project | Click on the 'green book' icon on the buttons bar. |


