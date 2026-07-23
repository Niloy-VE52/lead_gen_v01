from apify_client import ApifyClient
from dotenv import load_dotenv
load_dotenv()  # Load environment variables from .env file
import os

apify_token = os.getenv("APIFY_KEY")
# Initialize the ApifyClient with your API token
client = ApifyClient(apify_token)


def get_email_from_linkedin_profile(profile_url):
    # Prepare the Actor input
    run_input = { "urls": [profile_url] }

    # Run the Actor and wait for it to finish
    run = client.actor("bfH8Ermocz8oYKQVO").call(run_input=run_input)

    # Fetch and return Actor results from the run's dataset (if there are any)
    results = []
    for item in client.dataset(run["defaultDatasetId"]).iterate_items():
        results.append(item)
    
    return results

def get_decisionmakers_linkedin(company_url):
    # Prepare the Actor input
    run_input = {
        "companies": [
            company_url
        ],
        "jobTitles": [
            "CEO",
            "President",
            "Founder",
            "Vice President",
            "Co-Founder",
            "Director of Talent Acquisition",
            "CRO",
            "Chief Revenue Officer",
            "Director of operations",
            "Managing Director",
            "Chief People officer",
            "COO",
            "Chief Operating Officer",
            "HR head",
            "Head of Business Operations",
            
        ],
        "maxItems": 10,
        "profileScraperMode": "Short ($4 per 1k)",
        "recentlyChangedJobs": False,
        "seniorityLevelIds": [
            "310",
            "300",
            "220",
            "320",
            "210"
        ]
    }

    # Run the Actor and wait for it to finish
    # run = client.actor('george.the.developer/linkedin-company-employees-scraper').call(run_input=run_input)
    run = client.actor("Vb6LZkh4EqRlR0Ka9").call(run_input=run_input)

    # Fetch and return Actor results from the run's dataset (if there are any)
    results = []
    for item in client.dataset(run["defaultDatasetId"]).iterate_items():
        results.append(item)
    
    return results


# company_url = "https://www.linkedin.com/company/ecm-holding-group"  # Replace with the actual company URL

# results = get_decisionmakers_linkedin(company_url)
# print(results)
# for person in results:
#     profile = person

#     print("Name:", profile["firstName"], profile["lastName"])
#     print("LinkedIn:", profile["linkedinUrl"])
#     print("Title:", profile["currentPositions"][0]["title"])
#     print("Company:", profile["currentPositions"][0]["companyName"])
#     print("Location:", profile["location"]["linkedinText"])
#     print("-"*50)


# employee_url = "https://www.linkedin.com/in/ACwAAAMU2okBR6B4eEMOPW5H5IZf8Qsyss4CMFE"



#             #    "https://www.linkedin.com/in/ACwAAACav98B7pieUIUzDKgJUlkxKe4gHnRihYE",
#             #    "https://www.linkedin.com/in/ACwAABVVyF8BehWUwqF2tM9Bn-dCARF5mVzd6CU",
#             #    "https://www.linkedin.com/in/ACwAAAB3y8oBKWuV-9_ILSc568Mr9SOS17aB1oU",
#             #    "https://www.linkedin.com/in/ACwAAAACyR8Bt1pUjQSIiooxmgopF99G2XT4pZU",
#             #    "https://www.linkedin.com/in/ACwAAAqYesIBikcGF5_NfIq0JR5U546fdKmttfI",
#             #    "https://www.linkedin.com/in/ACwAAAMU2okBR6B4eEMOPW5H5IZf8Qsyss4CMFE"
               

# result = get_email_from_linkedin_profile(employee_url)
# print(result)

# for person in result:
#     profile = person

#     print("Name:", profile["name"])
#     print("Email:", profile.get("email", "N/A"))
#     print("Company:", profile.get("company", "N/A"))
#     print("-"*50)



