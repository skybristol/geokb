from datetime import datetime
import requests
from bs4 import BeautifulSoup
import unicodedata
import re
import yaml
from dictdiffer import diff
import wikibaseintegrator


def check_blocklist(url):
    api = f"https://geokb.wikibase.cloud/w/api.php"
    parameters = {
        'action': 'spamblacklist',
        'format': 'json',
        'url': url,
        'formatversion': 2
    }
    return requests.get(api, params=parameters).json()


class Person:
    def __init__(self, wb, logger, org_url_lookup, org_name_lookup, person_class_lookup):
        self.wb = wb
        self.logger = logger
        self.org_url_lookup = org_url_lookup
        self.org_name_lookup = org_name_lookup
        self.person_class_lookup = person_class_lookup

        self.rge_link_qid = 'Q159626'

    def staff_profile_scrape(self, profile):
        '''
        Web scraping routine for USGS staff profile pages

        return: dict
        '''
        if profile.startswith('http'):
            profile_url = profile
        else:
            profile_url = f"https://www.usgs.gov/staff-profiles/{profile}"

        self.logger.log(
            message={
                'url': profile_url,
                'action': 'staff_profile_scrape started',
            }
        )

        r = requests.get(profile_url)

        profile = {
            "meta": {
                "url": profile_url,
                "timestamp": datetime.now().isoformat(),
                "status_code": r.status_code
            }
        }

        if r.status_code == 200:
            self.logger.log(
                message={
                    'url': profile_url,
                    'action': 'scraping content',
                }
            )
            profile['profile'] = {
                "name": None,
                "name_qualifier": None,
                "titles": [],
                "organizations": [],
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
            if not first_h1:
                self.logger.log(
                    message={
                        'url': profile_url,
                        'action': 'improper HTML structure',
                    },
                    level='error'
                )
                return None
            else:
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

            for primary_org_container in soup.find_all('div', {'class': 'field-org-primary'}):
                for microsite_div in primary_org_container.find_all('div', {'class': 'field-microsite'}):
                    for org_link in microsite_div.find_all('a'):
                        profile['profile']["organizations"].append((org_link.text.strip(),f"https://www.usgs.gov{org_link['href']}"))

                for title_div in primary_org_container.find_all('div', {'class': 'field-title'}):
                    profile['profile']["titles"].append(unicodedata.normalize("NFKD", title_div.text.strip()))

            for additional_org_container in soup.find_all('div', {'class': 'field-org-additional'}):
                for microsite_div in additional_org_container.find_all('div', {'class': 'field-microsite'}):
                    for org_link in microsite_div.find_all('a'):
                        profile['profile']["organizations"].append((org_link.text.strip(),f"https://www.usgs.gov{org_link['href']}"))

                for title_div in additional_org_container.find_all('div', {'class': 'field-title'}):
                    profile['profile']["titles"].append(unicodedata.normalize("NFKD", title_div.text.strip()))

            email_div = soup.find('div', {'class': 'field-email'})
            if email_div:
                profile['profile']["email"] = email_div.text.strip()

            orcid_div = soup.find('div', {'class': 'field--name--field-staff-orcid'})
            if orcid_div:
                profile['profile']["orcid"] = orcid_div.text.strip()

            intro_div = soup.find('div', {'class': 'field-intro'})
            if intro_div:
                profile['profile']["intro_statements"] = [unicodedata.normalize("NFKD", i.text.strip()) for i in intro_div.find_all('p')]
                profile['profile']["intro_statements"] = [i for i in profile['profile']["intro_statements"] if len(i.strip()) > 0]

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
        else:
            self.logger.log(
                message={
                    'url': profile_url,
                    'status_code': r.status_code,
                    'action': 'failed to retrieve profile',
                },
                level='error'
            )

        return profile

    def _wb_dt(self, input_string):
        '''
        Convert a date string from a timestamp to a Wikibase datetime string

        return: str or None
        '''
        try:
            datetime_obj = datetime.strptime(input_string, '%Y-%m-%dT%H:%M:%S.%f')
        except Exception as e:
            return None

        datetime_obj = datetime_obj.replace(hour=0, minute=0, second=0, microsecond=0)
        return datetime_obj.strftime('%Y-%m-%dT%H:%M:%SZ')

    def latest_website_from_claim(self, item):
        '''
        Process the official website claim to get the most recent URL

        return: str or None
        '''
        official_website_claims = item.claims.get(self.wb.prop_lookup['official website'])
        if not official_website_claims:
            return None
        
        if len(official_website_claims) == 1:
            return official_website_claims[0].mainsnak.datavalue['value']

        websites = []
        for c in official_website_claims:
            url = c.mainsnak.datavalue['value']
            retrieved = c.qualifiers.get(self.wb.prop_lookup['retrieved'])
            if retrieved:
                retrieved = retrieved[0].datavalue['value']['time']
            else:
                retrieved = None
            websites.append((url, retrieved))
        websites = [i for i in websites if i[1] is not None]
        return max(websites, key=lambda x: x[1])[0]

    def get_item(self, qid):
        '''
        Retrieve an item object from the GeoKB
        '''
        try:
            return self.wb.wbi.item.get(qid)
        except:
            return None

    def build_timestamp_qualifiers(self, timestamp, prop_nr):
        '''
        Build a timestamp qualifier for a claim
        '''
        return self.wb.datatypes.Time(
            prop_nr=prop_nr,
            time=self._wb_dt(timestamp),
            precision=11
        )

    def build_reference_url(self, url):
        '''
        Build a reference URL reference for a claim
        '''
        return self.wb.datatypes.URL(
            prop_nr=self.wb.prop_lookup['reference URL'],
            value=url
        )

    def get_affiliation(self, org_url, org_name):
        '''
        Use the org link or org name to lookup the QID for an organization to link to as affiliation
        '''
        if org_url in self.org_url_lookup:
            return self.org_url_lookup[org_url]
        elif org_name in self.org_name_lookup:
            return self.org_name_lookup[org_name]
        else:
            return None
    
    def read_item_talk(self, qid, convert='yaml'):
        '''
        Retrieves the item talk page cache for a given QID
        Converts to a dictionary if convert is set to 'yaml'
        Converts to a list of strings if convert is set to 'list'
        '''
        item_talk_page = self.wb.mw_site.pages[f'Item_talk:{qid}']
        item_talk_page_text = item_talk_page.text()
        if convert == 'yaml':
            yaml_load = yaml.load(item_talk_page_text, Loader=yaml.FullLoader)
            return item_talk_page, yaml_load if yaml_load else {}
        elif convert == 'list':
            return item_talk_page, item_talk_page_text.split(',')
        else:
            return item_talk_page, item_talk_page_text
        
    def write_item_talk(self, content, item_talk_page=None, qid=None, summary="Updated item talk page content"):
        '''
        Writes content to an item talk page
        Converts a dictionary to YAML, converts a list to a comma-separated string
        '''
        if item_talk_page is None and qid is not None:
            item_talk_page = self.wb.mw_site.pages[f'Item_talk:{qid}']
        if item_talk_page is not None:
            if isinstance(content, dict):
                content = yaml.dump(content, default_flow_style=False, sort_keys=False)
            elif isinstance(content, list):
                content = ",".join(content)

            item_talk_page.save(content, summary=summary)

    def process_profile(self, qid):
        '''
        Run the full process for a given person entity containing a USGS staff profile as official website
        '''
        # Get the object from the GeoKB so we can operate on it
        item = self.get_item(qid)
        if not item:
            self.logger.log(
                message={
                    'qid': qid,
                    'action': 'could not retrieve item from GeoKB',
                },
                level='warning'
            )
            return self.logger.last_message()
        
        # Make sure the item has an instance of claim
        try:
            instance_of_claims = item.claims.get(self.wb.prop_lookup['instance of'])
        except:
            self.logger.log(
                message={
                    'qid': qid,
                    'action': 'no instance of claim on item',
                },
                level='warning'
            )
            return self.logger.last_message()
        
        # Make sure the item represents a human
        if not any([i.mainsnak.datavalue['value']['id'] == 'Q3' for i in instance_of_claims]):
            self.logger.log(
                message={
                    'qid': qid,
                    'action': 'item is not an instance of human',
                },
                level='warning'
            )
            return self.logger.last_message()

        # Get the profile URL from the official website claim
        profile_url = self.latest_website_from_claim(item)
        if not profile_url:
            self.logger.log(
                message={
                    'qid': qid,
                    'action': 'could not retrieve profile URL',
                },
                level='warning'
            )
            return self.logger.last_message()

        # Scrape the staff profile from the USGS website
        staff_profile = self.staff_profile_scrape(profile_url)
        if not staff_profile:
            self.logger.log(
                message={
                    'qid': qid,
                    'profile_url': profile_url,
                    'action': 'could not retrieve staff profile',
                },
                level='warning'
            )
            return self.logger.last_message()
        
        if "profile" not in staff_profile:
            self.logger.log(
                message={
                    'qid': qid,
                    'profile_url': profile_url,
                    'action': 'problem in profile scrape',
                },
                level='warning'
            )
            return self.logger.last_message()
        
        # Process label, description, and aliases
        english_label = item.labels.get('en').value
        english_description = item.descriptions.get('en')
        if english_description:
            english_description = english_description.value
        english_aliases = item.aliases.get('en') if item.aliases.get('en') else []
        if english_aliases:
            english_aliases = [a.value for a in english_aliases]

        # Check the alignment of the label to name and set label and aliases as needed
        if english_label != staff_profile['profile']['name']:
            item.labels.set('en', staff_profile['profile']['name'])
            self.logger.log(
                message={
                    'qid': qid,
                    'profile_url': profile_url,
                    'label': staff_profile['profile']['name'],
                    'action': 'updated entity label',
                }
            )
            if english_label not in english_aliases:
                english_aliases.append(english_label)
                item.aliases.set('en', english_aliases)
                self.logger.log(
                    message={
                        'qid': qid,
                        'profile_url': profile_url,
                        'aliases': english_aliases,
                        'action': 'updated entity aliases',
                    }
                )

        # Set description to the first title scraped from the staff profile
        if not staff_profile['profile']['titles']:
            person_title = 'USGS staff person'
        else:
            person_title = staff_profile['profile']['titles'][0]
        if english_description != person_title:
            item.descriptions.set('en', person_title)
            self.logger.log(
                message={
                    'qid': qid,
                    'profile_url': profile_url,
                    'description': person_title,
                    'action': 'updated entity description',
                }
            )
        
        # Build qualifiers and references for claims coming from the staff profile
        profile_timestamp_qualifier = self.wb.datatypes.Time(
            prop_nr=self.wb.prop_lookup['point in time'],
            time=self._wb_dt(staff_profile['meta']['timestamp']),
            precision=11
        )
        profile_reference_url_qualifier = self.wb.datatypes.URL(
            prop_nr=self.wb.prop_lookup['reference URL'],
            value=profile_url
        )

        # Update the official website claim with timestamp and status code
        profile_url_claim_qualifiers = []
        profile_url_claim_qualifiers.append(
            self.wb.datatypes.Time(
                prop_nr=self.wb.prop_lookup['retrieved'],
                time=self._wb_dt(staff_profile['meta']['timestamp']),
                precision=11
            )
        )
        profile_url_claim_qualifiers.append(
            self.wb.datatypes.String(
                prop_nr=self.wb.prop_lookup['status code'],
                value=str(staff_profile['meta']['status_code'])
            )
        )
        new_website_claims = [
            self.wb.datatypes.URL(
                prop_nr=self.wb.prop_lookup['official website'],
                value=profile_url,
                qualifiers=profile_url_claim_qualifiers
            )
        ]

        # Add any previous employers as they are
        try:
            for claim in item.claims.get(self.wb.prop_lookup['official website']):
                if claim.mainsnak.datavalue['value'] != profile_url:
                    new_website_claims.append(claim)
        except:
            pass

        # Add the full set of website claims as a replacement for the current set
        item.claims.add(new_website_claims, action_if_exists=self.wb.action_if_exists.REPLACE_ALL)

        affiliation_qids = []
        for org_name, org_link in staff_profile['profile']['organizations']:
            affiliation_qids.append(self.get_affiliation(org_name=org_name, org_url=org_link))
            affiliation_qids = [i for i in affiliation_qids if i is not None]

        if affiliation_qids:
            new_affiliation_claims = []
            for affiliation_qid in affiliation_qids:
                new_affiliation_claims.append(
                    self.wb.datatypes.Item(
                        prop_nr=self.wb.prop_lookup['is affiliated with'],
                        value=affiliation_qid,
                        qualifiers=[profile_timestamp_qualifier],
                        references=[profile_reference_url_qualifier]
                    )
                )

            # Add any previous affiliations as they are
            try:
                for claim in item.claims.get(self.wb.prop_lookup['is affiliated with']):
                    if claim.mainsnak.datavalue['value']['id'] not in affiliation_qids:
                        new_affiliation_claims.append(claim)
            except:
                pass

            # Add the full set of affiliation claims as a replacement for the current set
            item.claims.add(new_affiliation_claims, action_if_exists=self.wb.action_if_exists.REPLACE_ALL)

        # If there is still an affiliation for a person in their staff profile
        # We assume they are still employed by the USGS
        # This claim needs further thought
        if affiliation_qids:
            new_employer_claims = [
                self.wb.datatypes.Item(
                    prop_nr=self.wb.prop_lookup['employer'],
                    value='Q44210',
                    qualifiers=[profile_timestamp_qualifier],
                    references=[profile_reference_url_qualifier]
                )
            ]

            # Add any previous employers as they are
            try:
                for claim in item.claims.get(self.wb.prop_lookup['employer']):
                    if claim.mainsnak.datavalue['value']['id'] != 'Q44210':
                        new_employer_claims.append(claim)
            except:
                pass

            # Add the full set of employer claims as a replacement for the current set
            item.claims.add(new_employer_claims, action_if_exists=self.wb.action_if_exists.REPLACE_ALL)

        # Process titles for occupation and manner of evaluation links
        current_occupation_qids = [self.person_class_lookup.get(title, None) for title in staff_profile['profile']['titles']]
        current_occupation_qids = [i for i in current_occupation_qids if i is not None]
        if current_occupation_qids:
            new_occupation_claims = []
            for occupation_qid in current_occupation_qids:
                new_occupation_claims.append(
                    self.wb.datatypes.Item(
                        prop_nr=self.wb.prop_lookup['occupation'],
                        value=occupation_qid,
                        qualifiers=[profile_timestamp_qualifier],
                        references=[profile_reference_url_qualifier]
                    )
                )

            # Add any previous affiliations as they are
            try:
                for claim in item.claims.get(self.wb.prop_lookup['employer']):
                    if claim.mainsnak.datavalue['value']['id'] not in current_occupation_qids:
                        new_occupation_claims.append(claim)
            except:
                pass

            # Add the full set of occupation claims as a replacement for the current set
            item.claims.add(new_occupation_claims, action_if_exists=self.wb.action_if_exists.REPLACE_ALL)

        # Check if the current title asserts that the person should be classified as "research"
        if staff_profile['profile']['titles'][0].startswith("Research "):
            item.claims.add(
                self.wb.datatypes.Item(
                    prop_nr=self.wb.prop_lookup['manner of evaluation'],
                    value=self.rge_link_qid,
                    qualifiers=[profile_timestamp_qualifier],
                    references=[profile_reference_url_qualifier]
                ),
                action_if_exists=self.wb.action_if_exists.REPLACE_ALL
            )

        if staff_profile['profile']['email']:
            new_email_claims = [
                self.wb.datatypes.URL(
                    prop_nr=self.wb.prop_lookup['email address'],
                    value=f"mailto:{staff_profile['profile']['email']}",
                    qualifiers=[profile_timestamp_qualifier],
                    references=[profile_reference_url_qualifier]
                )
            ]

            # Add any previous emails as they are
            try:
                for claim in item.claims.get(self.wb.prop_lookup['email address']):
                    if claim.mainsnak.datavalue['value'] != f"mailto:{staff_profile['profile']['email']}":
                        new_email_claims.append(claim)
            except:
                pass

            # Add the full set of employer claims as a replacement for the current set
            item.claims.add(new_email_claims, action_if_exists=self.wb.action_if_exists.REPLACE_ALL)

        if staff_profile['profile']['orcid']:
            new_orcid_claims = [
                self.wb.datatypes.ExternalID(
                    prop_nr=self.wb.prop_lookup['ORCID iD'],
                    value=staff_profile['profile']['orcid'],
                    qualifiers=[profile_timestamp_qualifier],
                    references=[profile_reference_url_qualifier]
                )
            ]

            # Add any previous ORCIDs as they are
            try:
                for claim in item.claims.get(self.wb.prop_lookup['ORCID iD']):
                    if claim.mainsnak.datavalue['value'] != staff_profile['profile']['orcid']:
                        new_orcid_claims.append(claim)
            except:
                pass

            # Add the full set of employer claims as a replacement for the current set
            item.claims.add(new_orcid_claims, action_if_exists=self.wb.action_if_exists.REPLACE_ALL)

        # Retrieve and process the source data cache from the item talk page
        item_talk_page, item_talk_page_data = self.read_item_talk(qid)

        if 'usgs_staff_profile' not in item_talk_page_data:
            item_talk_page_data['usgs_staff_profile'] = staff_profile
            self.write_item_talk(item_talk_page_data, item_talk_page=item_talk_page)
            self.logger.log(
                message={
                    'qid': qid,
                    'profile_url': profile_url,
                    'action': 'cached staff profile for first time',
                }
            )

        else:
            # Compare the new staff profile data with the cached data
            # We only need to write the new staff profile if there are changes (beyond the timestamp)
            differences = list(diff(staff_profile, item_talk_page_data['usgs_staff_profile']))

            if len(differences) > 1:
                # If there is more than just a timestamp change, update the cache
                item_talk_page_data['usgs_staff_profile'] = staff_profile
                self.write_item_talk(item_talk_page_data, item_talk_page=item_talk_page)
                self.logger.log(
                    message={
                        'qid': qid,
                        'profile_url': profile_url,
                        'action': 'updated cached staff profile',
                    }
                )

        # Write the item with changes
        try:
            response = item.write(summary="Updated person item from staff profile source information")
            self.logger.log(
                message={
                    'qid': response.id,
                    'profile_url': profile_url,
                    'action': 'updated item',
                }
            )
        except Exception as e:
            self.logger.log(
                message={
                    'qid': response.id,
                    'profile_url': profile_url,
                    'action': 'problem writing item to the GeoKB',
                },
                level='error'
            )
        
        return self.logger.last_message()
