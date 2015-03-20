all_lines = open( 'PyCXX.html' ).readlines()

all_contents = []

for line in all_lines:
    if( line.startswith( '<h1><a name=' )
    or line.startswith( '<h2><a name=' ) ):
        all_contents.append( line )

all_html_contents = []
all_html_contents.append( '<ul>' )

nested = False
indent = ''
cls = 'contents_h1'
for line in all_contents:
    tag = line[0:len('<h1>')]
    contents = line[len('<h1><a name="'):-(len('</a></h1>')+1)]
    if nested:
        if tag == '<h1>':
            all_html_contents.append( '    </ul></li>' )
            nested = False
            indent = ''
            cls = 'contents_h1'
    else:
        if tag == '<h2>':
            nested = True
            indent = '    '
            cls = 'contents_h2'
            all_html_contents.append( '    <li><ul>' )
    all_html_contents.append( '%s<li class="%s"><a href="#%s</a></li>' % (indent, cls, contents) )

if nested:
    all_html_contents.append( '    </ul></li>' )
all_html_contents.append( '</ul>' )

output = True
for line in all_lines:
    if line == '<h2>Contents</h2>\n':
        print line,
        for line in all_html_contents:
            print line

        output = False

    elif output:
        print line,

    else:
        if line.startswith( '<h' ):
            print line,
            output = True
