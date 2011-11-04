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

verbose = False
FCCheck = True
Script.registerSwitch( "v", "Verbose", " use this option for verbose output [False]" )
Script.registerSwitch( "n", "NoLFC", " use this option to force the removal from storage of replicas not registered in FC [by default, replicas not registered are NOT removed from storage]" )

Script.setUsageMessage( '\n'.join( [ __doc__.split( '\n' )[1],
                                     'Usage:',
                                     '  %s [option|cfgfile] ... LFN SE ' % Script.scriptName,
                                     'Arguments:',
                                     '  LFN:      Logical File Name or file containing LFNs',
                                     '  SE:       Valid DIRAC SE' ] ) )
Script.parseCommandLine( ignoreErrors = True )
args = Script.getPositionalArgs()

if len( args ) < 2:
  Script.showHelp()

if len( args ) > 2:
  FCCheck = args[ 2 ]
  print 'Only one LFN SE pair will be considered'
  Script.showHelp()

switches = Script.getUnprocessedSwitches()
for switch in switches:
  if switch[0] == "v" or switch[0].lower() == "verbose":
    verbose = True
  if switch[0] == "n" or switch[0].lower() == "nolfc":
    FCCheck = False

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
if not FCCheck:
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
  if verbose:
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
