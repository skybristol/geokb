# geokb
Data processing workflows for initializing and building the Geoscience Knowledgebase

## Dependencies

See the environment.yml for a complete environment if you choose to go that route. Primary dependencies here include something that will run Python Notebooks plus the following. Earlier versions of Python should be fine to a certain extent.

* required installs:
    - `pip install -U setuptools`
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