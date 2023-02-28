# GeoKB Notebook-based Bots
The Geoscience Knowledgebase (GeoKB) is a framework for assembling, organizing, growing, and reasoning (AI) knowledge about the earth system. We are building it on the Wikibase infrastructure to take advantage of tools and techniques already in use across many other domains. Much of the content that flows into the GeoKB comes from existing sources, both static and dynamic. We use bots as one method to build entities and claims, some of which make best sense as computational notebooks. This repository is dedicated to those notebook bots that are foudnational to initializing an GeoKB instance or that are otherwise part of the core development effort.

Over time, we will likely develop the following types of bots:
* Bots designed to process specific source data and information into the GeoKB (e.g., bring in scientific reference material like journal articles and government reports)
* Bots designed to handle the inner workings of the GeoKB from the initialization of properties and classifiers to the introduction of claims that arise from other things showing up in the knowledgebase
* Bots that handle the regularized production of different kinds of output transformations from the GeoKB such as generating geospatial databases and spinning up online GIS services

## The Notebooks

* [Initialize GeoKB](Initialize GeoKB.ipynb) - works through the process of initializing a new knowledgebase (and occasionally updating) with the foundational properties and top-level classification items that will form the "instance of" classification of core items in the knowledgebase
* [GeoArchive (Zotero)](GeoArchive - Zotero.ipynb) - explores how we map documents stored in the Zotero part of our GeoArchive work to GeoKB items and claims
* [SEC Companies/Filings](SEC Companies and Mining Filings.ipynb) - explores using the SEC EDGAR API to identify companies involved in mining and mineral exploration and relevant filings we need to identify and process for claims about mineral exploration history

## Other Methods
Bots, whether built in notebook form or some other packaging, are one method of handling more routine or regular input to the GeoKB. We'll use these for cases where we need to process an entire source over and over again to incorporate new records and updates or to reprocess information into a new knowledge encoding.

Other routes we are exploring will take advantage of the longstanding QuickStatements tool and related methods to produce QuickStatements encoding through OpenRefine. We are also exploring the use of GIS software where part of the work includes viewing a batch of items in a GIS (via point coordinate location with a property using the globe-coordinate datatype) and doing work on either the geospatial piece or associated property data. These will get fed back into the system via some type of bot action that will incorporate edits, including new items. The GIS part of this will take some additional work as we need to also deal with items in the GeoKB with more complex geometry, likely using a different approach than the Wikidata/Wikimedia Commons connection with the GeoShape datatype.

## Python Package
We are iteratively working to build our abstracted functionality in a deployable Python package based on the pywikibot package that impose the rules and conventions we are evolving for the GeoKB. Both that package and the notebooks may prove useful for other communinities. That package is being built by a contract group engaged in this work and will be spun up in a separate deployable repo soonish.

## Dependencies
See the environment.yml for a complete Conda environment if you choose to go that route. My environment is built on a Python 3.11 base with Anaconda. You can build it however you want, though, and other versions of the basic dependencies should work. 

### Primary packages

* Jupyter (pick your flavor for running ipynb Notebooks)
* WikibaseIntegrator (PyPi) - primary API into a Wikibase instance
* requests (CondaForge) - primary means of interfacing with SPARQL service from Wikibase and other HTTP REST
* pyzotero (PyPi) - API for Zotero
* sec-api (PyPi) - API for SEC EDGAR

I also use Pandas and GeoPandas along with a handful of other custom packages. You can go a different route on data handling if you'd like.

## Authentication and Bot Accounts

For GeoKB purposes, a bot account represents not only a means of connecting with the system to do stuff but an important aspect of provenance. A bot is responsible for doing something specific, once or over a duration. Everything that happens in a Wikibase instance is recorded in history, which is accessible through the API (and UI) for reasoning and making judgments about the viability of information for use.

While we can flag a normal user account as a bot account in Wikibase, the convention of having a real person responsible for a bot is quite useful. Sure, we'll have bots operating independently on schedules or other triggers using Lambdas or other technologies over time, but there should be a real person who stands behind the actions of every bot.

Bots should be specific to a logical set of tasks. Creative names are fine, but we should try to use things that are reasonably short and descriptive so when they show up in provenance as actors, we have a clue about what they might have been up to.

### Setup Bot Account(s)
* Go to the Wikibase instance (local or deployed) and navigate to "Special pages" (/Special:SpecialPages)
* Under Users and rights select "Bot passwords"
* Log in with your credentials set up for the Wikibase instance
* You'll see a list of any existing bot names. You can navigate to one to reset a password as needed. Otherewise, use "Create a new bot password" and give your bot a reasonable name for what it will be doing.

Note: We need to come back to this with more guidance on bot permissions once we figure all that out.

## WikibaseIntegrator
After struggling for a while using pywikibot as an approach to connecting with the Wikibase APIs, I went another route with WikibaseIntegrator. It got me past an issue I kept having with claims, which was probably operator error, but it also offers a much more straightforward method for connecting to a Wikibase instance. I also find its syntax much easier to follow and implement.

### Configuring WBI

The following three variables need to be set for connecting to a specific Wikibase instance:

```python
from wikibaseintegrator.wbi_config import config as wbi_config

wbi_config['MEDIAWIKI_API_URL'] = '' # Generally something like the base domain with /w/api.php in the path
wbi_config['SPARQL_ENDPOINT_URL'] = '' # Depends on the configuration of the WQDS component in the stack
wbi_config['WIKIBASE_URL'] = '' # Generally the base domain of the MediaWiki instance
```

It's a good practice to set these variables in the Python environment and pull them in from there to configure WBI.

### Authenticating WBI

OAuth authentication is probably most secure, but I'm currently just storing individual bot names and passwords needed for specific operations as environment variables and using simple user/password authentication with wikibaseintegrator.wbi_login. Bot names are passed in as `<real user>@<bot name>`.

## Packaging Functional Code

As we work out overall methodology, there will be certain common operations and procedures that would be useful to have in an abstracted package we can import into processing workflows. Over time, we may start much of that within a given notebook, move functions to a local import, and then engineer to a deployable package as another project.

# Disclaimer

This software is preliminary or provisional and is subject to revision. It is being provided to meet the need for timely best science. The software has not received final approval by the U.S. Geological Survey (USGS). No warranty, expressed or implied, is made by the USGS or the U.S. Government as to the functionality of the software and related material nor shall the fact of release constitute any such warranty. The software is provided on the condition that neither the USGS nor the U.S. Government shall be held liable for any damages resulting from the authorized or unauthorized use of the software.

