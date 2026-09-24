"""
Generate realistic pharma sales data at scale.

Outputs:
  schema/generated/organizations.csv
  schema/generated/products.csv
  schema/generated/sales.csv
  schema/generated/zip_territory.csv

Usage:
  python3 schema/generate_data.py
"""

import csv
import os
import random
from datetime import datetime, timedelta
from pathlib import Path

SEED = 42
random.seed(SEED)

ROOT = Path(__file__).parent.parent
OUT_DIR = ROOT / "schema" / "generated"

NUM_GRANDPARENTS = 500
NUM_PARENTS = 2_000
NUM_FACILITIES_WITH_PARENT = 27_500
NUM_STANDALONE_FACILITIES = 10_000
TOTAL_ORGS = NUM_GRANDPARENTS + NUM_PARENTS + NUM_FACILITIES_WITH_PARENT + NUM_STANDALONE_FACILITIES
NUM_SALES = 2_000_000
NUM_WEEKS = 156  # ~3 years of weekly data

# ---------------------------------------------------------------------------
# Reference data
# ---------------------------------------------------------------------------

REGIONS = [
    ("R01", "Northeast"),
    ("R02", "Mid-Atlantic"),
    ("R03", "Southeast"),
    ("R04", "Midwest"),
    ("R05", "South Central"),
    ("R06", "West"),
]

TERRITORIES = [
    ("T001", "New York Metro", "R01", "Northeast"),
    ("T002", "New England", "R01", "Northeast"),
    ("T003", "Mid-Atlantic East", "R02", "Mid-Atlantic"),
    ("T004", "Mid-Atlantic West", "R02", "Mid-Atlantic"),
    ("T005", "Southeast Atlantic", "R03", "Southeast"),
    ("T006", "Southeast Gulf", "R03", "Southeast"),
    ("T007", "Great Lakes East", "R04", "Midwest"),
    ("T008", "Great Lakes West", "R04", "Midwest"),
    ("T009", "Upper Midwest", "R04", "Midwest"),
    ("T010", "Texas", "R05", "South Central"),
    ("T011", "South Central", "R05", "South Central"),
    ("T012", "Pacific Northwest", "R06", "West"),
    ("T013", "California North", "R06", "West"),
    ("T014", "California South", "R06", "West"),
    ("T015", "Mountain", "R06", "West"),
]

STATES_BY_TERRITORY = {
    "T001": [("NY", "New York"), ("NJ", "New Jersey")],
    "T002": [("MA", "Massachusetts"), ("CT", "Connecticut"), ("RI", "Rhode Island"), ("NH", "New Hampshire")],
    "T003": [("PA", "Pennsylvania"), ("DE", "Delaware"), ("DC", "Washington DC")],
    "T004": [("MD", "Maryland"), ("VA", "Virginia"), ("WV", "West Virginia")],
    "T005": [("NC", "North Carolina"), ("SC", "South Carolina"), ("GA", "Georgia")],
    "T006": [("FL", "Florida"), ("AL", "Alabama"), ("MS", "Mississippi")],
    "T007": [("OH", "Ohio"), ("MI", "Michigan"), ("IN", "Indiana")],
    "T008": [("IL", "Illinois"), ("WI", "Wisconsin")],
    "T009": [("MN", "Minnesota"), ("IA", "Iowa"), ("ND", "North Dakota")],
    "T010": [("TX", "Texas")],
    "T011": [("LA", "Louisiana"), ("OK", "Oklahoma"), ("AR", "Arkansas")],
    "T012": [("WA", "Washington"), ("OR", "Oregon")],
    "T013": [("CA", "California")],  # Northern CA zips
    "T014": [("CA", "California")],  # Southern CA zips
    "T015": [("CO", "Colorado"), ("AZ", "Arizona"), ("UT", "Utah"), ("NV", "Nevada"), ("NM", "New Mexico")],
}

CITIES_BY_STATE = {
    "NY": ["New York", "Brooklyn", "Bronx", "Queens", "Buffalo", "Rochester", "Albany", "Syracuse",
           "Yonkers", "White Plains", "Ithaca", "Utica", "Binghamton", "Poughkeepsie", "Schenectady"],
    "NJ": ["Newark", "Jersey City", "New Brunswick", "Trenton", "Camden", "Morristown",
           "Princeton", "Hoboken", "Paterson", "Elizabeth", "Edison", "Cherry Hill"],
    "MA": ["Boston", "Cambridge", "Worcester", "Springfield", "Salem", "Lowell", "Brockton",
           "Quincy", "Newton", "Framingham", "Brookline", "Medford"],
    "CT": ["New Haven", "Hartford", "Stamford", "Bridgeport", "Waterbury", "Norwalk", "Danbury", "Greenwich"],
    "RI": ["Providence", "Warwick", "Cranston", "Pawtucket"],
    "NH": ["Manchester", "Concord", "Nashua", "Dover", "Keene", "Lebanon"],
    "PA": ["Philadelphia", "Pittsburgh", "Allentown", "Reading", "Lancaster", "Scranton",
           "Harrisburg", "Erie", "Bethlehem", "York", "State College", "Wilkes-Barre"],
    "DE": ["Wilmington", "Dover", "Newark", "Middletown"],
    "DC": ["Washington"],
    "MD": ["Baltimore", "Bethesda", "Rockville", "Silver Spring", "Frederick", "Annapolis",
           "Columbia", "Towson", "Hagerstown", "Salisbury"],
    "VA": ["Richmond", "Norfolk", "Arlington", "Charlottesville", "Roanoke", "Virginia Beach",
           "Alexandria", "Newport News", "Fairfax", "Lynchburg", "Fredericksburg"],
    "WV": ["Charleston", "Morgantown", "Huntington", "Parkersburg"],
    "NC": ["Raleigh", "Durham", "Charlotte", "Chapel Hill", "Winston-Salem", "Greensboro",
           "Asheville", "Wilmington", "Fayetteville", "Cary", "Hickory"],
    "SC": ["Charleston", "Columbia", "Greenville", "Spartanburg", "Myrtle Beach", "Rock Hill"],
    "GA": ["Atlanta", "Savannah", "Augusta", "Macon", "Columbus", "Athens", "Roswell",
           "Marietta", "Alpharetta", "Decatur"],
    "FL": ["Miami", "Tampa", "Orlando", "Jacksonville", "Fort Lauderdale", "Sarasota",
           "St. Petersburg", "Tallahassee", "Gainesville", "Naples", "Palm Beach",
           "Boca Raton", "Clearwater", "Coral Gables"],
    "AL": ["Birmingham", "Huntsville", "Mobile", "Montgomery", "Tuscaloosa", "Auburn"],
    "MS": ["Jackson", "Biloxi", "Hattiesburg", "Gulfport", "Oxford"],
    "OH": ["Cleveland", "Columbus", "Cincinnati", "Akron", "Dayton", "Toledo",
           "Canton", "Youngstown", "Springfield", "Athens"],
    "MI": ["Detroit", "Ann Arbor", "Grand Rapids", "Lansing", "Kalamazoo",
           "Flint", "Dearborn", "Troy", "Traverse City", "Marquette"],
    "IN": ["Indianapolis", "Fort Wayne", "Bloomington", "South Bend", "Evansville",
           "Carmel", "Lafayette", "Terre Haute"],
    "IL": ["Chicago", "Evanston", "Springfield", "Peoria", "Naperville", "Rockford",
           "Aurora", "Champaign", "Joliet", "Elgin", "Decatur", "Bloomington"],
    "WI": ["Milwaukee", "Madison", "Green Bay", "Kenosha", "Racine", "Appleton",
           "Waukesha", "La Crosse"],
    "MN": ["Minneapolis", "Rochester", "St. Paul", "Duluth", "Bloomington",
           "Brooklyn Park", "Edina", "Mankato", "St. Cloud"],
    "IA": ["Des Moines", "Iowa City", "Cedar Rapids", "Davenport", "Sioux City",
           "Waterloo", "Ames"],
    "ND": ["Fargo", "Bismarck", "Grand Forks", "Minot"],
    "TX": ["Houston", "Dallas", "San Antonio", "Austin", "Fort Worth", "El Paso",
           "Plano", "Arlington", "Lubbock", "Corpus Christi", "Amarillo",
           "Laredo", "McAllen", "Midland", "Beaumont"],
    "LA": ["New Orleans", "Baton Rouge", "Shreveport", "Lafayette", "Lake Charles",
           "Monroe", "Alexandria"],
    "OK": ["Oklahoma City", "Tulsa", "Norman", "Broken Arrow", "Edmond", "Lawton"],
    "AR": ["Little Rock", "Fayetteville", "Fort Smith", "Springdale", "Jonesboro"],
    "WA": ["Seattle", "Tacoma", "Spokane", "Bellevue", "Olympia", "Vancouver",
           "Everett", "Renton", "Kirkland", "Kennewick"],
    "OR": ["Portland", "Eugene", "Salem", "Bend", "Medford", "Corvallis", "Beaverton"],
    "CA": ["Los Angeles", "San Francisco", "San Diego", "Sacramento", "San Jose",
           "Palo Alto", "Irvine", "Pasadena", "Oakland", "Long Beach", "Fresno",
           "Anaheim", "Santa Barbara", "Riverside", "Bakersfield", "Stockton",
           "Torrance", "Burbank", "Glendale", "Redwood City"],
    "CO": ["Denver", "Boulder", "Colorado Springs", "Aurora", "Fort Collins",
           "Lakewood", "Pueblo", "Arvada", "Westminster"],
    "AZ": ["Phoenix", "Tucson", "Scottsdale", "Mesa", "Chandler", "Tempe",
           "Gilbert", "Glendale", "Peoria", "Flagstaff"],
    "UT": ["Salt Lake City", "Provo", "Ogden", "St. George", "Orem", "Sandy"],
    "NV": ["Las Vegas", "Reno", "Henderson", "North Las Vegas", "Sparks"],
    "NM": ["Albuquerque", "Santa Fe", "Las Cruces", "Rio Rancho", "Roswell"],
}

# ZIP prefixes by state (first 3 digits)
ZIP_PREFIXES = {
    "NY": range(100, 150), "NJ": range(70, 90), "MA": range(10, 28),
    "CT": range(60, 70), "RI": range(28, 30), "NH": range(30, 39),
    "PA": range(150, 197), "DE": range(197, 200), "DC": [200, 201, 202],
    "MD": range(206, 220), "VA": range(220, 247), "WV": range(247, 269),
    "NC": range(270, 290), "SC": range(290, 300), "GA": range(300, 320),
    "FL": range(320, 350), "AL": range(350, 370), "MS": range(386, 398),
    "OH": range(430, 460), "MI": range(480, 500), "IN": range(460, 480),
    "IL": range(600, 630), "WI": range(530, 550), "MN": range(550, 568),
    "IA": range(500, 529), "ND": range(580, 589), "TX": range(750, 800),
    "LA": range(700, 715), "OK": range(730, 750), "AR": range(716, 730),
    "WA": range(980, 995), "OR": range(970, 980), "CA": range(900, 970),
    "CO": range(800, 817), "AZ": range(850, 866), "UT": range(840, 848),
    "NV": range(889, 899), "NM": range(870, 885),
}

SPECIALTIES = ["Oncology", "Urology", "Mixed"]
SPECIALTY_WEIGHTS = [0.65, 0.20, 0.15]

ARCHETYPES = ["Hospital", "Clinic", "IDN", "Specialty Pharmacy", "Government"]
ARCHETYPE_WEIGHTS_GP = [0.0, 0.0, 0.85, 0.0, 0.15]
ARCHETYPE_WEIGHTS_PA = [0.45, 0.40, 0.0, 0.10, 0.05]
ARCHETYPE_WEIGHTS_FA = [0.40, 0.45, 0.0, 0.10, 0.05]

GPO_NAMES = ["Onmark", "ION", "Unity", "VitalSource"]
GPO_WEIGHTS = [0.30, 0.25, 0.25, 0.20]

HEALTH_SYSTEM_PREFIXES = [
    "Memorial", "Atlantic", "Keystone", "Peachtree", "Great Lakes",
    "Lone Star", "Pacific", "Mountain", "Sunshine", "Heartland",
    "Northwest", "Capital", "Valley", "Tri-State", "Southern",
    "Heritage", "Pinnacle", "Summit", "Lakewood", "Bayview",
    "Crescent", "Eagle", "Falcon", "Gateway", "Harbor",
    "Ironwood", "Juniper", "Kensington", "Liberty", "Maple",
    "Noble", "Oakwood", "Prairie", "Redwood", "Sierra",
    "Timber", "Union", "Vista", "Westfield", "Zenith",
    "Alliance", "Beacon", "Cascade", "Delta", "Evergreen",
    "Frontier", "Granite", "Highland", "Integrity", "Jade",
    "Aspen", "Bridgeport", "Coastal", "Dominion", "Elmwood",
    "Foxhill", "Glacier", "Horizon", "Imperial", "Jubilee",
    "Keystone", "Lakeshore", "Meridian", "Northgate", "Olympic",
    "Parkview", "Quorum", "Riverside", "Sterling", "Trident",
    "Upstate", "Valor", "Windham", "Xavier", "Yorktown",
    "Arbor", "Blueridge", "Cornerstone", "Daybreak", "Emerald",
    "Freemont", "Goldcrest", "Hillside", "Ivywood", "Jasper",
    "Kingsley", "Landmark", "Montclair", "Newbridge", "Orion",
    "Pemberton", "Quantum", "Rosewood", "Silverton", "Thornton",
    "Unity", "Vanguard", "Whitfield", "Yarmouth", "Zephyr",
]

HEALTH_SYSTEM_SUFFIXES = [
    "Health System", "Medical Group", "Care Network", "Health Alliance",
    "Health Partners", "Medical Center", "Health Network", "Healthcare",
    "Medical Associates", "Health Services", "Clinical Network", "Medical Alliance",
]

FACILITY_TYPES = [
    "Cancer Center", "Oncology Clinic", "Infusion Center", "Urology Center",
    "Medical Center", "Community Oncology", "Regional Cancer Institute",
    "Outpatient Infusion", "Specialty Clinic", "Academic Medical Center",
    "General Hospital", "University Hospital", "Research Hospital",
    "Community Hospital", "Veterans Clinic", "Treatment Center",
    "Surgical Center", "Diagnostic Center", "Rehabilitation Center",
    "Wellness Center",
]

STREET_NAMES = [
    "Main St", "Oak Ave", "Park Blvd", "Medical Dr", "Hospital Way",
    "University Ave", "Lake Shore Dr", "Broadway", "Center St",
    "Health Pkwy", "Campus Dr", "Research Blvd", "Clinic Rd",
    "Innovation Way", "Wellness Dr", "Heritage Ln", "Summit Rd",
]

# Products — same as in seed_data.sql (loaded from the existing products)
NOVAPHARMA_PRODUCTS = [
    ("11111-0101-01", "ZENOVAX", "docetaxel", "80MG/4ML", "Injectable", 1, "Oncology", "Taxanes", "Docetaxel", 1.0, 80.0),
    ("11111-0101-02", "ZENOVAX", "docetaxel", "20MG/1ML", "Injectable", 1, "Oncology", "Taxanes", "Docetaxel", 0.25, 20.0),
    ("11111-0201-01", "CARBOTREL", "carboplatin", "450MG/45ML", "Injectable", 1, "Oncology", "Platinum Compounds", "Carboplatin", 1.0, 450.0),
    ("11111-0201-02", "CARBOTREL", "carboplatin", "150MG/15ML", "Injectable", 1, "Oncology", "Platinum Compounds", "Carboplatin", 0.333, 150.0),
    ("11111-0301-01", "GEMTARA", "gemcitabine", "1000MG", "Injectable", 1, "Oncology", "Antimetabolites", "Gemcitabine", 1.0, 1000.0),
    ("11111-0301-02", "GEMTARA", "gemcitabine", "200MG", "Injectable", 1, "Oncology", "Antimetabolites", "Gemcitabine", 0.2, 200.0),
    ("11111-0401-01", "PAXELIUM", "pemetrexed", "500MG", "Injectable", 1, "Oncology", "Antimetabolites", "Pemetrexed", 1.0, 500.0),
    ("11111-0401-02", "PAXELIUM", "pemetrexed", "100MG", "Injectable", 1, "Oncology", "Antimetabolites", "Pemetrexed", 0.2, 100.0),
    ("11111-0501-01", "ONCOSETRON", "palonosetron", "0.25MG/5ML", "Injectable", 1, "Oncology", "Antiemetics", "Palonosetron", 1.0, 0.25),
    ("11111-0601-01", "CYCLONOVA", "cyclophosphamide", "1G", "Injectable", 1, "Oncology", "Alkylating Agents", "Cyclophosphamide", 1.0, 1000.0),
    ("11111-0601-02", "CYCLONOVA", "cyclophosphamide", "500MG", "Injectable", 1, "Oncology", "Alkylating Agents", "Cyclophosphamide", 0.5, 500.0),
    ("11111-0701-01", "LUPREX DEPOT", "leuprolide", "22.5MG", "Injectable", 1, "Urology", "GnRH Agonists", "Leuprolide", 1.0, 22.5),
    ("11111-0701-02", "LUPREX DEPOT", "leuprolide", "7.5MG", "Injectable", 1, "Urology", "GnRH Agonists", "Leuprolide", 0.333, 7.5),
]

COMPETITOR_PRODUCTS = [
    ("22222-0101-01", "TAXOTERE", "docetaxel", "80MG/4ML", "Injectable", 0, "Oncology", "Taxanes", "Docetaxel", 1.0, 80.0),
    ("22222-0101-02", "DOCETAXEL GENERIC", "docetaxel", "80MG/4ML", "Injectable", 0, "Oncology", "Taxanes", "Docetaxel", 1.0, 80.0),
    ("22222-0201-01", "PARAPLATIN", "carboplatin", "450MG/45ML", "Injectable", 0, "Oncology", "Platinum Compounds", "Carboplatin", 1.0, 450.0),
    ("22222-0201-02", "CARBOPLATIN GENERIC", "carboplatin", "150MG/15ML", "Injectable", 0, "Oncology", "Platinum Compounds", "Carboplatin", 0.333, 150.0),
    ("22222-0301-01", "GEMZAR", "gemcitabine", "1000MG", "Injectable", 0, "Oncology", "Antimetabolites", "Gemcitabine", 1.0, 1000.0),
    ("22222-0301-02", "GEMCITABINE GENERIC", "gemcitabine", "200MG", "Injectable", 0, "Oncology", "Antimetabolites", "Gemcitabine", 0.2, 200.0),
    ("22222-0401-01", "ALIMTA", "pemetrexed", "500MG", "Injectable", 0, "Oncology", "Antimetabolites", "Pemetrexed", 1.0, 500.0),
    ("22222-0401-02", "PEMETREXED GENERIC", "pemetrexed", "100MG", "Injectable", 0, "Oncology", "Antimetabolites", "Pemetrexed", 0.2, 100.0),
    ("22222-0501-01", "ALOXI", "palonosetron", "0.25MG/5ML", "Injectable", 0, "Oncology", "Antiemetics", "Palonosetron", 1.0, 0.25),
    ("22222-0501-02", "PALONOSETRON GENERIC", "palonosetron", "0.25MG/5ML", "Injectable", 0, "Oncology", "Antiemetics", "Palonosetron", 1.0, 0.25),
    ("22222-0601-01", "CYTOXAN", "cyclophosphamide", "1G", "Injectable", 0, "Oncology", "Alkylating Agents", "Cyclophosphamide", 1.0, 1000.0),
    ("22222-0601-02", "CYCLOPHOSPHAMIDE GENERIC", "cyclophosphamide", "500MG", "Injectable", 0, "Oncology", "Alkylating Agents", "Cyclophosphamide", 0.5, 500.0),
    ("22222-0701-01", "LUPRON DEPOT", "leuprolide", "22.5MG", "Injectable", 0, "Urology", "GnRH Agonists", "Leuprolide", 1.0, 22.5),
    ("22222-0701-02", "ELIGARD", "leuprolide", "22.5MG", "Injectable", 0, "Urology", "GnRH Agonists", "Leuprolide", 1.0, 22.5),
    ("22222-0801-01", "FIRMAGON", "degarelix", "240MG", "Injectable", 0, "Urology", "GnRH Antagonists", "Degarelix", 1.0, 240.0),
    ("22222-0901-01", "XTANDI", "enzalutamide", "40MG", "Oral", 0, "Urology", "Antiandrogens", "Enzalutamide", 1.0, 40.0),
    ("22222-1001-01", "ZYTIGA", "abiraterone", "250MG", "Oral", 0, "Urology", "CYP17 Inhibitors", "Abiraterone", 1.0, 250.0),
    ("22222-1101-01", "KEYTRUDA", "pembrolizumab", "100MG/4ML", "Injectable", 0, "Oncology", "Immunotherapy", "PD-1 Inhibitors", 1.0, 100.0),
    ("22222-1201-01", "OPDIVO", "nivolumab", "240MG/24ML", "Injectable", 0, "Oncology", "Immunotherapy", "PD-1 Inhibitors", 1.0, 240.0),
    ("22222-1301-01", "AVASTIN", "bevacizumab", "400MG/16ML", "Injectable", 0, "Oncology", "Angiogenesis Inhibitors", "VEGF Inhibitors", 1.0, 400.0),
    ("22222-1301-02", "BEVACIZUMAB BIOSIMILAR", "bevacizumab", "400MG/16ML", "Injectable", 0, "Oncology", "Angiogenesis Inhibitors", "VEGF Inhibitors", 1.0, 400.0),
    ("22222-1401-01", "ABRAXANE", "paclitaxel albumin", "100MG", "Injectable", 0, "Oncology", "Taxanes", "Paclitaxel", 1.0, 100.0),
    ("22222-1501-01", "CISPLATIN GENERIC", "cisplatin", "50MG/50ML", "Injectable", 0, "Oncology", "Platinum Compounds", "Cisplatin", 1.0, 50.0),
    ("22222-1601-01", "OXALIPLATIN GENERIC", "oxaliplatin", "100MG/20ML", "Injectable", 0, "Oncology", "Platinum Compounds", "Oxaliplatin", 1.0, 100.0),
    ("22222-1701-01", "DOXORUBICIN GENERIC", "doxorubicin", "50MG/25ML", "Injectable", 0, "Oncology", "Anthracyclines", "Doxorubicin", 1.0, 50.0),
    ("22222-1801-01", "IRINOTECAN GENERIC", "irinotecan", "100MG/5ML", "Injectable", 0, "Oncology", "Topoisomerase Inhibitors", "Irinotecan", 1.0, 100.0),
    ("22222-1901-01", "ERBITUX", "cetuximab", "200MG/100ML", "Injectable", 0, "Oncology", "EGFR Inhibitors", "Cetuximab", 1.0, 200.0),
]

ALL_PRODUCTS = NOVAPHARMA_PRODUCTS + COMPETITOR_PRODUCTS

# WAC price ranges per mg for different drug categories
WAC_PER_MG = {
    "ZENOVAX": 6.2, "CARBOTREL": 0.9, "GEMTARA": 0.6, "PAXELIUM": 1.58,
    "ONCOSETRON": 580.0, "CYCLONOVA": 1.75, "LUPREX DEPOT": 35.5,
    "TAXOTERE": 8.1, "DOCETAXEL GENERIC": 2.5, "PARAPLATIN": 0.9,
    "CARBOPLATIN GENERIC": 0.4, "GEMZAR": 0.45, "GEMCITABINE GENERIC": 0.2,
    "ALIMTA": 1.58, "PEMETREXED GENERIC": 0.5, "ALOXI": 580.0,
    "PALONOSETRON GENERIC": 200.0, "CYTOXAN": 0.4, "CYCLOPHOSPHAMIDE GENERIC": 0.15,
    "LUPRON DEPOT": 35.5, "ELIGARD": 33.0, "FIRMAGON": 18.75,
    "XTANDI": 87.5, "ZYTIGA": 26.0, "KEYTRUDA": 150.0,
    "OPDIVO": 62.5, "AVASTIN": 37.5, "BEVACIZUMAB BIOSIMILAR": 25.0,
    "ABRAXANE": 100.0, "CISPLATIN GENERIC": 0.5, "OXALIPLATIN GENERIC": 1.0,
    "DOXORUBICIN GENERIC": 2.0, "IRINOTECAN GENERIC": 1.0, "ERBITUX": 15.0,
}

# Products relevant per specialty
ONCOLOGY_NOVA_NDCS = [p[0] for p in NOVAPHARMA_PRODUCTS if p[6] == "Oncology"]
UROLOGY_NOVA_NDCS = [p[0] for p in NOVAPHARMA_PRODUCTS if p[6] == "Urology"]
ONCOLOGY_COMP_NDCS = [p[0] for p in COMPETITOR_PRODUCTS if p[6] == "Oncology"]
UROLOGY_COMP_NDCS = [p[0] for p in COMPETITOR_PRODUCTS if p[6] == "Urology"]

PRODUCT_BY_NDC = {p[0]: p for p in ALL_PRODUCTS}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def generate_zip(state: str) -> str:
    prefixes = ZIP_PREFIXES.get(state, [100])
    prefix = random.choice(list(prefixes))
    suffix = random.randint(0, 99)
    return f"{prefix:03d}{suffix:02d}"


def pick_weighted(options, weights):
    return random.choices(options, weights=weights, k=1)[0]


def generate_address(city: str) -> str:
    num = random.randint(100, 9999)
    street = random.choice(STREET_NAMES)
    return f"{num} {street}"


# ---------------------------------------------------------------------------
# Organization generation
# ---------------------------------------------------------------------------

def generate_organizations():
    orgs = []
    org_index = {"grandparents": [], "parents": [], "facilities": []}

    used_names = set()

    def unique_system_name():
        for _ in range(1000):
            prefix = random.choice(HEALTH_SYSTEM_PREFIXES)
            suffix = random.choice(HEALTH_SYSTEM_SUFFIXES)
            name = f"{prefix} {suffix}"
            if name not in used_names:
                used_names.add(name)
                return name
        seq = len(used_names)
        return f"Health System {seq}"

    def pick_territory():
        return random.choice(TERRITORIES)

    def pick_location(territory_id):
        states = STATES_BY_TERRITORY.get(territory_id, [("NY", "New York")])
        state_code, _ = random.choice(states)
        city = random.choice(CITIES_BY_STATE.get(state_code, ["Unknown"]))
        zipcode = generate_zip(state_code)
        return state_code, city, zipcode

    # --- Grandparents ---
    for i in range(NUM_GRANDPARENTS):
        org_id = f"GP{i+1:04d}"
        name = unique_system_name()
        terr = pick_territory()
        terr_id, terr_name, region_id, region_name = terr
        state, city, zipcode = pick_location(terr_id)
        specialty = pick_weighted(SPECIALTIES, SPECIALTY_WEIGHTS)
        gpo = pick_weighted(GPO_NAMES, GPO_WEIGHTS) if random.random() < 0.90 else None
        is_340b = 0

        org = {
            "org_id": org_id, "org_name": name, "org_type": "Grandparent",
            "org_status": "Active", "org_archetype": "IDN",
            "specialty": specialty, "address_line1": generate_address(city),
            "city": city, "state": state, "zip": zipcode,
            "territory_name": terr_name, "region_name": region_name,
            "parent_org_id": None, "parent_org_name": None,
            "grandparent_org_id": None, "grandparent_org_name": None,
            "gpo_name": gpo, "is_340b": is_340b,
            "_territory_id": terr_id,
        }
        orgs.append(org)
        org_index["grandparents"].append(org)

    # --- Parents ---
    for i in range(NUM_PARENTS):
        gp = random.choice(org_index["grandparents"])
        org_id = f"PA{i+1:04d}"
        ftype = random.choice(FACILITY_TYPES[:7])
        name = f"{gp['org_name'].split()[0]} {ftype}"
        if name in used_names:
            name = f"{name} {random.choice(['East','West','North','South','Central'])}"
        used_names.add(name)

        state, city, zipcode = pick_location(gp["_territory_id"])
        archetype = pick_weighted(ARCHETYPES, ARCHETYPE_WEIGHTS_PA)

        org = {
            "org_id": org_id, "org_name": name, "org_type": "Parent",
            "org_status": "Active" if random.random() < 0.95 else "Inactive",
            "org_archetype": archetype, "specialty": gp["specialty"],
            "address_line1": generate_address(city),
            "city": city, "state": state, "zip": zipcode,
            "territory_name": gp["territory_name"], "region_name": gp["region_name"],
            "parent_org_id": None, "parent_org_name": None,
            "grandparent_org_id": gp["org_id"], "grandparent_org_name": gp["org_name"],
            "gpo_name": gp["gpo_name"], "is_340b": 1 if random.random() < 0.08 else 0,
            "_territory_id": gp["_territory_id"],
        }
        orgs.append(org)
        org_index["parents"].append(org)

    # --- Facilities with parents ---
    for i in range(NUM_FACILITIES_WITH_PARENT):
        pa = random.choice(org_index["parents"])
        org_id = f"FA{i+1:04d}"
        ftype = random.choice(FACILITY_TYPES)
        qualifier = random.choice(["", " East", " West", " North", " South", " Main", " Satellite"])
        name = f"{pa['org_name'].split()[0]} {ftype}{qualifier}"
        if name in used_names:
            name = f"{name} {i+1}"
        used_names.add(name)

        state, city, zipcode = pick_location(pa["_territory_id"])
        archetype = pick_weighted(ARCHETYPES, ARCHETYPE_WEIGHTS_FA)

        org = {
            "org_id": org_id, "org_name": name, "org_type": "Facility",
            "org_status": "Active" if random.random() < 0.93 else "Inactive",
            "org_archetype": archetype, "specialty": pa["specialty"],
            "address_line1": generate_address(city),
            "city": city, "state": state, "zip": zipcode,
            "territory_name": pa["territory_name"], "region_name": pa["region_name"],
            "parent_org_id": pa["org_id"], "parent_org_name": pa["org_name"],
            "grandparent_org_id": pa["grandparent_org_id"],
            "grandparent_org_name": pa["grandparent_org_name"],
            "gpo_name": pa["gpo_name"],
            "is_340b": 1 if random.random() < 0.12 else 0,
            "_territory_id": pa["_territory_id"],
        }
        orgs.append(org)
        org_index["facilities"].append(org)

    # --- Standalone facilities ---
    for i in range(NUM_STANDALONE_FACILITIES):
        org_id = f"SA{i+1:04d}"
        terr = pick_territory()
        terr_id, terr_name, region_id, region_name = terr
        state, city, zipcode = pick_location(terr_id)
        specialty = pick_weighted(SPECIALTIES, SPECIALTY_WEIGHTS)
        ftype = random.choice(FACILITY_TYPES)
        name = f"{city} {ftype}"
        if name in used_names:
            name = f"{name} {i+1}"
        used_names.add(name)

        gpo = pick_weighted(GPO_NAMES, GPO_WEIGHTS) if random.random() < 0.65 else None
        archetype = pick_weighted(ARCHETYPES, ARCHETYPE_WEIGHTS_FA)

        org = {
            "org_id": org_id, "org_name": name, "org_type": "Facility",
            "org_status": "Active" if random.random() < 0.90 else "Inactive",
            "org_archetype": archetype, "specialty": specialty,
            "address_line1": generate_address(city),
            "city": city, "state": state, "zip": zipcode,
            "territory_name": terr_name, "region_name": region_name,
            "parent_org_id": None, "parent_org_name": None,
            "grandparent_org_id": None, "grandparent_org_name": None,
            "gpo_name": gpo, "is_340b": 1 if random.random() < 0.10 else 0,
            "_territory_id": terr_id,
        }
        orgs.append(org)
        org_index["facilities"].append(org)

    return orgs, org_index


# ---------------------------------------------------------------------------
# ZIP territory generation
# ---------------------------------------------------------------------------

def generate_zip_territories(orgs):
    zip_terr = {}

    for org in orgs:
        zipcode = org["zip"]
        if zipcode in zip_terr:
            continue
        terr_id = org["_territory_id"]
        terr = next(t for t in TERRITORIES if t[0] == terr_id)
        zip_terr[zipcode] = {
            "zip": zipcode,
            "state": org["state"],
            "territory_number": terr[0],
            "territory_name": terr[1],
            "region_number": terr[2],
            "region_name": terr[3],
        }

    # Add additional zips to fill out territories
    for terr_id, terr_name, region_id, region_name in TERRITORIES:
        states = STATES_BY_TERRITORY.get(terr_id, [])
        for state_code, _ in states:
            for _ in range(10):
                z = generate_zip(state_code)
                if z not in zip_terr:
                    zip_terr[z] = {
                        "zip": z,
                        "state": state_code,
                        "territory_number": terr_id,
                        "territory_name": terr_name,
                        "region_number": region_id,
                        "region_name": region_name,
                    }

    return list(zip_terr.values())


# ---------------------------------------------------------------------------
# Sales generation
# ---------------------------------------------------------------------------

def generate_sales(orgs, org_index):
    selling_orgs = [
        o for o in orgs
        if o["org_type"] == "Facility" and o["org_status"] == "Active"
    ]

    # Assign volume tiers — controls how often an org appears in weekly samples
    org_tiers = {}
    for org in selling_orgs:
        roll = random.random()
        if roll < 0.05:
            org_tiers[org["org_id"]] = "large"
        elif roll < 0.20:
            org_tiers[org["org_id"]] = "medium"
        else:
            org_tiers[org["org_id"]] = "small"

    tier_weight = {"large": 10, "medium": 3, "small": 1}
    org_weights = [tier_weight[org_tiers[o["org_id"]]] for o in selling_orgs]

    # Pre-compute product lists by specialty to avoid repeated filtering
    nova_onc = [p for p in NOVAPHARMA_PRODUCTS if p[6] == "Oncology"]
    nova_uro = [p for p in NOVAPHARMA_PRODUCTS if p[6] == "Urology"]
    comp_onc = [p for p in COMPETITOR_PRODUCTS if p[6] == "Oncology"]
    comp_uro = [p for p in COMPETITOR_PRODUCTS if p[6] == "Urology"]

    # Date anchors: 156 weeks (~3 years) ending 2026-09-19
    base_saturday = datetime(2026, 9, 19)
    weeks = []
    for wk in range(NUM_WEEKS):
        sat = base_saturday - timedelta(weeks=wk)
        mon = sat - timedelta(days=5)
        mo_offset = (base_saturday.year * 12 + base_saturday.month) - (sat.year * 12 + sat.month)
        period_mo = sat.strftime("%Y-%m")
        q = (sat.month - 1) // 3 + 1
        period_qtr = f"{sat.year}-Q{q}"
        period_wk = f"{sat.year}-W{sat.isocalendar()[1]:02d}"
        weeks.append({
            "wk_offset": wk,
            "mo_offset": mo_offset,
            "week_start": mon,
            "week_ending_date": sat.strftime("%Y-%m-%d"),
            "period_wk": period_wk,
            "period_mo": period_mo,
            "period_qtr": period_qtr,
        })

    target_per_week = NUM_SALES // NUM_WEEKS
    sales_count = 0
    sale_id = 0

    def make_sale(org, product_tuple, data_source, week_info):
        nonlocal sale_id
        sale_id += 1
        ndc, drug_name = product_tuple[0], product_tuple[1]
        brand_flag = product_tuple[5]
        mg_equiv = product_tuple[10]
        specialty = product_tuple[6]

        tier = org_tiers.get(org["org_id"], "small")
        if tier == "large":
            packs = random.randint(3, 25)
        elif tier == "medium":
            packs = random.randint(1, 12)
        else:
            packs = random.randint(1, 5)

        total_mg = packs * mg_equiv
        wac_per_mg = WAC_PER_MG.get(drug_name, 1.0)
        noise = random.uniform(0.85, 1.15)
        wac = round(total_mg * wac_per_mg * noise, 2) if data_source != "hub_dispense" else 0.0

        txn_date = week_info["week_start"] + timedelta(days=random.randint(0, 4))

        return (
            org["org_id"], ndc, drug_name, data_source, brand_flag,
            float(packs), round(total_mg, 2), wac,
            txn_date.strftime("%Y-%m-%d"), week_info["week_ending_date"],
            org["state"], specialty,
            week_info["period_wk"], week_info["period_mo"], week_info["period_qtr"],
            week_info["wk_offset"], week_info["mo_offset"],
        )

    def pick_product_and_source(org_spec):
        source_roll = random.random()
        if source_roll < 0.45:
            data_source = "distributor"
            if org_spec == "Urology":
                prod = random.choice(nova_uro)
            elif org_spec == "Oncology":
                prod = random.choice(nova_onc)
            else:
                prod = random.choice(NOVAPHARMA_PRODUCTS)
        elif source_roll < 0.50:
            data_source = "hub_dispense"
            prod = random.choice(nova_uro if org_spec == "Urology" else nova_onc)
        else:
            data_source = "market_data"
            if org_spec == "Urology":
                prod = random.choice(comp_uro)
            elif org_spec == "Oncology":
                prod = random.choice(comp_onc)
            else:
                prod = random.choice(COMPETITOR_PRODUCTS)
        return prod, data_source

    print(f"Generating {NUM_SALES:,} sales across {len(selling_orgs)} facilities and {NUM_WEEKS} weeks...")

    for week_info in weeks:
        sampled_orgs = random.choices(selling_orgs, weights=org_weights, k=target_per_week)
        for org in sampled_orgs:
            prod, data_source = pick_product_and_source(org["specialty"])
            yield make_sale(org, prod, data_source, week_info)
            sales_count += 1

        if sales_count >= NUM_SALES:
            break

    while sales_count < NUM_SALES:
        org = random.choice(selling_orgs)
        week_info = random.choice(weeks)
        prod, data_source = pick_product_and_source(org["specialty"])
        yield make_sale(org, prod, data_source, week_info)
        sales_count += 1

    print(f"Generated {sales_count:,} sales records.")


# ---------------------------------------------------------------------------
# CSV writing
# ---------------------------------------------------------------------------

ORG_FIELDS = [
    "org_id", "org_name", "org_type", "org_status", "org_archetype",
    "specialty", "address_line1", "city", "state", "zip",
    "parent_org_id", "parent_org_name",
    "grandparent_org_id", "grandparent_org_name", "gpo_name", "is_340b",
]

PRODUCT_FIELDS = [
    "ndc", "drug_name", "generic_name", "strength", "form",
    "brand_flag", "specialty", "market_category", "market_subcategory",
    "unit_conversion_factor", "mg_equivalent",
]

SALES_FIELDS = [
    "org_id", "ndc", "drug_name", "data_source", "brand_flag",
    "pack_units", "total_mg", "wac", "transaction_date", "week_ending_date",
    "state", "specialty", "period_wk", "period_mo", "period_qtr",
    "wk_offset", "mo_offset",
]

ZIP_FIELDS = [
    "zip", "state", "territory_number", "territory_name",
    "region_number", "region_name",
]


def write_csv(filepath, fieldnames, rows):
    with open(filepath, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(fieldnames)
        for row in rows:
            if isinstance(row, dict):
                writer.writerow([row.get(f, "") for f in fieldnames])
            else:
                writer.writerow(row)
    print(f"  {filepath} ({os.path.getsize(filepath) / 1024 / 1024:.1f} MB)")


def write_sales_csv(filepath, fieldnames, sales_gen):
    """Stream sales to CSV to avoid holding 1M rows in memory."""
    count = 0
    with open(filepath, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(fieldnames)
        for row in sales_gen:
            writer.writerow(row)
            count += 1
            if count % 200_000 == 0:
                print(f"    ... {count:,} sales written")
    size = os.path.getsize(filepath) / 1024 / 1024
    print(f"  {filepath} ({size:.1f} MB, {count:,} rows)")
    return count


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print("=== Generating organizations ===")
    orgs, org_index = generate_organizations()
    write_csv(OUT_DIR / "organizations.csv", ORG_FIELDS, orgs)
    print(f"  {len(orgs):,} organizations")

    print("\n=== Generating products ===")
    products_as_rows = [list(p) for p in ALL_PRODUCTS]
    write_csv(OUT_DIR / "products.csv", PRODUCT_FIELDS, products_as_rows)
    print(f"  {len(ALL_PRODUCTS)} products")

    print("\n=== Generating zip territories ===")
    zips = generate_zip_territories(orgs)
    write_csv(OUT_DIR / "zip_territory.csv", ZIP_FIELDS, zips)
    print(f"  {len(zips):,} zip codes")

    print("\n=== Generating sales ===")
    sales_gen = generate_sales(orgs, org_index)
    write_sales_csv(OUT_DIR / "sales.csv", SALES_FIELDS, sales_gen)


if __name__ == "__main__":
    main()
