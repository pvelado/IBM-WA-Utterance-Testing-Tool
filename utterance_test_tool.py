"""
Auther: Paulo Velado

utterance_test_tool.py: Script takes in a single csv file with a single column of utterances. The Utterances will be fed into 
and Assistant instance created within the IBM Watson Assistant Service and return a JSON on the output data of that response. 
The JSON data will then be parsed into a data frame and exported to a excel document.
Output data includes:
-Utterance 
-Response 
-Node triggered by utterance
-Condition of triggered node
-Top three Intents triggered by utterance
-Confidence Score of each Intent
-Top 4 Entities triggered by response

"""

import ibm_watson
import json
import csv
import warnings
import pandas as pd
import tkinter as tk
from tkinter import filedialog
from ibm_watson import AssistantV2
from ibm_cloud_sdk_core.authenticators import IAMAuthenticator

    # Enter Credentials from your Watson Assistant Service
ASSISTANT_ID = "[ENTER ASSISTANT ID HERE]"
API_KEY = '[ENTER APY KEY HERE]'
VERSION = '[ENTER VERSION]'
SERVICE_URL = '[ENTER URL HERE]'
warnings.filterwarnings("ignore") 

###################################################WA ASSISTANT CONNECTION###############################################

    # Creates a connection to the WA assistant instance and returns assistant connection
def connect_to_service():
    authenticator = IAMAuthenticator(API_KEY)
    assistant = AssistantV2(
        version = VERSION,
        authenticator = authenticator
    )
    assistant.set_service_url(SERVICE_URL)
    assistant.set_disable_ssl_verification(True) # if behind corprate firewall turn to "True"
    return assistant
    
    # Creates a session for the WA assistant and returns the a reference ID
def create_session_id (assistant_service):
    temp = assistant_service.create_session(assistant_id=ASSISTANT_ID).get_result()
    session_id = temp["session_id"]
    return session_id


    #Connects to WA assistant with session that was created, inputs utterance, returns output as json, then deletes session
def pull_json_output(utterance,session_id,assistant_service):

        #initial connection to session to trigger "welcome statment"
    assistant_service.message(
        assistant_id=ASSISTANT_ID,
        session_id=session_id,
        input= {"text" : ""}
    )
        #second connection to session feeds
    json_output = assistant_service.message(
        assistant_id=ASSISTANT_ID,
        session_id=session_id,
        input= {
            "text" : utterance,
            "options" : {
                "alternate_intents": True,
                "debug": True,
            }
        }
    ).get_result()

    assistant_service.delete_session(ASSISTANT_ID,session_id) #delets session before timed out
    return json_output

################################################### DATAFRAME CREATION ##################################################

    # Saves CSV of utterances to dataframe and returns dataframe
def create_utterance_dataframe(csv_file_path):

    df = pd.read_csv(csv_file_path, header=None )
    df = df.rename(columns = {0:"Utterances"})
    return df

    # Function constucts and returns main dataframe that will be exported
def build_main_dataframe(utterance_df,columns_list,assistant_service):


    df = utterance_df #add utterances as the begining column in the dataframe.

        # Adds a list of column names sequentially, as empty dataframe columns.
    for i in range (len(columns_list)):
        df.insert(len(utterance_df.columns), columns_list[i], "")

        #Iterates through the column of utterances
        #Retrives the output for each utterance 
        #Parses the json output and populates each row sequentially in the dataframe
        #Note: each utterances requires the creation of a new session
    for i in utterance_df.index:

        print ("Processing Line = " + str(i+1)) # Terminal output of what line is being processed in the dataframe.

        session_id = create_session_id(assistant_service)
        utterance = utterance_df.loc[i,"Utterances"] 
        json_output = pull_json_output(utterance,session_id,assistant_service) # raw json output.


        # "if" statments below check if column is present in dataframe, runs parsing function, then populates dataframe.

        if "Responses" in df.columns:
            df.loc[i,"Responses"] = get_response(json_output)

        if "Triggered Node" in df.columns:
            name, condition = get_triggered_node (json_output)
            df.loc[i,"Triggered Node"] = name
            df.loc[i,"Node Condition"] = condition
        
        if "Intent 1" in  df.columns:
            i1, cs1, i2, cs2, i3, cs3 = get_intents(json_output)
            df.loc[i,"Intent 1"] = i1
            df.loc[i,"Confidence Score 1"] = cs1
            df.loc[i,"Intent 2"] = i2
            df.loc[i,"Confidence Score 2"] = cs2
            df.loc[i,"Intent 3"] = i3
            df.loc[i,"Confidence Score 3"] = cs3
        if "Entity 1" in df.columns:
            e1,e2,e3,e4 = get_entities(json_output)
            df.loc[i,"Entity 1"] = e1
            df.loc[i,"Entity 2"] = e2
            df.loc[i,"Entity 3"] = e3
            df.loc[i,"Entity 4"] = e4

    df = df.convert_dtypes() #Converts the columns from "object" data type to proper data type.
    return df

################################################# JSON OUTPUT PARSING ######################################################################
    #Parses and out and returns the response from the raw json output
def get_response(json_output):
    response = ""
    for i in range (len(json_output["output"]["generic"])):

        if json_output["output"]["generic"][i]["response_type"] == "option":
             response = response + json_output["output"]["generic"][i]["title"] + "\n\n"
             for j in range (len(json_output["output"]["generic"][i]["options"])):
                 response = response + json_output["output"]["generic"][i]["options"][j]["label"] + "\n"
        elif json_output["output"]["generic"][i]["response_type"] == "text":
             response = response + json_output["output"]["generic"][i]["text"] + "\n\n"

    return response

    #Parses out and returns the Node that response came from and the node condition from the raw json output
def get_triggered_node (json_output):
    node_name = ""
    node_condition = ""
    if any("nodes_visited" in x for x in json_output["output"]["debug"]):
        for i in reversed(range (len(json_output["output"]["debug"]["nodes_visited"]))):
            if json_output["output"]["debug"]["nodes_visited"][i]["title"] != "anything_else_help":
                node_name = json_output["output"]["debug"]["nodes_visited"][i]["title"]
                node_condition = json_output["output"]["debug"]["nodes_visited"][i]["conditions"]
                break
    return node_name,node_condition

    # Parses out and returns the top 3 intents that the utterance triggered and their confidence score
def get_intents(json_output):
    intent_1 = ""
    confidence_score_1 = ""
    intent_2 = ""
    confidence_score_2 = ""
    intent_3 = ""
    confidence_score_3 = ""

    for i in range(len(json_output["output"]["intents"])):
        if i == 0:
            intent_1 = json_output["output"]["intents"][i]["intent"]
            confidence_score_1 = json_output["output"]["intents"][i]["confidence"]
        elif i == 1:
            intent_2 = json_output["output"]["intents"][i]["intent"]
            confidence_score_2 = json_output["output"]["intents"][i]["confidence"]
        elif i == 2:
            intent_3 = json_output["output"]["intents"][i]["intent"]
            confidence_score_3 = json_output["output"]["intents"][i]["confidence"]
        else:
            break

    return intent_1, confidence_score_1, intent_2, confidence_score_2, intent_3, confidence_score_3


    # Parses out and returns the top 4 entities that were triggered by utterance
def get_entities(json_output):
    entity_1 = ""
    entity_2 = ""
    entity_3 = ""
    entity_4 = ""

    for i in range (len(json_output["output"]["entities"])):
        if i == 0:
            entity_1 = json_output["output"]["entities"][i]["entity"] + ":" + json_output["output"]["entities"][i]["value"]
        elif i == 1:
            entity_2 = json_output["output"]["entities"][i]["entity"] + ":" + json_output["output"]["entities"][i]["value"]
        elif i == 2:
            entity_3 = json_output["output"]["entities"][i]["entity"] + ":" + json_output["output"]["entities"][i]["value"]
        elif i == 3:
            entity_4 = json_output["output"]["entities"][i]["entity"] + ":" + json_output["output"]["entities"][i]["value"]
        else:
            break
    return entity_1, entity_2, entity_3, entity_4



############################################################## MAIN #############################################################
def main():

    columns_list = ["Responses", "Triggered Node", "Node Condition","Intent 1", "Confidence Score 1", "Intent 2", "Confidence Score 2", "Intent 3", "Confidence Score 3","Entity 1","Entity 2","Entity 3","Entity 4"]
    
    csv_file_path = "[CSV PATH]" # Enter the path where the test sample csv file resides.

    assistant_service = connect_to_service()

    utterance_df = create_utterance_dataframe(csv_file_path)
    
    main_df = build_main_dataframe(utterance_df,columns_list,assistant_service)

    main_df.to_excel("[EXPORT LOCATION PATH]output.xlsx", index = False) # Enter the path to the directory you wish to export the "output.xlsx" to.
if __name__ == '__main__':
    main()