"""  TransferAgent takes transfer requests from the RequestDB and replicates them
"""

from DIRAC  import gLogger, gConfig, S_OK, S_ERROR
from DIRAC.Core.Base.Agent import Agent
from DIRAC.Core.Utilities.Pfn import pfnparse, pfnunparse
from DIRAC.RequestManagementSystem.Client.Request import RequestClient
from DIRAC.RequestManagementSystem.Client.DataManagementRequest import DataManagementRequest
from DIRAC.DataManagementSystem.Client.ReplicaManager import ReplicaManager
import time
from types import *

AGENT_NAME = 'DataManagement/TransferAgent'

class TransferAgent(Agent):

  def __init__(self):
    """ Standard constructor
    """
    Agent.__init__(self,AGENT_NAME)

  def initialize(self):
    result = Agent.initialize(self)
    self.RequestDBClient = RequestClient()
    self.ReplicaManager = ReplicaManager()
    return result

  def execute(self):

    ################################################
    # Get a request from request DB
    res = self.RequestDBClient.getRequest('transfer')
    if not res['OK']:
      gLogger.info("TransferAgent.execute: Failed to get request from database.")
      return S_OK()
    elif not res['Value']:
      gLogger.info("TransferAgent.execute: No requests to be executed found.")
      return S_OK()
    requestString = res['Value']['requestString']
    requestName = res['Value']['requestName']
    sourceServer= res['Value']['Server']
    gLogger.info("TransferAgent.execute: Obtained request %s" % requestName)
    oRequest = DataManagementRequest(request=requestString)

    ################################################
    # Find the number of sub-requests from the request
    res = oRequest.getNumSubRequests('transfer')
    if not res['OK']:
      errStr = "TransferAgent.execute: Failed to obtain number of transfer subrequests."
      gLogger.error(errStr,res['Message'])
      return S_OK()
    gLogger.info("TransferAgent.execute: Found %s sub requests." % res['Value'])

    ################################################
    # For all the sub-requests in the request
    for ind in range(res['Value']):
      gLogger.info("TransferAgent.execute: Processing sub-request %s." % ind)
      subRequestAttributes = oRequest.getSubRequestAttributes(ind,'transfer')['Value']
      if subRequestAttributes['Status'] == 'Waiting':
        subRequestFiles = oRequest.getSubRequestFiles(ind,'transfer')['Value']
        operation = subRequestAttributes['Operation']

        ################################################
        #  If the sub-request is a put and register operation
        if operation == 'putAndRegister':
          gLogger.info("TransferAgent.execute: Attempting to execute %s sub-request." % operation)
          diracSE = subRequestAttributes['TargetSE']
          for subRequestFile in subRequestFiles:
            if subRequestFile['Status'] == 'Waiting':
              lfn = subRequestFile['LFN']
              file = subRequestFile['PFN']
              guid = subRequestFile['GUID']
              res = self.ReplicaManager.putAndRegister(lfn, file, diracSE, guid=guid)
              if res['OK']:
                if res['Value']['Successful'].has_key(lfn):
                  if not res['Value']['Successful'][lfn].has_key('put'):
                    gLogger.info("TransferAgent.execute: Failed to put %s to %s." % (lfn,diracSE))
                  elif not res['Value']['Successful'][lfn].has_key('register'):
                    gLogger.info("TransferAgent.execute: Successfully put %s to %s in %s seconds." % (lfn,diracSE,res['Value']['Successful'][lfn]['put']))
                    gLogger.info("TransferAgent.execute: Failed to register %s to %s." % (lfn,diracSE))
                    oRequest.setSubRequestFileAttributeValue(ind,'transfer',lfn,'Status','Done')
                    fileDict = res['Value']['Failed'][lfn]['register']
                    registerRequestDict = {'Attributes':{'TargetSE': fileDict['TargetSE'],'Operation':'registerFile'},'Files':[{'LFN': fileDict['LFN'],'PFN':fileDict['PFN'], 'Size':fileDict['Size'], 'GUID':fileDict['GUID']}]}
                    gLogger.info("TransferAgent.execute: Setting registration request for failed file.")
                    oRequest.addSubRequest(registerRequestDict,'register')
                  else:
                    gLogger.info("TransferAgent.execute: Successfully put %s to %s in %s seconds." % (lfn,diracSE,res['Value']['Successful'][lfn]['put']))
                    gLogger.info("TransferAgent.execute: Successfully registered %s to %s in %s seconds." % (lfn,diracSE,res['Value']['Successful'][lfn]['register']))
                    oRequest.setSubRequestFileAttributeValue(ind,'transfer',lfn,'Status','Done')
                else:
                  errStr = "TransferAgent.execute: Failed to put and register file."
                  gLogger.error(errStr,"%s %s %s" % (lfn,diracSE,res['Value']['Failed'][lfn]))
              else:
                errStr = "TransferAgent.execute: Completely failed to put and register file."
                gLogger.error(errStr, res['Message'])
            else:
              gLogger.info("TransferAgent.execute: File already completed.")

        ################################################
        #  If the sub-request is a put operation
        elif operation == 'put':
          gLogger.info("TransferAgent.execute: Attempting to execute %s sub-request." % operation)
          diracSE = subRequestAttributes['TargetSE']
          for subRequestFile in subRequestFiles:
            if subRequestFile['Status'] == 'Waiting':
              lfn = subRequestFile['LFN']
              file = subRequestFile['PFN']
              res = self.ReplicaManager.put(lfn, file, diracSE)
              if res['OK']:
                if res['Value']['Successful'].has_key(lfn):
                  gLogger.info("TransferAgent.execute: Successfully put %s to %s in %s seconds." % (lfn,diracSE,res['Value']['Successful'][lfn]))
                  oRequest.setSubRequestFileAttributeValue(ind,'transfer',lfn,'Status','Done')
                else:
                  errStr = "TransferAgent.execute: Failed to put file."
                  gLogger.error(errStr,"%s %s %s" % (lfn,diracSE,res['Value']['Failed'][lfn]))
              else:
                errStr = "TransferAgent.execute: Completely failed to put file."
                gLogger.error(errStr, res['Message'])
            else:
              gLogger.info("TransferAgent.execute: File already completed.")

        ################################################
        #  If the sub-request is a replicate and register operation
        elif operation == 'replicateAndRegister':
          gLogger.info("TransferAgent.execute: Attempting to execute %s sub-request." % operation)
          targetSE = subRequestAttributes['TargetSE']
          sourceSE = subRequestAttributes['SourceSE']
          for subRequestFile in subRequestFiles:
            if subRequestFile['Status'] == 'Waiting':
              lfn = subRequestFile['LFN']
              res = self.ReplicaManager.replicateAndRegister(lfn,targetSE,sourceSE=sourceSE)
              if res['OK']:
                if res['Value']['Successful'].has_key(lfn):
                  if not res['Value']['Successful'][lfn].has_key('replicate'):
                    gLogger.info("TransferAgent.execute: Failed to replicate %s to %s." % (lfn,targetSE))
                  elif not res['Value']['Successful'][lfn].has_key('register'):
                    gLogger.info("TransferAgent.execute: Successfully replicated %s to %s in %s seconds." % (lfn,targetSE,res['Value']['Successful'][lfn]['replicate']))
                    gLogger.info("TransferAgent.execute: Failed to register %s to %s." % (lfn,targetSE))
                    oRequest.setSubRequestFileAttributeValue(ind,'transfer',lfn,'Status','Done')
                    fileDict = res['Value']['Failed'][lfn]['register']
                    registerRequestDict = {'Attributes':{'TargetSE': fileDict['TargetSE'],'Operation':'registerReplica'},'Files':[{'LFN': fileDict['LFN'],'PFN':fileDict['PFN']}]}
                    gLogger.info("TransferAgent.execute: Setting registration request for failed replica.")
                    oRequest.addSubRequest(registerRequestDict,'register')
                  else:
                    gLogger.info("TransferAgent.execute: Successfully replicated %s to %s in %s seconds." % (lfn,targetSE,res['Value']['Successful'][lfn]['replicate']))
                    gLogger.info("TransferAgent.execute: Successfully registered %s to %s in %s seconds." % (lfn,targetSE,res['Value']['Successful'][lfn]['register']))
                    oRequest.setSubRequestFileAttributeValue(ind,'transfer',lfn,'Status','Done')
                else:
                  errStr = "TransferAgent.execute: Failed to replicate and register file."
                  gLogger.error(errStr,"%s %s %s" % (lfn,targetSE,res['Value']['Failed'][lfn]))
              else:
                errStr = "TransferAgent.execute: Completely failed to replicate and register file."
                gLogger.error(errStr, res['Message'])
            else:
              gLogger.info("TransferAgent.execute: File already completed.")

        ################################################
        #  If the sub-request is a replicate operation
        elif operation == 'replicate':
          gLogger.info("TransferAgent.execute: Attempting to execute %s sub-request." % operation)
          targetSE = subRequestAttributes['TargetSE']
          sourceSE = subRequestAttributes['SourceSE']
          for subRequestFile in subRequestFiles:
            if subRequestFile['Status'] == 'Waiting':
              lfn = subRequestFile['LFN']
              res = self.ReplicaManager.replicate(lfn,targetSE,sourceSE=sourceSE)
              if res['OK']:
                if res['Value']['Successful'].has_key(lfn):
                  gLogger.info("TransferAgent.execute: Successfully replicated %s to %s in %s seconds." % (lfn,diracSE,res['Value']['Successful'][lfn]))
                  oRequest.setSubRequestFileAttributeValue(ind,'transfer',lfn,'Status','Done')
                else:
                  errStr = "TransferAgent.execute: Failed to replicate file."
                  gLogger.error(errStr,"%s %s %s" % (lfn,targetSE,res['Value']['Failed'][lfn]))
              else:
                errStr = "TransferAgent.execute: Completely failed to replicate file."
                gLogger.error(errStr, res['Message'])
            else:
              gLogger.info("TransferAgent.execute: File already completed.")

        ################################################
        #  If the sub-request is none of the above types
        else:
          gLogger.error("TransferAgent.execute: Operation not supported.", operation)

        ################################################
        #  Determine whether there are any active files
        if oRequest.isSubRequestEmpty(ind,'transfer')['Value']:
          oRequest.setSubRequestStatus(ind,'transfer','Done')

      ################################################
      #  If the sub-request is already in terminal state
      else:
        gLogger.info("TransferAgent.execute: Sub-request %s is status '%s' and  not to be executed." % (ind,subRequestAttributes['Status']))

    ################################################
    #  Generate the new request string after operation
    requestString = oRequest.toXML()['Value']
    res = self.RequestDBClient.updateRequest(requestName,requestString,sourceServer)

    return S_OK()
