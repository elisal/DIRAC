#!/usr/bin/env python
########################################################################
# $HeadURL$
# File :    dirac-dms-remove-lfn-replica
# Author :  Stuart Paterson
########################################################################
"""
  Remove replica of LFN from specified Storage Element and File catalogs.
"""
__RCSID__ = "$Id$"
import DIRAC
from DIRAC.Core.Base import Script

Script.setUsageMessage( '\n'.join( [ __doc__.split( '\n' )[1],
                                     'Usage:',
                                     '  %s [option|cfgfile] ... LFN SE [FCCheck]' % Script.scriptName,
                                     'Arguments:',
                                     '  LFN:      Logical File Name or file containing LFNs',
                                     '  SE:       Valid DIRAC SE',
                                     '  FCCheck:  Check replica existence in FC, possible values: YESLFC/NOLFC [default is YESLFC]' ] ) )
Script.parseCommandLine( ignoreErrors = True )
args = Script.getPositionalArgs()

if len( args ) < 2:
  Script.showHelp()

FCCheck = 'YESLFC'
if len( args ) > 2:
  FCCheck = args[ 2 ]
  #print 'Only one LFN SE pair will be considered'
  if FCCheck != 'YESLFC' and FCCheck != 'NOLFC':
    print( "Invalid value: %s Only possible values for FCCheck are YESLFC or NOLFC" % FCCheck )
    Script.showHelp()

from DIRAC.Interfaces.API.Dirac                       import Dirac
dirac = Dirac()
exitCode = 0

lfn = args[0]
seName = args[1]

try:
  f = open( lfn, 'r' )
  lfns = f.read().splitlines()
  f.close()
except:
  lfns = [lfn]
if FCCheck == 'NOLFC':
  successRemoved = []
  failedRemoved = []
  print 'WARNING: removing physical replica from storage, without removing entry in the FC'
  from DIRAC.Resources.Storage.StorageElement         import StorageElement
  se = StorageElement( seName )
  from DIRAC.DataManagementSystem.Client.ReplicaManager import ReplicaManager
  rm = ReplicaManager()
  for lfn in lfns:
    # check if it is registered in LFC
    res = rm.getReplicaIsFile( lfn, seName )
    if res['OK']:
      print 'WARNING: file is registered in FC! it will NOT be removed from storage! ', res
      continue

    res = se.getPfnForLfn( lfn )
    if not res['OK']:
      print 'ERROR: ', result['Message']
      continue
    surl = res[ 'Value']
    res = rm.removeStorageFile( surl, seName )
    if not res['OK']:
      print 'ERROR: ', res['Message']
      continue
    success = res['Value']['Successful']
    for file in success.keys():
      successRemoved.append( file )
    failed = res['Value']['Failed']
    for file in failed:
      failedRemoved.append( file )
  print 'Summary:'
  print 'Successfully removed: ', successRemoved
  print 'Failed to remove: ', failedRemoved
else:
  for lfn in lfns:
    result = dirac.removeReplica( lfn, seName, printOutput = True )
    if not result['OK']:
      print 'ERROR: ', result['Message']
      exitCode = 2

DIRAC.exit( exitCode )
