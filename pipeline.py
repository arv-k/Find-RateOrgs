http_client = httpx.Client(verify=False)
# --- Configuration ---
# It's best to set this as an environment variable
OPENAI_API_KEY = "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" 
# BING_SEARCH_API_KEY = "your-bing-api-key-here" # Optional, for more robust search

client = OpenAI(api_key=OPENAI_API_KEY, http_client=http_client)

# --- Step 1: Scrape CampusLabs (Mock Implementation) ---
# Replace this with your actual requests/BeautifulSoup implementation
def scrape_campus_labs():
    """
    Scrapes MSU's student org portal (Involve at State) using its public API.
    This is a live scraper, not a mock function.
    """
    print("⚙️ Starting live scrape of MSU student orgs...")
    
    # This is the API endpoint the website uses to load organizations
    api_url = "https://msu.campuslabs.com/engage/api/discovery/search/organizations"
    
    all_orgs = []
    page_size = 100 # Request 100 orgs per API call
    skip = 0
    
    while True:
        # Parameters for the API request: get 100 orgs, then skip for the next page
        params = {
            "orderBy[0]": "UpperName asc",
            "top": page_size,
            "filter": "",
            "query": "",
            "skip": skip
        }
        
        try:
            response = requests.get(api_url, params=params, verify=False)
            response.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)
            data = response.json()
            
            page_orgs = data.get('value', [])
            
            if not page_orgs:
                # No more organizations found, break the loop
                break
            
            for org in page_orgs:
                all_orgs.append({
                    "name": org.get("Name"),
                    "categories": org.get("CategoryNames", []),
                    "description": org.get("Summary", "No description provided."), # Use 'Summary' for description
                    "website_key": org.get("WebsiteKey")
                })
            
            # Prepare for the next page
            skip += page_size
            print(f"  -> Fetched {len(all_orgs)} orgs so far...")
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Error during API request: {e}")
            break # Exit on error
            
    print(f"✅ Scrape complete. Found {len(all_orgs)} total organizations.")
    return all_orgs
    mock_org_data = [
        {
            "name": "MSU Innovation Club",
            "categories": ["Academic", "Technology"],
            "description": "A club for student innovators and entrepreneurs. We host weekly workshops and an annual pitch competition.",
            "website_key": "msuinnovation"
        },
        {
            "name": "Spartan Ski Club",
            "categories": ["Sports", "Recreation"],
            "description": "Michigan State's largest student org! We organize ski trips across the country. Check our Insta for trip sign-ups.",
            "website_key": "spartanski"
        },
        {
            "name": "MSU Accounting Society",
            "categories": ["Professional", "Business"],
            "description": "Connecting students with accounting firms. We host networking nights and info sessions. RSVP for our Fall Gala!",
            "website_key": "msuaccounting"
        },
    ]
    print(f"Found {len(mock_org_data)} orgs.")
    return mock_org_data


# --- Step 2: Find Instagram Profile URL ---
def find_instagram_url(org_name, school="Michigan State"):
    """
    Uses Selenium to perform a Google search in a real browser,
    making it much harder to block.
    """
    print(f"  -> Searching for '{org_name}' via Selenium...")
    query = f'site:instagram.com "{org_name}" "{school}"'
    search_url = f"https://www.google.com/search?q={quote_plus(query)}"
    
    # Setup headless Chrome browser
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")  # Runs Chrome in the background
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36")
    
    driver = None
    try:
        # Initialize the Chrome driver automatically
        driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=options)
        driver.get(search_url)
        
        # Let the page load and handle potential consent pop-ups
        time.sleep(2) 
        
        # Get the page source and parse with BeautifulSoup
        soup = BeautifulSoup(driver.page_source, 'html.parser')

        # The parsing logic remains the same
        for link in soup.find_all('a'):
            href = link.get('href')
            # Look for a clean Instagram URL
            if href and href.startswith("https://www.instagram.com/"):
                if "/p/" not in href and "/reel/" not in href:
                    return href
    except Exception as e:
        print(f"  -> Selenium search failed for {org_name}. Error: {e}")
        return None
    finally:
        # Ensure the browser is closed to free up resources
        if driver:
            driver.quit()
            
    return None

# --- Step 3: Scrape Instagram Profile ---
def scrape_instagram_data(profile_url):
    """
    Scrapes public data from an Instagram profile page without an API.
    It does this by finding the JSON data embedded in the page's HTML.
    """
    if not profile_url:
        return None
        
    print(f"Scraping Instagram data from {profile_url}...")
    headers = {"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 12_3_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/12.1.1 Mobile/15E148 Safari/604.1"}
    
    try:
        response = requests.get(profile_url, headers=headers)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        # Find the script tag containing the profile data
        json_script = soup.find('script', string=re.compile('window._sharedData'))
        
        if not json_script: # Fallback for different Instagram HTML structures
            json_script = soup.find('script', type='application/ld+json')
            if json_script:
                data = json.loads(json_script.string)
                bio = data.get("description")
                followers = data.get("mainEntityofPage", {}).get("interactionStatistic", {}).get("userInteractionCount")
                return {"bio": bio, "followers": followers, "captions": []} # Captions aren't in this JSON-LD
            return None # Could not find data

        # For the classic _sharedData structure
        json_text = json_script.string.replace('window._sharedData = ', '').rstrip(';')
        data = json.loads(json_text)
        
        user_data = data['entry_data']['ProfilePage'][0]['graphql']['user']
        
        bio = user_data.get('biography')
        external_url = user_data.get('external_url')
        followers = user_data['edge_followed_by']['count']
        
        # Get recent post captions
        posts = user_data['edge_owner_to_timeline_media']['edges']
        captions = [post['node']['edge_media_to_caption']['edges'][0]['node']['text'] 
                    for post in posts if post['node']['edge_media_to_caption']['edges']]
        
        return {
            "bio": bio,
            "external_url": external_url,
            "followers": followers,
            "captions": captions[:5] # Get latest 5 captions
        }
        
    except (requests.exceptions.RequestException, KeyError, IndexError, TypeError) as e:
        print(f"  -> Failed to scrape {profile_url}. Error: {e}")
        return None

# In pipeline.py

def get_gpt_scores(orgs_with_insta_data):
    """
    Sends enriched organization data to GPT for scoring using batch processing
    and prints high-scoring results as it goes.
    """
    print("Sending data to GPT in batches to manage rate limits...")
    
    all_scored_orgs = []
    chunk_size = 25
    org_chunks = [orgs_with_insta_data[i:i + chunk_size] for i in range(0, len(orgs_with_insta_data), chunk_size)]
    
    for i, chunk in enumerate(org_chunks):
        print(f"--> Processing batch {i+1}/{len(org_chunks)}...")
        
        # This part is unchanged
        orgs_formatted_list = []
        for org in chunk:
            # ... (code to format the orgs blob is unchanged)
            insta_info = org.get("instagram_data")
            if insta_info:
                insta_str = f"""
Instagram Bio: {insta_info.get('bio', 'N/A')}
Followers: {insta_info.get('followers', 'N/A')}
External Link: {insta_info.get('external_url', 'N/A')}
Recent Post Captions:
1. {insta_info.get('captions', ['N/A'])[0] if len(insta_info.get('captions', [])) > 0 else 'N/A'}
2. {insta_info.get('captions', ['N/A','N/A'])[1] if len(insta_info.get('captions', [])) > 1 else 'N/A'}
"""
            else:
                insta_str = "Instagram data not available."

            org_blob = f"""
Org:
Name: {org['name']}
CampusLabs Description: {org['description']}
{insta_str}
"""
            orgs_formatted_list.append(org_blob)

        system_prompt = """
You are an expert analyst helping a startup called Doorlist. Your task is to evaluate student organizations.
For each organization, provide a score from 0 to 10 indicating how likely they are to benefit from Doorlist (an RSVP/ticketing tool).
- Score 8-10: Prime targets. Explicitly mention ticketed events, sign-ups, galas, or use external ticketing links.
- Score 4-7: Potential targets. Mention events, meetings, or workshops but without clear ticketing/RSVP language.
- Score 0-3: Low-priority. Little to no evidence of hosting events that would require management.

You MUST reply with a single JSON object. That object must contain one key, and the value for that key must be a JSON array of objects. Each object in the array must have three keys: "club_name", "score", and "reason".
"""
        user_prompt = "Here is a batch of organizations. Please evaluate them:\n\n" + "\n---\n".join(orgs_formatted_list)
        
        try:
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
            )
            results_json = json.loads(response.choices[0].message.content)
            
            for key, value in results_json.items():
                if isinstance(value, list):
                    print(f"  -> Successfully received and parsed {len(value)} scores for this batch.")
                    all_scored_orgs.extend(value)
                    
                    # --- NEW: PRINT HIGH-SCORING RESULTS FOR THIS BATCH ---
                    print("  -> Checking for high scores in this batch...")
                    found_high_score = False
                    for result in value:
                        score = result.get('score', 0)
                        if score >= 7:
                            print(f"    ✅ High Score Find! | Score: {score}/10 | {result.get('club_name')} | Reason: {result.get('reason')}")
                            found_high_score = True
                    if not found_high_score:
                        print("    -- No high-scoring clubs in this batch.")
                    # --- END OF NEW CODE ---
                    
                    break
            
            time.sleep(2) 

        except Exception as e:
            print(f"  -> Error processing batch {i+1}: {e}")
            continue

    return all_scored_orgs

def process_single_org(org):
    """
    Worker function to find and scrape Instagram data for a single organization.
    This is designed to be run in parallel.
    """
    print(f"  -> Processing {org['name']}...")
    insta_url = find_instagram_url(org['name'])
    if insta_url:
        org['instagram_url'] = insta_url
        org['instagram_data'] = scrape_instagram_data(insta_url)
    else:
        org['instagram_url'] = None
        org['instagram_data'] = None
    return org

# --- Main Execution Logic ---
def run_pipeline():
    """Main function to run the entire pipeline with parallel processing."""
    # 1. Scrape CampusLabs
    orgs = scrape_campus_labs()
    if not orgs:
        print("No organizations found. Exiting.")
        return pd.DataFrame()

    # 2 & 3. Find and Scrape Instagram in PARALLEL
    enriched_orgs = []
    print("🔎 Starting parallel search for Instagram profiles...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        results_iterator = executor.map(process_single_org, orgs)
        enriched_orgs = list(results_iterator)
    print("✅ Parallel search complete.")

    # --- NEW: CALCULATE AND PRINT THE INSTAGRAM FIND RATE ---
    found_count = sum(1 for org in enriched_orgs if org.get('instagram_url'))
    total_count = len(enriched_orgs)
    find_rate = (found_count / total_count * 100) if total_count > 0 else 0
    print("\n--- Search Summary ---")
    print(f"📊 Found Instagram profiles for {found_count} out of {total_count} organizations ({find_rate:.2f}% find rate).")
    print("----------------------\n")
    # --- END OF NEW CODE ---

    # 4. Score with GPT
    scored_orgs = get_gpt_scores(enriched_orgs)

    if not scored_orgs:
        print("Could not get scores from GPT. Exiting.")
        return pd.DataFrame()

    # 5. Combine and Format Results
    orgs_df = pd.DataFrame(enriched_orgs)
    scores_df = pd.DataFrame(scored_orgs)

    final_df = pd.merge(orgs_df, scores_df, left_on='name', right_on='club_name', how='left')
    final_df = final_df.sort_values(by='score', ascending=False)

    print("\n--- Pipeline Complete ---")
    return final_df[['name', 'score', 'reason', 'description', 'instagram_url']]
