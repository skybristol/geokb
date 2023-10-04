import os
import requests
import pandas as pd
import json
from urllib.parse import urlparse, parse_qs, quote
from wikibaseintegrator.wbi_config import config as wbi_config
from wikibaseintegrator import WikibaseIntegrator, wbi_login
from wikibaseintegrator import models, datatypes
from wikibaseintegrator.wbi_enums import WikibaseDatatype, ActionIfExists, WikibaseDatePrecision
from sqlalchemy import create_engine
import mwclient

class WikibaseConnection:
    def __init__(
        self, 
        bot_name: str,
        authenticate: bool = True,
        load_refs: bool = True):
        if f"WB_SPARQL_{bot_name}" not in os.environ:
            if os.path.isfile('env_vars.sh'):
                # Workaround for MPC environment
                with open('env_vars.sh') as file:
                    for l in file:
                        if l.startswith('export'):
                            varcmd = l.split(" ")[1]
                            var = varcmd.split("=")[0]
                            val = varcmd.split("=")[1].strip()
                            val = val[1:-1]
                            os.environ[var] = val
            else:
                raise ValueError("Environment does not appear to contain required variables to run this code.")

        # Set basic parameters from env variables we have to know about to start operating
        self.sparql_endpoint = os.environ[f'WB_SPARQL_{bot_name}']
        self.wikibase_url = os.environ[f'WB_URL_{bot_name}']
        self.bot_user_agent = f'{bot_name}/1.0 ({os.environ[f"WB_URL_{bot_name}"]})'

        # WikibaseIntegrator config
        wbi_config['MEDIAWIKI_API_URL'] = os.environ[f'WB_API_{bot_name}']
        wbi_config['SPARQL_ENDPOINT_URL'] = os.environ[f'WB_SPARQL_{bot_name}']
        wbi_config['WIKIBASE_URL'] = os.environ[f'WB_URL_{bot_name}']
        wbi_config['USER_AGENT'] = self.bot_user_agent
        
        # Instantiate important aspect of WBI for calling from elsewhere
        self.models = models
        self.datatypes = datatypes
        self.wbi_data_types = WikibaseDatatype
        self.action_if_exists = ActionIfExists
        self.date_precision = WikibaseDatePrecision

        self.site_domain = os.environ[f'WB_URL_{bot_name}'].split("/")[-1]

        # Establish authentication connection to instance
        if authenticate:
            self.login_instance = wbi_login.Login(
                user=os.environ[f'WB_BOT_{bot_name}'],
                password=os.environ[f'WB_BOT_PASS_{bot_name}']
            )
            self.wbi = WikibaseIntegrator(login=self.login_instance)

            # Establish site for writing to Mediawiki pages
            self.mw_site = mwclient.Site(
                self.site_domain, 
                path='/w/', 
                scheme='https', 
                clients_useragent=self.bot_user_agent
            )
            self.mw_site.login(username=os.environ[f'WB_BOT_{bot_name}'], password=os.environ[f'WB_BOT_PASS_{bot_name}'])
            
        # Set up queries
        self.property_query = "SELECT%20%3Fproperty%20%3FpropertyLabel%20%3Fproperty_type%20WHERE%20%7B%0A%20%20%3Fproperty%20a%20wikibase%3AProperty%20.%0A%20%20%3Fproperty%20wikibase%3ApropertyType%20%3Fproperty_type%20.%0A%20%20SERVICE%20wikibase%3Alabel%20%7B%20bd%3AserviceParam%20wikibase%3Alanguage%20%22en%22%20.%20%7D%0A%7D%0A"

        # Set up configuration details and references        
        if load_refs:
            # config_file = json.load(open(f'{bot_name}.json', 'r'))
            # self.config = config_file[bot_name]
            self.wb_properties, self.prop_lookup = self.get_properties()
        
    # Parameters
    def sparql_namespaces(self):
        namespaces = """
        PREFIX wd: <%(wikibase_url)s/entity/>
        PREFIX wdt: <%(wikibase_url)s/prop/direct/>
        """ % {'wikibase_url': self.wikibase_url}

        return namespaces
    
    # Core Functions
    def url_sparql_query(self, sparql_url: str, output_format: str = 'dataframe'):
        r = requests.get(sparql_url, headers={'accept': 'application/sparql-results+json'})
        if r.status_code != 200:
            return
        
        if output_format == "dataframe":
            return self.df_sparql_results(json_results=r.json())
        
        return r.json()
    
    def simplify_sparql_results(self, json_results: dict):
        if "results" not in json_results and "bindings" not in json_results["results"]:
            return

        data_records = []
        var_names = json_results['head']['vars']

        for record in json_results['results']['bindings']:
            data_record = {}
            for var_name in var_names:
                data_record[var_name] = record[var_name]['value'] if var_name in record else None
            data_records.append(data_record)
        
        return data_records

    def df_sparql_results(self, json_results: dict):
        data_records = self.simplify_sparql_results(json_results)
        return pd.DataFrame(data_records)

    def key_lookup(self, df_results: dict, k_prop: str, v_prop: str):
        return df_results.set_index(k_prop)[v_prop].to_dict()

    def wb_ref_data(self, ref=None, query=None):
        if ref is not None:
            q = self.config["queries"][ref]
        elif query is not None:
            q = query
        else:
            return
        q_url = f"{self.sparql_endpoint}?query={q}"
        json_results = self.url_sparql_query(q_url)
        df = self.df_sparql_results(json_results)

        return df

    def get_properties(self):
        query_url = f"{self.sparql_endpoint}?query={self.property_query}"
        df_props = self.url_sparql_query(
            sparql_url=query_url,
            output_format="dataframe"
        )
        df_props["pid"] = df_props.property.apply(lambda x: x.split("/")[-1])
        df_props["p_type"] = df_props.property_type.apply(lambda x: x.split("#")[-1])
        prop_lookup = self.key_lookup(
            df_props, 
            k_prop="propertyLabel",
            v_prop="pid"
        )

        return df_props, prop_lookup

    def get_classes(self):
        df_classes = self.wb_ref_data('classes')
        df_classes["qid"] = df_classes['class'].apply(lambda x: x.split("/")[-1])
        class_lookup = self.key_lookup(
            df_classes, 
            k_prop="classLabel",
            v_prop="qid"
        )

        return df_classes, class_lookup

    def get_references(self):
        df_refs = self.wb_ref_data('references')
        df_refs["qid"] = df_refs['ref_source'].apply(lambda x: x.split("/")[-1])
        ref_lookup = self.key_lookup(
            df_refs, 
            k_prop="ref_sourceLabel",
            v_prop="qid"
        )

        return df_refs, ref_lookup

    def datasource(self, ds_qid: str):
        """
        This is the somewhat complicated query for all properties and qualifiers on an item.
        """
        ds_query = """
        %(namespaces)s

        SELECT ?wdLabel ?ps_ ?ps_Label ?ps_type ?wdpq ?wdpqLabel ?pq_ ?pq_Label 
        {
          VALUES (?datasource) {(wd:%(ds_qid)s)}

          ?datasource ?p ?statement .
          ?statement ?ps ?ps_ .

          ?wd wikibase:claim ?p.
          ?wd wikibase:statementProperty ?ps.

          OPTIONAL {
          ?statement ?pq ?pq_ .
          ?wdpq wikibase:qualifier ?pq .
          }

          OPTIONAL { ?ps_ wikibase:propertyType ?ps_type . }

          SERVICE wikibase:label { bd:serviceParam wikibase:language "en" }
        } ORDER BY ?datasourceLabel ?wd ?statement ?ps_
        """ % {
            'namespaces': self.sparql_namespaces(),
            'ds_qid': ds_qid
        }

        ds_wb_source = self.sparql_query(
            query=ds_query,
            output="dataframe"
        )
        
        return ds_wb_source

    def item_by_label(self, label: str, id_only: bool = False):
        label_query = """
        SELECT ?item
        WHERE {
            ?item ?label "%s"@en .
        }
        """ % label
        
        results = self.sparql_query(
            query=label_query,
            output="raw"
        )

        if id_only:
            ids = []
            if results["results"]["bindings"]:
                return [i[list(i.keys())[0]]["value"].split('/')[-1] for i in results["results"]["bindings"]]
        
        return results
    
    # Utilities
    def extract_wbid(self, url):
        # Extracts QID or PID from the end of a URL-formatted identifier
        return url.split('/')[-1]
        
    def sparql_query(self, query: str, endpoint: str = None, output: str = 'dataframe'):
        # Run SPARQL query against target Wikibase instance of another endpoint
        # Handles some processing of results needed often
        if not endpoint:
            endpoint = self.sparql_endpoint
        
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
        
        if not json_results['results']['bindings']:
            return

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
            elif output == 'lookup':
                # Assumes first column contains identifier and second column contains label
                df = pd.DataFrame(data_records)
                df['lookup_value'] = df.iloc[:, 1]
                df['identifier'] = df.iloc[:, 0].apply(lambda x: x.split('/')[-1])
                return df[['lookup_value','identifier']].set_index('lookup_value').to_dict()['identifier']
            else:
                return data_records

    def parse_sparql_url(self, url: str, param: str = 'query'):
        # Parse the query out of a SPARQL statement in URL form so we can run it in a different context
        x = urlparse(url)
        
        sparql_endpoint=f"{x.scheme}://{x.netloc}{x.path}"
        sparql_query = parse_qs(x.query)[param][0]
        
        return sparql_endpoint, sparql_query
    
    def get_html_table(self, url: str, table_ordinal: int = 0, injection: dict = None):
        # Retrieve tabular data from an HTML page
        tables_on_page = pd.read_html(url)

        if not tables_on_page:
            return

        # Build a converter to get everything as strings
        data_preview = tables_on_page[table_ordinal]
        converters = {c:str for c in data_preview.columns}

        # Retrieve the tables again using the converters
        tables_on_page = pd.read_html(url, converters=converters)

        # Get specific table
        df = tables_on_page[table_ordinal]
        
        # Inject extra information if specified
        if injection is not None:
            for k, v in injection.items():
                df[k] = v

        return df
    
    def pg_cnxn(self, db, db_user, db_pass, db_host, db_port):
        if db_user is None:
            return
        try:
            engine = create_engine(
                f'postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/{db}'
            )
            return engine
        except Exception as e:
            print(e)
            return None
        
    def sparql_query_to_url(self, query_str):
        query_string = quote(query_str).replace('/', '%2F')
        query_url = f"{self.sparql_endpoint}?query={query_string}"
        return query_url
