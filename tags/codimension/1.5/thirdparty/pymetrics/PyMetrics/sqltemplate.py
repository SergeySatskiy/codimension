""" sqltemplate - template for generating sql token output. """

__revision__ = "$Revision: 1.2 $"[11:-2]
__author__ = 'Reg. Charney <pymetrics@charneyday.com>'

tokenHdr = """--
-- Automatically generated table structure for token table `%s`
--

DROP TABLE IF EXISTS %s;

CREATE TABLE %s (
  IDDateTime datetime NOT NULL default '0000-00-00 00:00:00',
  ID int(11) unsigned NOT NULL auto_increment,
  libraryName varchar(32) default '',
  fileName varchar(255) default NULL,
  lineNum int(11) NOT NULL,
  colNum int(11) NOT NULL,
  type varchar(16) NOT NULL default 'ERRORTOKEN',
  semtype varchar(16) default NULL,
  textLen int(11) NOT NULL default 1,
  text varchar(255) NOT NULL default '',
  fqnFunction varchar(255) default NULL,
  fqnClass varchar(255) default NULL,
  blockNum int(11) NOT NULL default 1,
  blockDepth int(11) NOT NULL default 0,
  fcnDepth int(11) NOT NULL default 0,
  classDepth int(11) NOT NULL default 0,
  parenDepth int(11) NOT NULL default 0,
  bracketDepth int(11) NOT NULL default 0,
  braceDepth int(11) NOT NULL default 0,
  PRIMARY KEY (IDDateTime,ID),
  FULLTEXT KEY FULLTEXTIDX (text)
) TYPE=MyISAM;

--
-- Load data for table `%s`
--
"""
tokenInsert = """INSERT INTO %s VALUES (%s);\n"""

dataHdr = """
-- Automatically generated table structure for metric data table `%s`
--

DROP TABLE IF EXISTS %s;

CREATE TABLE %s (
  IDDateTime datetime NOT NULL default '0000-00-00 00:00:00',
  ID int(10) unsigned NOT NULL auto_increment,
  libraryName varchar(32) default '',
  metricName varchar(32) NOT NULL default '',
  srcFileName varchar(255) NOT NULL default '',
  varName varchar(255) NOT NULL default '',
  value decimal(15,5) NOT NULL default '0',
  PRIMARY KEY  (IDDateTime,ID)
) TYPE=MyISAM;


--
-- Load metric data for table `%s`
--
"""

dataInsert = """INSERT INTO %s VALUES (%s);\n"""

