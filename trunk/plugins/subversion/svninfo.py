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
from svnstrconvert import nodeKindToString, scheduleToString, timestampToString


def getSVNInfo( client, path, repRevision = None, pegRevision = None ):
    " Provides info for the given path "
    if repRevision is None:
        repRevision = pysvn.Revision( pysvn.opt_revision_kind.unspecified )
    if pegRevision is None:
        pegRevision = pysvn.Revision( pysvn.opt_revision_kind.unspecified )

    result = []
    try:
        entries = client.info2( path, repRevision, pegRevision,
                                recurse = False )
        if len( entries ) != 1:
            raise Exception( "Unexpected number of entries for the path. "
                             "Expected 1, received " + str( len( entries ) ) )
        itemPath, info = entries[ 0 ]
        result.append( ("Path", itemPath) )
        if 'URL' in info and info[ 'URL' ]:
            result.append( ("URL", info[ 'URL' ]) )
        if 'rev' in info and info[ 'rev' ]:
            result.append( ("Revision", str( info[ 'rev' ].number )) )
        if 'repos_root_URL' in info and info[ 'repos_root_URL' ]:
            result.append( ("Repository root URL", info[ 'repos_root_URL' ]) )
        if 'repos_UUID' in info and info[ 'repos_UUID' ]:
            result.append( ("Repository UUID", info[ 'repos_UUID' ]) )
        if 'last_changed_author' in info and info[ 'last_changed_author' ]:
            result.append( ("Author of the last changes",
                            info[ 'last_changed_author' ]) )
        if 'last_changed_date' in info and info[ 'last_changed_date' ]:
            result.append( ("Date of the last changes",
                            timestampToString( info[ 'last_changed_date' ] )) )
        if 'last_changed_rev' in info and info[ 'last_changed_rev' ] and \
           info[ 'last_changed_rev' ].kind == pysvn.opt_revision_kind.number:
            result.append( ("Revision of the last changes",
                            str( info[ 'last_changed_rev' ].number )) )
        if 'kind' in info and info[ 'kind' ]:
            result.append( ("Node kind", nodeKindToString( info[ 'kind' ] )) )
        if 'lock' in info and info[ 'lock' ]:
            lockInfo = info[ 'lock' ]
            if 'owner' in lockInfo:
                if lockInfo[ 'owner' ]:
                    result.append( ("Lock owner", lockInfo[ 'owner' ]) )
                else:
                    result.append( ("Lock owner", "unknown") )
            if 'creation_date' in lockInfo:
                if lockInfo[ 'creation_date' ]:
                    result.append( ("Lock creation date",
                                    timestampToString( lockInfo[ 'creation_date' ] )) )
                else:
                    result.append( ("Lock creation date", "unknown") )
            if 'expiration_date' in lockInfo:
                if lockInfo[ 'expiration_date' ]:
                    result.append( ("Lock expiration date",
                                    timestampToString( lockInfo[ 'expiration_date' ] )) )
                else:
                    result.append( ("Lock expiration date", "unknown") )
            if 'token' in lockInfo:
                if lockInfo[ 'token' ]:
                    result.append( ("Lock token", lockInfo[ 'token' ]) )
                else:
                    result.append( ("Lock token", "none") )
            if 'comment' in lockInfo:
                if lockInfo[ 'comment' ]:
                    result.append( ("Lock comment", lockInfo[ 'comment' ]) )
                else:
                    result.append( ("Lock comment", "none") )
        if 'wc_info' in info and info[ 'wc_info' ]:
            wcInfo = info[ 'wc_info' ]
            if 'schedule' in wcInfo and wcInfo[ 'schedule' ]:
                result.append( ("Schedule",
                                scheduleToString( wcInfo[ 'schedule' ] )) )
            if 'copyfrom_url' in wcInfo and wcInfo[ 'copyfrom_url' ]:
                result.append( ("Copied from URL", wcInfo[ 'copyfrom_url' ]) )
            if 'copyfrom_rev' in wcInfo and wcInfo[ 'copyfrom_rev' ]:
                if wcInfo[ 'copyfrom_rev' ].kind == pysvn.opt_revision_kind.number:
                    if wcInfo[ 'copyfrom_rev' ].number != -1:
                        result.append( ("Copied from revision",
                                        str( wcInfo[ 'copyfrom_rev' ].number )) )
            if 'text_time' in wcInfo and wcInfo[ 'text_time' ]:
                result.append( ("Last time content updated",
                                timestampToString( wcInfo[ 'text_time' ] )) )
            if 'prop_time' in wcInfo and wcInfo[ 'prop_time' ]:
                result.append( ("Last time properties updated",
                                timestampToString( wcInfo[ 'prop_time' ] )) )
            if 'checksum' in wcInfo and wcInfo[ 'checksum' ]:
                result.append( ("Checksum", wcInfo[ 'checksum' ]) )
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
