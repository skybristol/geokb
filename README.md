# GeoKB Notebook-based Bots
The Geoscience Knowledgebase (GeoKB) is a framework for assembling, organizing, growing, and reasoning (AI) knowledge about the earth system. We are building it on the Wikibase infrastructure to take advantage of tools and techniques already in use across many other domains. Much of the content that flows into the GeoKB comes from existing sources, both static and dynamic. We use bots as one method to build entities and claims, some of which make best sense as computational notebooks. This repository is dedicated to those notebook bots that are foudnational to initializing an GeoKB instance or that are otherwise part of the core development effort.

Over time, we will likely develop the following types of bots:
* Bots designed to process specific source data and information into the GeoKB (e.g., bring in scientific reference material like journal articles and government reports)
* Bots designed to handle the inner workings of the GeoKB from the initialization of properties and classifiers to the introduction of claims that arise from other things showing up in the knowledgebase
* Bots that handle the regularized production of different kinds of output transformations from the GeoKB such as generating geospatial databases and spinning up online GIS services

## The Notebooks

* Initialize GeoKB - works through the process of initializing a new knowledgebase (and occasionally updating) with the foundational properties and top-level classification items that will form the "instance of" classification of core items in the knowledgebase
* GeoArchive (Zotero) - explores how we map documents stored in the Zotero part of our GeoArchive work to GeoKB items and claims
* SEC Companies/Filings - explores using the SEC EDGAR API to identify companies involved in mining and mineral exploration and relevant filings we need to identify and process for claims about mineral exploration history

## Other Methods
Bots, whether built in notebook form or some other packaging, are one method of handling more routine or regular input to the GeoKB. We'll use these for cases where we need to process an entire source over and over again to incorporate new records and updates or to reprocess information into a new knowledge encoding.

Other routes we are exploring will take advantage of the longstanding QuickStatements tool and related methods to produce QuickStatements encoding through OpenRefine. We are also exploring the use of GIS software where part of the work includes viewing a batch of items in a GIS (via point coordinate location with a property using the globe-coordinate datatype) and doing work on either the geospatial piece or associated property data. These will get fed back into the system via some type of bot action that will incorporate edits, including new items. The GIS part of this will take some additional work as we need to also deal with items in the GeoKB with more complex geometry, likely using a different approach than the Wikidata/Wikimedia Commons connection with the GeoShape datatype.

## Python Package
We are iteratively working to build our abstracted functionality in a deployable Python package based on the pywikibot package that impose the rules and conventions we are evolving for the GeoKB. Both that package and the notebooks may prove useful for other communinities. That package is being built by a contract group engaged in this work and will be spun up in a separate deployable repo soonish.

## Dependencies
See the environment.yml for a complete Conda environment if you choose to go that route. Primary dependencies here include something that will run Python Notebooks plus the following. Earlier versions of Python should be fine to a certain extent.

* Primary packages
    - `pip install pywikibot`
    - `pip install wikitextparser`

## Pywikibot
The interactions from the notebooks in this project use the pywikibot package for interfacing with a Wikibase instance where we are establishing our GeoKB. All edit/write interfaces with Wikibase use bot accounts that are tied to a real user account. The following steps will set all of this up and support notebook-based interactions with the GeoKB.

### Setup Bot Account(s)
* Go to the Wikibase instance (local or deployed) and navigate to "Special pages" (/Special:SpecialPages)
* Under Users and rights select "Bot passwords"
* Log in with your credentials set up for the Wikibase instance
* You'll see a list of any existing bot names. You can navigate to one to reset a password as needed. Otherewise, use "Create a new bot password" and give your bot a reasonable name for what it will be doing.

Note: Need to come back to add some more details on this.

### Setup custom Wikibase family
With pywikibot, you need to create a "family" for the custom Wikibase instance where you will be setting up the GeoKB. By default, pywikibot only knows about all of the Wikimedia Commons components (Wikipedia, Wikidata, etc.) and their test and production environments. We need to set up a config for our own instance(s).

1. Create `<family-filename>` family using command `pwb generate_family_file`
2. Please insert URL to wiki: `<url to wikibase instance, localhost or deployed>` 
3. Please insert a short name (eg: freeciv): `<some logical short name like geokb>`

This will create a "families" in your project with a necessary config Python file that can be modified with additional core functions (more on that later).

### Generate user files
Now, we need to set up how pywikibot will authenticate to the custom "family" (our Wikibase instance).

1. Ensuring that you are in the same directory with the "families" folder generated in the previous step, create user config and password files with command `pwb generate_user_files`
2. You will see a list of wiki families starting with "commons." Your custom family name generated in the previous step should be near the top. Put in the number for the custom family.
3. Depending on how you setup multi language support, you may need to respond differently to the language site code - default is en.
4. Specify your personal user name on the wikibase instance under which you created the bot password.
5. Don't worry about adding any other projects unless you have something else going on.
6. 'Do you want to add a BotPassword for `<user name>`?' `y`
7. 'BotPassword's "bot name" for `<user name>`:' `<what you used when you set up the bot account>`
8. 'BotPassword's "password" for "init-bot" (no characters will be shown):' `<copy and paste the password provided in the Wikibase GUI when you created the bot password>`
9. Take the defaults (None) for the last two questions
10. Change user-config file to read only by running `chmod 0444 user-config.py`
11. Test the connection by running `pwb login`. You may see a couple of warnings related to deprecated methods, but you will see a "Logged in on `<family name>`:en as `<user name>`" message at the end if successful.

# Disclaimer

This software is preliminary or provisional and is subject to revision. It is being provided to meet the need for timely best science. The software has not received final approval by the U.S. Geological Survey (USGS). No warranty, expressed or implied, is made by the USGS or the U.S. Government as to the functionality of the software and related material nor shall the fact of release constitute any such warranty. The software is provided on the condition that neither the USGS nor the U.S. Government shall be held liable for any damages resulting from the authorized or unauthorized use of the software.

