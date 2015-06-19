/*
 * codimension - graphics python two-way code editor and analyzer
 * Copyright (C) 2014  Sergey Satskiy <sergey.satskiy@gmail.com>
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 *
 * $Id$
 *
 * Python extension module - utility functions
 */

#ifndef CFLOWUTILS_HPP
#define CFLOWUTILS_HPP

#include <string>
#include <vector>


const char *  trimStart( const char *  str );
const char *  trimEnd( const char *  end );
std::string   trim( const char *  buffer, int  len );
void          trimInplace( std::string &  str );
void          trimEndInplace( std::string &  str );
std::string   expandTabs( const std::string &  s, int  tabstop = 4 );
std::vector< std::string >
              splitLines( const std::string &  str );


#endif

