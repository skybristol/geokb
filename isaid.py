import os
import mwclient
from datetime import datetime
import requests
from bs4 import BeautifulSoup
import unicodedata
import re
import yaml


def staff_profile_scrape(profile_url):
    r = requests.get(profile_url)

    profile = {
        "meta": {
            "url": profile_url,
            "timestamp": datetime.now().isoformat(),
            "status_code": r.status_code
        }
    }

    if r.status_code == 200:
        profile['profile'] = {
            "name": None,
            "name_qualifier": None,
            "title": None,
            "organization_name": None,
            "organization_link": None,
            "email": None,
            "orcid": None,
            "intro_statements": [],
            "expertise_terms": [],
            "professional_experience": [],
            "education": [],
            "affiliations": [],
            "honors": [],
            "abstracts": [],
            "personal_statement": None
        }

        soup = BeautifulSoup(r.content, 'html.parser')

        first_h1 = soup.find('h1')
        if first_h1:
            name_text = unicodedata.normalize("NFKD", first_h1.text.strip())
            if name_text.endswith(")"):
                name_qual = re.search(r'\((.*?)\)', name_text)
                if name_qual:
                    profile['profile']["name_qualifier"] = name_qual.group(1)
                    profile['profile']["name"] = name_text.split("(")[0].strip()
                else:
                    profile['profile']["name"] = name_text
            else:
                profile['profile']["name"] = name_text

        org_div = soup.find('div', {'class': 'field-org-primary'})
        if org_div:
            microsite_div = org_div.find('div', {'class': 'field-microsite'})
            if microsite_div:
                org_link = microsite_div.find('a')
                if org_link:
                    profile['profile']["organization_name"] = org_link.text.strip()
                    profile['profile']["organization_link"] = f"https://www.usgs.gov{org_link['href']}"

            title_div = org_div.find('div', {'class': 'field-title'})
            if title_div:
                profile['profile']["title"] = unicodedata.normalize("NFKD", title_div.text.strip())

        email_div = soup.find('div', {'class': 'field-email'})
        if email_div:
            profile['profile']["email"] = email_div.text.strip()

        orcid_div = soup.find('div', {'class': 'field--name--field-staff-orcid'})
        if orcid_div:
            profile['profile']["orcid"] = orcid_div.text.strip()

        intro_div = soup.find('div', {'class': 'field-intro'})
        if intro_div:
            profile['profile']["intro_statements"] = [unicodedata.normalize("NFKD", i.text.strip()) for i in intro_div.find_all('p')]

        expertise_sections = soup.find_all('div', {'class': 'field-staff-expertise'})
        if expertise_sections:
            profile['profile']['expertise_terms'] = [unicodedata.normalize("NFKD", i.text.strip()) for i in expertise_sections]

        bulleted_sections = {
            "professional_experience": "field-professional-experience",
            "education": "field-education",
            "affiliations": "field-affiliations",
            "honors": "field-honors",
            "abstracts": "field-abstracts"
        }

        for k,v in bulleted_sections.items():
            items = soup.find_all('li', {'class': v})
            if items:
                item_contents = [unicodedata.normalize("NFKD", i.text.strip()) for i in items]
                for line in item_contents:
                    profile['profile'][k].extend(line.split('\n'))

        body_div = soup.find('div', {'class': 'body'})
        if body_div:
            profile['profile']["personal_statement"] = body_div.get_text(strip=True).replace(u'\xa0', u' ')

    return profile


def create_authenticated_site():
    user_name = os.environ['bot_username']
    password = os.environ['bot_password']

    site = mwclient.Site('geokb.wikibase.cloud', path='/w/', scheme='https')
    site.login(user_name, password)

    return site


def scrape_and_write_profile(profile, site):
    profile_cache_page = f"Item_talk:{profile[0]}"
    profile_url = profile[1]
    
    profile_data = staff_profile_scrape(profile_url)
    
    person_info = {
        "usgs_staff_profile": profile_data
    }
    
    yaml_data = yaml.dump(person_info)

    try:
        page = site.pages[profile_cache_page]
        page.save(yaml_data, summary=f'Added profile data from {profile_url}')
    except Exception as e:
        return e
