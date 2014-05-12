import pysvn
import sys
import os

def make_tag( from_url, tag_base_url, version ):
    client = pysvn.Client()
    client.callback_get_log_message = lambda : (True, 'Tag version '+version)
    client.callback_get_login = callback_getLogin

    try:
        from_files = client.ls( from_url, recurse=False )
        print 'Info: Found', from_url
    except pysvn.ClientError, e:
        print 'Error: From does not exist',from_url
        return

    try:
        tag_files = client.ls( tag_base_url, recurse=False )
        print 'Info: Found', tag_base_url
    except pysvn.ClientError, e:
        print 'Error: Tag base does not exist',tag_base_url
        return

    cur_versions = [os.path.basename(f['name']) for f in tag_files]

    if version in cur_versions:
        print 'Error: Already tagged',version
        return


    try:
        to_url = tag_base_url + '/' + version
        print 'Info: Copy',repr(from_url), repr(to_url)
        client.copy( from_url, to_url )
        print 'Info: Copy complete'
    except pysvn.ClientError, e:
        print 'Error: ', str(e)
        return

def callback_getLogin( realm, username, may_save ):
    print 'May save:',may_save
    print 'Realm:',realm
    if username:
        print 'Username:',username
    else:
        sys.stdout.write( 'Username: ' )
        username = sys.stdin.readline().strip()
        if len(username) == 0:
            return 0, '', '', False

    sys.stdout.write( 'Password: ' )
    password = sys.stdin.readline().strip()

    save_password = 'x'
    while save_password.lower() not in ['y','ye','yes','n', 'no','']:
        sys.stdout.write( 'Save password? [y/n] ' )
        save_password = sys.stdin.readline().strip()
    
    return 1, username, password, save_password in ['y','ye','yes']

def main():
    if len(sys.argv) != 2:
        print 'Usage: %s version' % sys.argv[0]
        return

    version = sys.argv[1]
    from_url = 'https://svn.code.sf.net/p/cxx/code/trunk/CXX'
    tag_base_url = 'https://svn.code.sf.net/p/cxx/code/tags'

    make_tag( from_url, tag_base_url, version )

if __name__ == '__main__':
    main()
