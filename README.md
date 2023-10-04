# GeoKB Notebook-based Bots
The Geoscience Knowledgebase (GeoKB) is a framework for assembling, organizing, growing, and reasoning (AI) knowledge about the earth system and the role of the USGS in studying it. We are building it on the Wikibase infrastructure to take advantage of tools and techniques already in use across many other domains. Much of the content that flows into the GeoKB comes from existing sources, both static and dynamic. We use bots as one method to build entities and claims, starting initially with computational notebooks and moving toward a microservices architecture to maintain the system over time.

Over time, we will develop the following types of bots:
* Bots designed to process specific source data and information into the GeoKB (e.g., bring in scientific reference material like journal articles and government reports)
* Bots designed to handle the inner workings of the GeoKB from the initialization of properties and classifiers to the introduction of claims that arise from other things showing up in the knowledgebase
* Bots that handle the regularized production of different kinds of output transformations from the GeoKB such as generating geospatial databases and spinning up online GIS services

## Using the tool to build the tool
One design philosophy we are pursuing is the concept of developing the tool to build and operate itself to the extent possible. In this case, the Wikibase framework gives us a robust and flexible content store that we can use as our data and information backing that code operates with. We are experimenting with a couple specific aspects of this idea:

* Almost every claim (statement) should have at least one reference indicating where the claim comes from. We have "data source" and "knowledge source" predicates that link a subject claim to an object item. Items as references document pertinent details about source material, and we are working on the schemas for these such that they contain all the necessary configuration details for processing codes to operate with. In many cases, we envision a claim coupling a source data reference with a source code reference, pointing to the encoded algorithm that does the work of processing the source data.
* We are taking advantage of the Mediawiki foundation for Wikibase and the "discussion" pages that come along with the structured data part of items and properties. We use these for documenting the knowledgebase, similar to how "Property Talk" pages are used in Wikidata (but lacking that detailed structure at this point). But we are also using them as a content store in a couple of specific ways:
    * Cache of source data when the source is less stable or messy to deal with (e.g., USGS staff profiles that have to be web scraped stored as YAML)
    * Housing for additional text content such as abstracts and tables of contents for publications that may or may not undergo additional processing to identify linked data and build claims

## iSAID
Some of the work from an older project called iSAID is being integrated into the GeoKB. This work dealt with building a graph representation for people, organizations, projects, publications, datasets, and models in the USGS. iSAID was focused on scientific capacity assessment use cases, particularly related to understanding the intersection across scientific disciplines in the USGS. Because we need the public aspects of these same entities in the GeoKB for many other use cases, we are porting that work into this project and refining it to work with the Wikibase model. As we bring this functionality into play, core Python processing logic for public data sources is being built into the isaid.py file that we'll eventually package up as a deployable.

## Python Package
We are iteratively working to build our abstracted functionality in a deployable Python package based on the pywikibot package that impose the rules and conventions we are evolving for the GeoKB. Both that package and the notebooks may prove useful for other communinities. That package is being built by a contract group engaged in this work and will be spun up in a separate deployable repo soonish. In the near term, we have a class in the wbmaker.py file that is evolving to handle connection details and general functionality.

## Other Tools
Other routes we are exploring will take advantage of the longstanding QuickStatements tool and related methods to produce QuickStatements encoding through OpenRefine. We are also exploring the use of GIS software where part of the work includes viewing a batch of items in a GIS (via point coordinate location with a property using the globe-coordinate datatype) and doing work on either the geospatial piece or associated property data. These will get fed back into the system via some type of bot action that will incorporate edits, including new items. The GIS part of this will take some additional work as we need to also deal with items in the GeoKB with more complex geometry, likely using a different approach than the Wikidata/Wikimedia Commons connection with the GeoShape datatype.

What we've discovered so far is that the knowledge graph needs to get to a particular tipping point where there is enough reference material built into the knowledge representation that many other users can contribute by building links to those items. Each body of concepts that will form objects linked through predicates to subject items being introduced needs to be thought through to a the point where they can be instantiated effectively. We still need to develop an effective operational model for working through these dynamics.

## Dependencies
See the environment.yml for a baseline Conda environment if you choose to go that route. My environment is built on a Python 3.11 base with Mamba (lighter weight Conda Forge-backed manager). You can build it however you want, though, and other versions of the basic dependencies should work.

In some cases, I am running code on cloud-based Jupyter server environments where I need either more processing power or access to specialized data. These include the Microsoft Planetary Computer Hub (Pangeo environment) where I've accessed some of their public datasets like U.S. Census sources and the ESIPLab's Nebari environment where I'm experimenting with processing methods of use to ESIP projects. We also have an internal Pangeo environment for the USGS, but because we are only dealing with public data sources here, there has been no need to work with that internal platform.

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

