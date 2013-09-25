#
# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2010  Sergey Satskiy <sergey.satskiy@gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# $Id$
#

" Codimension SVN plugin INFO command implementation "

import pysvn

def getSVNInfo( client, path,
                repRevision = pysvn.Revision( pysvn.opt_revision_kind.unspecified ),
                pegRevision = pysvn.Revision( pysvn.opt_revision_kind.unspecified ) ):
    " Provides info for the given path "
    result = []
    try:
        entries = client.info2( path, repRevision, pegRevision, recurse = False )
        if len( entries ) != 1:
            raise Exception( "Unexpected number of entries for the path. "
                             "Expected 1, received " + str( len( entries ) ) )
        itemPath, info = entries[ 0 ]
        result.append( ("Path", itemPath) )
        result.append( ("URL", info[ 'URL' ]) )
        
        return result

    except pysvn.ClientError, exc:
        errorCode = exc.args[ 1 ][ 0 ][ 1 ]
        if errorCode in [ pysvn.svn_err.wc_not_working_copy,
                          pysvn.svn_err.wc_path_not_found ]:
            return ( ("Status", "Not under SVN control"), )
        message = exc.args[ 0 ]
        return  ( ("Error", message), )
    except Exception, exc:
        return ( ("Error ", str( exc )), )
    except:
        return ( ("Error", "Unknown error"), )
