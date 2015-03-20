import sys
import os
import shutil

def main( argv ):
    f = open( 'CXX/Version.hxx' )
    major = None
    minor = None
    patch = None
    for line in f:
        words = line.split()
        if words[0:2] == ['#define', 'PYCXX_VERSION_MAJOR']:
            major = words[2]
        if words[0:2] == ['#define', 'PYCXX_VERSION_MINOR']:
            minor = words[2]
        if words[0:2] == ['#define', 'PYCXX_VERSION_PATCH']:
            patch = words[2]

    print( 'version: %s, %s, %s' % (major, minor, patch) )

    tmp_dir = os.environ.get('TMP','/tmp')
    kit_name = 'pycxx-%s.%s.%s' % (major, minor, patch)
    kit_dir = os.path.join( tmp_dir, kit_name )

    if os.path.exists( kit_dir ):
        print( 'Info: Removing tree at %s' % kit_dir )
        shutil.rmtree( kit_dir )

    os.mkdir( kit_dir )

    print( 'Info: svn export %s' % kit_dir )
    os.system( 'svn export --force . %s' % kit_dir )

    print( 'Info: Creating %s.tar.gz' % kit_dir )
    os.chdir( tmp_dir )
    os.system( 'tar czf %s.tar.gz %s' % (kit_dir, kit_name) )

    return 0
    
if __name__ == '__main__':
    sys.exit( main( sys.argv ) )
