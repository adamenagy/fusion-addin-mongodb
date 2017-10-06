#Author-
#Description-

import adsk.core, adsk.fusion, adsk.cam, traceback

# Makes sure that additional modules stored inside the
# add-in folder will be found
import os, sys
my_addin_path = os.path.dirname(os.path.realpath(__file__)) + '/modules' 
if not my_addin_path in sys.path:
   sys.path.append(my_addin_path) 
   
import pymongo

# Makes sure that our path is removed so that other add-ins
# won't accidentally load something from our folders
if my_addin_path in sys.path:
   sys.path.remove(my_addin_path)
   
uri = 'connection string'
# something like 'mongodb://<user name>:<user password>@<server id>.mlab.com:43734/fusion-data'

app = None
ui  = None
commandId = 'FusionDataCreate'
commandName = 'FusionDataCreate'
commandDescription = 'Add attribute to selected component.'

# Global set of event handlers to keep them referenced for 
# the duration of the command
handlers = []

class MyCommandDestroyHandler(adsk.core.CommandEventHandler):
    def __init__(self):
        super().__init__()
    def notify(self, args):
        try:
            print("MyCommandDestroyHandler")
            # When the command is done, terminate the script
            # This will release all globals which will remove all event handlers
            adsk.terminate()
        except:
            if ui:
                ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))
                
class MyExecuteHandler(adsk.core.CommandEventHandler):
    def __init__(self):
        super().__init__()
    def notify(self, args):
        # Code to react to the event.
        print("MyExecuteHandler")
        eventArgs = adsk.core.CommandEventArgs.cast(args)
        inputs = eventArgs.command.commandInputs             
        selInput = adsk.core.SelectionCommandInput.cast(
            inputs.itemById(commandId + '_selection'))
        strInput = adsk.core.StringValueCommandInput.cast(
            inputs.itemById(commandId + '_string'))
        
        body = adsk.fusion.BRepBody.cast(selInput.selection(0).entity)
        #body.attributes.add("FusionData", "StringData", strInput.value)
        
        # If the body is not in the root component
        fullPath = ''
        if type(body.assemblyContext) is adsk.fusion.Occurrence:
            fullPath = body.assemblyContext.fullPathName + "+"
      
        fullPath += body.name
        
        dataFile = app.activeDocument.dataFile
        
        # get document URN
        itemId = dataFile.id
        
        # 
        version = dataFile.versionNumber
        
        projectId = dataFile.parentProject.name
        
        # Store the data in the Mongo DB 
        client = pymongo.MongoClient(uri)

        db = client.get_default_database()
        coll = db['mycollection']
        for document in coll.find():
            print(document) # iterate the cursor
            
        coll.insert({
            'itemId': itemId,    
            'version': version,
            'projectId': projectId,
            'fullPath': fullPath,
            'stringData': strInput.value
        })
        
        client.close()
        
class MyValidateInputsHandler(adsk.core.ValidateInputsEventHandler):
    def __init__(self):
        super().__init__()
    def notify(self, args):
        # Code to react to the event.
        print("MyValidateInputsHandler")
        eventArgs = adsk.core.ValidateInputsEventArgs.cast(args)
        inputs = eventArgs.inputs             
        selInput = adsk.core.SelectionCommandInput.cast(
            inputs.itemById(commandId + '_selection'))
        
        body = adsk.fusion.BRepBody.cast(selInput.selection(0).entity)
        if type(body.assemblyContext) is adsk.fusion.Occurrence:
            eventArgs.areInputsValid = True
        else:
            eventArgs.areInputsValid = False

class MyCommandCreatedHandler(adsk.core.CommandCreatedEventHandler):
    def __init__(self):
        super().__init__()
    def notify(self, args):
        try:
            cmd = adsk.core.Command.cast(args.command)
            
            onDestroy = MyCommandDestroyHandler()
            cmd.destroy.add(onDestroy)
            handlers.append(onDestroy)
            
            onExecute = MyExecuteHandler()
            cmd.execute.add(onExecute)
            handlers.append(onExecute)
            
            #onValidateInputs = MyValidateInputsHandler()
            #cmd.validateInputs.add(onValidateInputs)
            #handlers.append(onValidateInputs)
            
            inputs = adsk.core.CommandInputs.cast(cmd.commandInputs)

            # Create string value input
            selInput = inputs.addSelectionInput(
                commandId + '_selection', 'Selection', 'Select component')
            selInput.selectionFilters = ["Bodies"]

            inputs.addStringValueInput(
                commandId + '_string', 'Text', 'Basic string command input')
        except:
            if ui:
                ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))

def run(context):
    ui = None
    try:
        global app
        app = adsk.core.Application.get()
        global ui
        ui = app.userInterface

        # Create command defintion
        cmdDef = ui.commandDefinitions.itemById(commandId)
        if not cmdDef:
            cmdDef = ui.commandDefinitions.addButtonDefinition(
                commandId, commandName, commandDescription)

        # Add command created event
        onCommandCreated = MyCommandCreatedHandler()
        cmdDef.commandCreated.add(onCommandCreated)
        handlers.append(onCommandCreated)

        # Execute command
        cmdDef.execute()

        # Prevent this module from being terminate when the script returns, 
        # because we are waiting for event handlers to fire
        adsk.autoTerminate(False)

    except:
        if ui:
            ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))
