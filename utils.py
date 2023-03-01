import os
import pandas as pd
import requests
from datetime import datetime
import json

### SPARQL Queries
def query_by_item_label(label: str, include_aliases: bool = True) -> str:
    label_criteria = 'rdfs:label|skos:altLabel'
    if not include_aliases:
        label_criteria = 'rdfs:label'
    query_string = """
        SELECT ?item ?itemLabel ?itemDescription ?itemAltLabel WHERE{  
        ?item %s "%s"@en.
        SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }    
        }
    """ % (label_criteria, label)

    return query_string

def query_item_subclasses(item_id: str, subclass_property_id: str = 'P13') -> str:
    query_string = """
        SELECT ?item ?itemLabel (GROUP_CONCAT(DISTINCT ?subclassOf; SEPARATOR=",") as ?subclasses)
        {
        VALUES (?item) {(wd:%s)}
        OPTIONAL {
            ?item wdt:%s ?subclassOf
        }
        SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
        } GROUP BY ?item ?itemLabel
    """ % (item_id, subclass_property_id)

    return query_string

property_query = """
SELECT ?property ?propertyLabel ?propertyDescription ?propertyAltLabel WHERE {
    ?property a wikibase:Property .
    SERVICE wikibase:label { bd:serviceParam wikibase:language "en" .}
 }
 """

def sparql_query(endpoint: str, query: str, output: str = 'raw'):
    r = requests.get(
        endpoint, 
        params = {'format': 'json', 'query': query}
    )

    if r.status_code != 200:
        return
    
    try:
        json_results = r.json()
    except Exception as e:
        return

    wd_countries = pd.DataFrame(r.json()['results']['bindings'])

    if output == 'raw':
        return json_results
    else:
        data_records = []
        var_names = json_results['head']['vars']

        for record in json_results['results']['bindings']:
            data_record = {}
            for var_name in var_names:
                data_record[var_name] = record[var_name]['value'] if var_name in record else None
            data_records.append(data_record)
        
        if output == 'dataframe':
            return pd.DataFrame(data_records)
        else:
            return data_records

