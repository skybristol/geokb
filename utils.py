import pywikibot as pwb
import pandas as pd
from SPARQLWrapper import SPARQLWrapper, JSON
from nested_lookup import nested_lookup
from datetime import datetime

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


def sparql_query(endpoint: str, output: str, query: str):
    sparql = SPARQLWrapper(endpoint)
    sparql.setReturnFormat(JSON)

    sparql.setQuery(query)
    results = sparql.queryAndConvert()

    if output == 'raw':
        return results
    elif output == 'dataframe':
        names = results["head"]["vars"]
        data = []
        for name in names:
            property_value = nested_lookup('value', nested_lookup(name, results['results']['bindings']))
            if not property_value:
                data.append(None)
            else:
                data.append(property_value)

        return pd.DataFrame.from_dict(dict(zip(names, data)))

def get_wb(site_name: str, language='en'):
    site = pwb.Site(language, site_name)
    site.login()
    return site

def check_item_label(labels: dict, sparql_endpoint: str, response: str = 'id'):
    label = labels['en']

    query_string = query_by_item_label(label=label)

    query_results = sparql_query(
        endpoint=sparql_endpoint,
        output='raw',
        query=query_string
    )

    if not query_results["results"]["bindings"]:
        return
    
    if len(query_results["results"]["bindings"]) > 1:
        raise ValueError(f"More than one item with the label: {labels}")
    
    if response == 'id':
        return query_results["results"]["bindings"][0]["item"]["value"].split('/')[-1]

    return query_results["results"]["bindings"][0]

def get_entity(
        site: pwb.APISite, 
        entity_id: str = None, 
        entity_type: str = 'item', 
        data_type: str = 'wikibase-item'):

    if entity_id and entity_id.startswith('Q'):
        entity_type = 'item'
    elif entity_id and entity_id.startswith('P'):
        entity_type = 'property'
    else:
        entity_type = entity_type

    if entity_type == 'item':
        return pwb.ItemPage(
            site=site.data_repository(),
            title=entity_id
        )
    elif entity_type == 'property':
        return pwb.PropertyPage(
            source=site.data_repository(),
            title=entity_id,
            datatype=data_type
        )

def edit_labels(
        site: pwb.APISite, 
        labels: dict, 
        prov_statement: str, 
        entity_type: str = 'item', 
        data_type: str = 'wikibase-item'
    ) -> str:
    try:
        entity_id = check_item_label(labels=labels)
    except Exception as e:
        raise ValueError("Problem in running query for item on labels")

    entity = get_entity(
        site=site,
        entity_id=entity_id,
        entity_type=entity_type,
        data_type=data_type
    )

    entity.editLabels(
        labels=labels, 
        summary=prov_statement
    )

    return entity.getID()

def edit_descriptions(site: pwb.APISite, entity_id: str, descriptions: dict, prov_statement: str):
    entity = get_entity(
        site=site,
        entity_id=entity_id
    )

    if entity.getID() == '-1':
        raise ValueError('Entity does not yet exist, create it first')

    entity.editDescriptions(
        descriptions=descriptions,
        summary=prov_statement,
    )
    return entity.get()

def edit_aliases(site: pwb.APISite, entity_id: str, aliases: dict, prov_statement: str):
    entity = get_entity(
        site=site,
        entity_id=entity_id
    )

    if entity.getID() == '-1':
        raise ValueError('Entity does not yet exist, create it first')

    entity.editAliases(
        aliases=aliases,
        summary=prov_statement,
    )
    return entity.get()

def process_item(
        site: pwb.APISite, 
        label: str, 
        prov_statement: str,
        description: str = None, 
        aliases: list = []
    ):

    # Assume English language for now
    label_dict = {'en': label}

    check_item = check_item_label(
        labels=label_dict,
        response='raw'
    )

    if not check_item:
        entity_id = edit_labels(
            site=site,
            labels={'en': 'copper'},
            prov_statement=prov_statement,
            entity_type='item'
        )
        missing_description = description
        missing_aliases = aliases
    else:
        entity_id = check_item['item']['value'].split('/')[-1]
        missing_description = description if description != check_item['itemDescription']['value'] else None
        existing_aliases = [i.strip() for i in check_item['itemAltLabel']['value'].split(',')]
        missing_aliases = list(set(aliases) - set(existing_aliases))

    if missing_description:
        edit_descriptions(
            site=site,
            entity_id=entity_id,
            descriptions={'en': missing_description},
            prov_statement=f'Adding description for {label}'
        )
    
    if missing_aliases:
        edit_aliases(
            site=site,
            entity_id=entity_id,
            aliases={'en': ['Cu','Copper']},
            prov_statement=f'Adding aliases for {label}'
        )

# Still problematic here with ItemPage.get() after adding claims
def add_claim(site: pwb.APISite, subject_item_id: str, property_id: str, claim_value: str, prov_statement: str):
    repo = site.data_repository()

    # Establish connection to item
    subject_item = pwb.ItemPage(repo, subject_item_id)
    if not subject_item.exists():
        raise ValueError(f'Item does not exist: {subject_item_id}')
    
    # Establish connection to property
    property_item = pwb.PropertyPage(repo, property_id)
    try:
        property_datatype = property_item.get()['datatype']
        subject_claim = pwb.Claim(repo, property_id)
    except Exception as e:
        raise ValueError(f'Property does not exist: {property_id}')
    
    if property_datatype == 'wikibase-item':
        # Get item target and verify exists
        claim_object = pwb.ItemPage(repo, claim_value)
        if not claim_object.exists():
            raise ValueError(f"Object item does not exist: {claim_value}")
    else:
        # Need to handle other cases where we property test/format an appropriate claim_target response
        return

    # Set the target for the claim
    subject_claim.setTarget(claim_object)
    # Need to handle additional work of adding references and qualifiers

    # Commit the claim to wikibase
    try:
        subject_item.addClaim(subject_claim, summary=prov_statement)
    except Exception as e:
        raise ValueError("Claim already exists")