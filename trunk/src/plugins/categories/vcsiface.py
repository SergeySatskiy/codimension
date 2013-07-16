#
#

from yapsy.IPlugin import IPlugin


class VersionControlSystemInterface( IPlugin ):
    """ Version control system plugin interface """

    def __init__( self ):
        """ The plugin class is instantiated with no arguments """
        return

    def getInterfaceVersion( self ):
        """ Do not override this method. Codimension uses it
            to detect the protocol version conformance. """
        return "1.0.0"


    # Member functions below could or should be implemented by the pugin.
    # See docstrings for the detailed description.

    @staticmethod
    def getVCSName():
        """ Should provide the specific version control name, e.g. SVN """
        raise Exception( "getVCSName() must be overridden" )

    def activate( self ):
        """ The plugin may override the method to do specific
            plugin activation handling.
            Note: if overriden do not forget to call the
                  base class activate() """
        super( VersionControlSystemInterface, self ).activate()
        return

    def deactivate( self ):
        """ The plugin may override the method to do specific
            plugin deactivation handling.
            Note: if overriden do not forget to call the
                  base class deactivate() """
        super( VersionControlSystemInterface, self ).deactivate()
        return

    def setEnvironment( self, ideSettings, ideGlobalData ):
        """ Codimension calls this method after the activate() call and
            before any other non-static methods.

            ideSettings - reference to the IDE Settings singleton
                          see codimension/src/utils/settings.py
            ideGlobalData - reference to the IDE global settings
                            see codimension/src/utils/globals.py

            No return value is expected
        """
        return

    def populateMainMenu( self, ... ):
        raise Exception( "populateMainMenu() must be overridden" )

    def populateFileContextMenu( self, ... ):
        raise Exception( "populateFileContextMenu() must be overridden" )

    def populateDirectoryContextMenu( self, ... ):
        raise Exception( "populateDirectoryContextMenu() must be overridden" )

    def populateBufferContextMenu( self, ... ):
        raise Exception( "populateBufferContextMenu() must be overridden" )


    def isUnderVCS( self, path ):
        """ 'path' is an absolute path to a directory or to a file.
            Return value must be True if the given path is under the
            revision control system type, or False otherwise. """
        raise Exception( "isUnderVCS() must be overridden" )

    def isChangedLocally( self, path, recursively = False ):
        raise Exception( "isChangedLocally() must be overridden" )

    def isChangedRemotely( self, path, recursively = False ):
        raise Exception( "isChangedRemotely() must be overridden" )

    def getInfo( self, path, recursively = False ):
        raise Exception( "getInfo() must be overridden" )

    def getRepositoryVersion( self, path, revision = None ):
        raise Exception( "getRepositoryVersion() must be overridden" )

