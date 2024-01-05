import os
import mwclient
from datetime import datetime
import requests
from bs4 import BeautifulSoup
import unicodedata
import re
import yaml
from urllib.parse import urlparse, parse_qs, unquote

# We need to get the range of pages to scrape
def last_page(profile_inventory_url):
    r_profile_inventory = requests.get(profile_inventory_url)
    soup_profile_inventory = BeautifulSoup(r_profile_inventory.content, 'html.parser')
    last_page_link = soup_profile_inventory.find('a', {'title': 'Go to last page'})['href']
    if not last_page_link:
        return

    last_page_url = "".join([profile_inventory_url, last_page_link])
    parsed_url = urlparse(last_page_url)
    query_params = parse_qs(parsed_url.query)
    last_page_num = query_params.get("page")
    if last_page_num:
        return int(last_page_num[0])

# Scrape an inventory page of up to 12 entries and return a list of dicts
def get_inventory_page(page_num):
    inventory_url = f'https://www.usgs.gov/connect/staff-profiles?node_staff_profile_type%5B141721%5D=141721&node_staff_profile_type%5B141730%5D=141730&node_staff_profile_type%5B141727%5D=141727&node_staff_profile_type%5B141728%5D=141728&node_staff_profile_type%5B141726%5D=141726&node_staff_profile_type%5B141722%5D=141722&node_staff_profile_type%5B141723%5D=141723&node_staff_profile_type%5B141719%5D=141719&node_staff_profile_type%5B141718%5D=141718&node_staff_profile_type%5B141759%5D=141759&node_staff_profile_type%5B141729%5D=141729&node_staff_profile_type%5B141717%5D=141717&node_staff_profile_type%5B141725%5D=141725&node_staff_profile_type%5B141745%5D=141745&node_staff_profile_type%5B141724%5D=141724&node_staff_profile_type%5B141720%5D=141720&node_staff_profile_type%5B141716%5D=141716&node_staff_profile_type_1=All&node_topics=All&items_per_page=12&node_states=&search_api_fulltext=&page={str(page_num)}'
    r = requests.get(inventory_url)
    if r.status_code != 200:
        return None

    soup = BeautifulSoup(r.text, 'html.parser')
    staff_profiles = soup.find_all('div', class_='grid-staff-profile')
    if not staff_profiles:
        return None

    staff = []
    for profile in staff_profiles:
        links = [(l.get('href').replace('/index.php', ''), l.text.strip()) for l in profile.find_all('a')]
        staff_profile_link = next((l for l in links if l[0].startswith('/staff-profiles/')), None)
        if not staff_profile_link:
            print(profile)
            continue
        person = {
            'date': datetime.now().isoformat(),
            'page_num': page_num,
            'name': staff_profile_link[1],
            'profile': staff_profile_link[0],
            'affiliations': []
        }
        email_link = next((l for l in links if l[0].startswith('mailto')), None)
        if email_link:
            person['email'] = email_link[0].split(':')[-1].strip()
        tel_link = next((l for l in links if l[0].startswith('tel')), None)
        if tel_link:
            person['telephone'] = unquote(tel_link[0].split(':')[-1].strip())
        person['affiliations'].extend([{'url': l[0], 'name': l[1]} for l in links if not l[0].startswith(('/staff-profiles/', 'mailto', 'tel'))])
        person['titles'] = [i.text.strip() for i in profile.find_all('div', class_='field-title')]
        staff.append(person)

    return staff

# Combine all lists returned in parallel processing into one with unique values
def inventory_list(inventories):
    inventory_records = []
    for i in inventories:
        inventory_records.extend(i)

    return inventory_records

def staff_profile_scrape(profile_url):
    if not profile_url.startswith('http'):
        profile_url = f"https://www.usgs.gov/staff-profiles/{profile_url}"
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
        page.save(yaml_data, summary=f'Added profile data from {profile_url}'.format(profile_url))
    except Exception as e:
        return e
