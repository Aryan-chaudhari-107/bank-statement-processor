"""Training dataset generator and ML model trainer for bank transaction classification."""

import random
import sys
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import joblib
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

from src.classifier.cleaner import clean_description

DATA_DIR = Path("data")
MODELS_DIR = Path("models")
CSV_PATH = DATA_DIR / "training_data.csv"
MODEL_PATH = MODELS_DIR / "classifier.pkl"

CATEGORY_TEMPLATES: dict[str, list[str]] = {
    "Salary": [
        "NEFT CR-{ifsc}-ACME TECH CORP-SALARY {month}",
        "ACH C- INFOSYS LTD MONTHLY SALARY {ref}",
        "SALARY FOR THE MONTH OF {month}",
        "NEFT CR-{ifsc}-TECHNOVA SYSTEMS-SALARY {month}",
        "MONTHLY PAYROLL DIRECT DEPOSIT {ref}",
        "CREDIT-SALARY-{ref}-WIPRO TECHNOLOGIES",
        "STIPEND PAYMENT {month} INTERNSHIP",
        "SALARY DISBURSEMENT TCS {ref}",
        "ACH C- ACCENTURE SERVICES SALARY",
        "NEFT SALARY CREDIT HCL TECHNOLOGIES",
        "EMPLOYEE PAYROLL SALARY CREDIT {month}",
        "MONTHLY STIPEND RESEARCH FELLOW {ref}",
        "NEFT CR-{ifsc}-GLOBAL TECH-REMUNERATION {month}",
        "ACH C- STRATTON CORP WAGES {month}",
        "MONTHLY CONSULTING RETAINER FEE CREDIT {month}",
        "PROFESSIONAL COMPENSATION ADVANCE {ref}",
        "HONORARIUM PAYOUT CONSULTANCY {ref}",
    ],
    "Food & Dining": [
        "UPI/{ref}/SWIGGY FOOD ORDER/{handle}",
        "UPI/{ref}/ZOMATO ONLINE ORDER/{handle}",
        "POS {card} DOMINOS PIZZA OUTLET {city}",
        "POS {card} MCDONALDS BURGER RESTAURANT {city}",
        "UPI-STARBUCKS COFFEE-{handle}-{ref}-PAYMENT",
        "POS {card} BURGER KING OUTLET {city}",
        "UPI/{ref}/CHAAYOS CHAI CAFE/{handle}",
        "POS {card} SUBWAY SANDWICH {city}",
        "UPI/{ref}/KFC FRIED CHICKEN/{handle}",
        "POS {card} HALDIRAM RESTAURANT SWEETS {city}",
        "UPI/{ref}/BARBEQUE NATION DINING {city}",
        "POS {card} CAFE COFFEE DAY BEVERAGES {city}",
        "UPI/{ref}/EATCLUB MEAL DELIVERY/{handle}",
        "UPI/{ref}/BEHROUZ BIRYANI DINING/{handle}",
        "POS {card} PIZZA HUT RESTAURANT {city}",
        "UPI/{ref}/CHAI POINT TEA CAFE/{handle}",
        "POS {card} SOCIAL PUB RESTAURANT {city}",
        "UPI/{ref}/CURRY HOUSE RESTAURANT/{handle}",
        "POS {card} SPICE KITCHEN DINER {city}",
        "UPI/{ref}/SWEET TOOTH BAKERY CAFE/{handle}",
        "POS {card} CORNER BISTRO CAFE {city}",
        "UPI/{ref}/RUSTIC PIZZERIA EATERY/{handle}",
        "POS {card} DELIGHT BAKERY TREATS {city}",
        "UPI/{ref}/ROYAL MITHAI SWEETS/{handle}",
        "POS {card} SIZZLER TANDOORI GRILL {city}",
        "UPI/{ref}/BREWHOUSE PUB DINING/{handle}",
        "UPI/{ref}/URBAN TIFFIN SERVICE/{handle}",
        "POS {card} BIRYANI EXPRESS DHABA {city}",
    ],
    "Shopping": [
        "UPI/{ref}/AMAZON SHOPPING PAY/{handle}",
        "UPI/{ref}/AMAZON RETAIL INDIA/{handle}",
        "UPI/{ref}/FLIPKART ONLINE SHOPPING/{handle}",
        "POS {card} CROMA ELECTRONICS STORE {city}",
        "UPI/{ref}/MYNTRA FASHION APPAREL/{handle}",
        "POS {card} RELIANCE DIGITAL APPLIANCES {city}",
        "UPI/{ref}/AJIO TRENDS CLOTHING/{handle}",
        "POS {card} DECATHLON SPORTS GEAR {city}",
        "UPI/{ref}/NYKAA BEAUTY COSMETICS/{handle}",
        "POS {card} ZARA CLOTHING RETAIL {city}",
        "UPI/{ref}/TATA CLIQ SHOPPING/{handle}",
        "POS {card} H&M APPAREL STORE {city}",
        "UPI/{ref}/MEESHO ONLINE STORE/{handle}",
        "POS {card} SHOPPERS STOP DEPARTMENT STORE {city}",
        "POS {card} LIFESTYLE CLOTHING STORE {city}",
        "POS {card} IKEA HOME FURNITURE {city}",
        "UPI/{ref}/FASHION BOUTIQUE APPAREL/{handle}",
        "POS {card} URBAN OUTFITTERS STORE {city}",
        "POS {card} SILK APPAREL GARMENTS {city}",
        "UPI/{ref}/MODERN FOOTWEAR STORE/{handle}",
        "POS {card} ELEGANT JEWELLERS RETAIL {city}",
        "UPI/{ref}/KIDS TOYS WORLD STORE/{handle}",
        "POS {card} VISION OPTICALS EYEWEAR {city}",
        "UPI/{ref}/GLAMOUR BEAUTY PARLOUR/{handle}",
        "POS {card} STATIONERY WORLD STORE {city}",
    ],
    "Groceries": [
        "UPI/{ref}/BLINKIT GROCERY DELIVERY/{handle}",
        "UPI/{ref}/ZEPTO QUICK GROCERY/{handle}",
        "UPI/{ref}/INSTAMART GROCERY ORDER/{handle}",
        "POS {card} DMART SUPERMARKET GROCERY {city}",
        "UPI/{ref}/BIGBASKET DAILY GROCERY/{handle}",
        "POS {card} BIG BAZAAR SUPERMARKET {city}",
        "UPI/{ref}/BBDALY MILK DAIRY/{handle}",
        "POS {card} RELIANCE FRESH VEGETABLES {city}",
        "UPI/{ref}/NATURES BASKET ORGANIC/{handle}",
        "POS {card} SPENCERS RETAIL SUPERSTORE {city}",
        "UPI/{ref}/MILKBASKET MORNING MILK/{handle}",
        "UPI/{ref}/DUNZO DAILY ESSENTIALS/{handle}",
        "POS {card} MORE SUPERMARKET PROVISIONS {city}",
        "POS {card} ORGANIC VEGETABLE MART {city}",
        "UPI/{ref}/FRESH PRODUCE FRUITS VEG/{handle}",
        "POS {card} DAILY PROVISION KIRANA {city}",
        "UPI/{ref}/SUNSHINE DAIRY FARMS/{handle}",
        "POS {card} GREEN VEGGIE FRUIT STALL {city}",
        "UPI/{ref}/WHOLESALE DRY FRUITS/{handle}",
        "POS {card} COLD STORAGE SUPERSTORE {city}",
        "UPI/{ref}/SPICES CONDIMENTS BAZAAR/{handle}",
    ],
    "Transport": [
        "UPI/{ref}/UBER CAB RIDE TRIP/{handle}",
        "UPI/{ref}/OLA CABS AUTO RIDE/{handle}",
        "UPI/{ref}/RAPIDO BIKE TAXI RIDE/{handle}",
        "POS {card} HPCL PETROL PUMP FUEL {city}",
        "POS {card} BPCL FUEL STATION DIESEL {city}",
        "POS {card} IOCL AUTO SERVICE PETROL {city}",
        "POS {card} SHELL FUEL STATION {city}",
        "NETC FASTAG TOLL RECHARGE {ref}",
        "TOLL PLAZA HIGHWAY PASS {ref}",
        "DMRC METRO SMARTCARD RECHARGE {ref}",
        "BMRC METRO RAIL PASS TRAVEL {ref}",
        "INDIAN OIL PETROL PUMP FUEL {ref}",
        "CITY TAXI CAB SERVICE {city}",
        "UPI/{ref}/EXPRESS CARGO FREIGHT/{handle}",
        "UPI/{ref}/CITY AUTO TAXI RIDES/{handle}",
        "POS {card} SPEED EV CHARGING STATION {city}",
        "EXPRESSWAY HIGHWAY TOLL PASS {ref}",
        "UPI/{ref}/SCOOTER BIKE RENTALS/{handle}",
        "INTERCITY BUS PASS TICKETS {ref}",
    ],
    "Bills & Utilities": [
        "BIL/BPAY/BESCOM ELECTRICITY BILL {ref}",
        "ACH D- LIC OF INDIA LIFE INSURANCE {ref}",
        "UPI/{ref}/AIRTEL BROADBAND FIBER BILL/{handle}",
        "UPI/{ref}/JIO MOBILE PREPAID RECHARGE/{handle}",
        "BIL/BPAY/TNEB POWER ELECTRIC BILL {ref}",
        "UPI/{ref}/VODAFONE IDEA POSTPAID BILL/{handle}",
        "BIL/BPAY/MAHAVITARAN ELECTRICITY POWER {ref}",
        "UPI/{ref}/ACT FIBERNET INTERNET BILL/{handle}",
        "BIL/BPAY/IGL PIPED NATURAL GAS BILL {ref}",
        "UPI/{ref}/TATA PLAY DTH TV RECHARGE/{handle}",
        "BILLDESK UTILITY BILL PAYMENT {ref}",
        "BIL/BPAY/MUNICIPAL WATER SUPPLY BILL {ref}",
        "BIL/BPAY/CESC POWER ELECTRICITY SUPPLY {ref}",
        "UPI/{ref}/BSNL LANDLINE BROADBAND/{handle}",
        "BIL/BPAY/CITY POWER ENERGY UTILITY {ref}",
        "ACH D- NATIONAL LIFE INSURANCE POL {ref}",
        "BIL/BPAY/METRO WATER SUPPLY TAX {ref}",
        "UPI/{ref}/BROADBAND FIBER LINK/{handle}",
        "BIL/BPAY/COOKING GAS CYLINDER {ref}",
        "ACH D- GENERAL INSURANCE PREMIUM {ref}",
    ],
    "Rent": [
        "IMPS-{ref}-RAHUL SHARMA-HOUSE RENT-{ifsc}",
        "UPI/{ref}/MONTHLY RENT PAYMENT APRIL/{handle}",
        "IMPS-{ref}-ANAND VERMA-FLAT RENT-{ifsc}",
        "NOBROKER RENT PAYMENT MONTHLY {ref}",
        "UPI/{ref}/PG HOSTEL ACCOMMODATION RENT/{handle}",
        "IMPS-{ref}-SURESH MENON-RENT HOME-{ifsc}",
        "MONTHLY APARTMENT RENT TRANSFER {ref}",
        "RESIDENTIAL LEASE RENT PAYMENT {ref}",
        "IMPS-{ref}-SANJAY GUPTA-ROOM LEASE-{ifsc}",
        "MONTHLY TENANCY RENTAL DEPOSIT {ref}",
        "UPI/{ref}/HOSTEL ROOM FEE PAYMENT/{handle}",
        "HOUSING SOCIETY MAINTENANCE RENT {ref}",
        "ACCOMMODATION LEASE PAYMENT {ref}",
    ],
    "EMI & Loans": [
        "ACH D- BAJAJ FINANCE LOAN EMI {ref}",
        "ACH D- HDFC BANK HOME LOAN EMI {ref}",
        "ACH D- ICICI BANK CAR VEHICLE LOAN EMI {ref}",
        "ACH D- TATA CAPITAL PERSONAL LOAN EMI {ref}",
        "ACH D- HDB FINANCIAL SERVICES LOAN {ref}",
        "LOAN EMI AUTO DEBIT INSTALLMENT SBI {ref}",
        "MUTHOOT FINANCE GOLD LOAN EMI {ref}",
        "ACH D- ADITYA BIRLA FINANCE LOAN {ref}",
        "ACH D- EDUCATION LOAN EMI PAYMENT {ref}",
        "ACH D- VEHICLE AUTO FINANCE LOAN {ref}",
        "ACH D- HOUSING FINANCE CREDIT EMI {ref}",
        "ACH D- CONSUMER DURABLES LOAN EMI {ref}",
        "MICROFINANCE LOAN REPAYMENT {ref}",
        "TERM LOAN INSTALLMENT DEBIT {ref}",
    ],
    "Investments": [
        "NEFT DR-{ifsc}-ZERODHA BROKING STOCKS-{ref}",
        "ACH D- GROWW INVEST TECH MUTUAL FUND {ref}",
        "UPI/{ref}/UPSTOX SECURITIES TRADING/{handle}",
        "ACH D- HDFC MUTUAL FUND SIP EQUITY {ref}",
        "ACH D- SBI MUTUAL FUND SIP INVESTMENT {ref}",
        "ACH D- ICICI PRUDENTIAL MF SIP {ref}",
        "UPI/{ref}/ANGEL ONE BROKING INVEST/{handle}",
        "ACH D- PPFAS MUTUAL FUND SIP {ref}",
        "ACH D- UTI MUTUAL FUND SCHEME {ref}",
        "SMALLCASE TECHNOLOGIES STOCKS {ref}",
        "KOTAK SECURITIES STOCK INVESTMENT {ref}",
        "ACH D- ASSET MANAGEMENT EQUITY {ref}",
        "UPI/{ref}/CAPITAL WEALTH ADVISORY/{handle}",
        "ACH D- FINANCIAL SERVICES BROKING {ref}",
        "UPI/{ref}/DIGITAL BULLION SAVINGS/{handle}",
        "NATIONAL PENSION SCHEME DEPOSIT {ref}",
    ],
    "Entertainment": [
        "UPI/{ref}/NETFLIX STREAMING SUBSCRIPTION/{handle}",
        "UPI/{ref}/SPOTIFY MUSIC STREAMING/{handle}",
        "UPI/{ref}/DISNEY HOTSTAR VIP SUBSCRIPTION/{handle}",
        "POS {card} PVR CINEMAS MOVIE TICKETS {city}",
        "POS {card} INOX LEISURE MOVIE THEATRE {city}",
        "UPI/{ref}/BOOKMYSHOW MOVIE CINEMA TICKETS/{handle}",
        "UPI/{ref}/PRIME VIDEO SUBSCRIPTION/{handle}",
        "UPI/{ref}/APPLE MUSIC SUBSCRIPTION/{handle}",
        "UPI/{ref}/YOUTUBE PREMIUM SUBSCRIPTION/{handle}",
        "POS {card} CINEPOLIS CINEMAS MOVIE {city}",
        "UPI/{ref}/SONY LIV OTT STREAMING/{handle}",
        "UPI/{ref}/ZEE5 ENTERTAINMENT SUBSCRIPTION/{handle}",
        "POS {card} FUN GAMING ARCADE {city}",
        "UPI/{ref}/THEATRE DRAMA PASS/{handle}",
        "UPI/{ref}/CONCERT MUSIC TICKETS/{handle}",
        "POS {card} COMEDY CLUB TICKETS {city}",
        "UPI/{ref}/VIDEO ON DEMAND MEDIA/{handle}",
    ],
    "Health": [
        "POS {card} APOLLO PHARMACY MEDICALS {city}",
        "UPI/{ref}/TATA 1MG HEALTH PHARMACY/{handle}",
        "UPI/{ref}/PHARMEASY MEDICINE ORDER/{handle}",
        "POS {card} MEDPLUS MEDICAL STORE PHARMACY {city}",
        "UPI/{ref}/NETMEDS ONLINE PHARMACY/{handle}",
        "DR LAL PATHLABS DIAGNOSTICS BLOOD TEST {ref}",
        "METROPOLIS HEALTHCARE LAB TESTING {ref}",
        "POS {card} MAX SUPER SPECIALITY HOSPITAL CLINIC",
        "POS {card} FORTIS HEALTHCARE CLINIC HOSPITAL",
        "UPI/{ref}/PRACTO DOCTOR CONSULTATION/{handle}",
        "DENTAL CLINIC DOCTOR TREATMENT {city}",
        "CITY CARE HOSPITAL CLINIC APPOINTMENT {ref}",
        "POS {card} PATHOLOGY LABORATORY SCANS {city}",
        "UPI/{ref}/POLY CLINIC CONSULTATION/{handle}",
        "POS {card} AYURVEDIC MEDICAL STORE {city}",
        "POS {card} WELLNESS PHYSIO CENTRE {city}",
        "EYE HOSPITAL SURGERY CLINIC {city}",
    ],
    "Travel": [
        "IRCTC RAILWAY TRAIN TICKETING DELHI {ref}",
        "UPI/{ref}/MAKEMYTRIP FLIGHT HOTEL BOOKING/{handle}",
        "UPI/{ref}/GOIBIBO TRAVEL HOTEL FLIGHTS/{handle}",
        "UPI/{ref}/EASEMYTRIP TICKETS AIRLINE/{handle}",
        "INDIGO AIRLINES FLIGHT TICKET BOOKING {ref}",
        "AIR INDIA TICKET FLIGHT BOOKING {ref}",
        "SPICEJET FLIGHT RESERVATION AIRLINE {ref}",
        "UPI/{ref}/YATRA ONLINE TRAVEL TOUR/{handle}",
        "VISTARA AIRLINE TICKETING FLIGHT {ref}",
        "UPI/{ref}/CLEARTRIP TRAVEL FLIGHTS/{handle}",
        "BOOKING COM HOTEL RESORT RESERVATION {ref}",
        "AGODA HOTEL BOOKING RESORT STAY {ref}",
        "AIRBNB VACATION STAY BOOKING {ref}",
        "UPI/{ref}/REDBUS BUS TICKETS TRAVEL/{handle}",
        "HOTEL SEASIDE RESORT STAY {city}",
        "UPI/{ref}/VACATION HOMESTAY BOOKING/{handle}",
        "POS {card} PALACE RESORT HOTEL {city}",
        "UPI/{ref}/AIRFARE FLIGHT TICKETING/{handle}",
        "HERITAGE COTTAGES STAY BOOKING {ref}",
        "TOUR OPERATOR HOLIDAY DESK {city}",
    ],
    "ATM Withdrawal": [
        "ATM WDL SBI ATM CASH WITHDRAWAL PUNE {ref}",
        "ATM WDL HDFC BANK ATM CASH MG ROAD {ref}",
        "ATM CASH WITHDRAWAL ICICI BANK ATM {ref}",
        "NFS WDL AXIS BANK ATM CASH {ref}",
        "CASH WDL KOTAK BANK ATM MONEY {ref}",
        "ATM WDL CANARA BANK CASH DISPENSER {ref}",
        "ATM CASH DISPENSER MACHINE {ref}",
        "AUTOMATED TELLER MACHINE CASHOUT {ref}",
        "ATM WITHDRAWAL POINT CASH {ref}",
    ],
    "Transfer": [
        "IMPS-{ref}-SELF TRANSFER TO SAVINGS ACC-{ifsc}",
        "FUND TRANSFER TO ACC 501002345678 SELF",
        "TRF TO LINKED SAVINGS ACCOUNT {ref}",
        "TRF FROM PARENT ACCOUNT TRANSFER {ref}",
        "IMPS-{ref}-PRIYA SHARMA-FAMILY SUPPORT-{ifsc}",
        "FUNDS TRF TO PPF ACCOUNT TRANSFER {ref}",
        "P2P REMITTANCE TO FAMILY MEMBER {ref}",
        "OUTWARD WIRE TRANSFER BENEFICIARY {ref}",
        "DOMESTIC MONEY TRANSFER TO ACC {ref}",
        "EXPENSE SETTLEMENT SHARE RECOVERY {ref}",
    ],
    "Cash Deposit": [
        "CHQ DEP-005512-CLEARING CHEQUE MUMBAI",
        "CDM CASH DEPOSIT MACHINE SBI CASH {ref}",
        "BY CASH DEPOSIT BRANCH COUNTER MONEY {ref}",
        "CHEQUE DEPOSIT IN CLEARING CHQ {ref}",
        "CASH DEP AT BRANCH COUNTER {city}",
        "TELLER DESK CASH DEPOSIT COUNTER {ref}",
        "CASH RECYCLER MACHINE DEPOSIT {ref}",
        "BRANCH CASH IN VAULT CREDIT {ref}",
    ],
    "Interest": [
        "INT PD 01-01-2025 TO 31-03-2025 SAVINGS",
        "INT.PD SAVINGS BANK INTEREST CREDIT {ref}",
        "SAVINGS ACCOUNT QUARTERLY INTEREST CREDIT",
        "FD INTEREST CREDIT FIXED DEPOSIT RETURN {ref}",
        "TERM DEPOSIT MONTHLY INTEREST PAYOUT {ref}",
        "DEPOSIT REVENUE ACCRUAL PAYOUT {ref}",
        "ANNUAL YIELD DIVIDEND CREDIT {ref}",
        "SAVINGS REVENUE ACCRUAL QUARTER {ref}",
    ],
    "Fees & Charges": [
        "SMS CHRG INCL GST QUARTER END CHARGES",
        "ANNUAL DEBIT CARD MAINTENANCE CHARGE FEE",
        "CONSOLIDATED CHARGES FOR LEDGER FEE",
        "CHEQUE BOOK ISSUANCE CHARGE FEE INCL GST",
        "PENALTY CHARGE NON MAINTENANCE MIN BAL FEE",
        "GST ON BANK CHARGES RECOVERED FEE",
        "CHEQUE RETURN BOUNCE PENALTY LEVY",
        "DOCUMENTATION PROCESSING FEE RECOVERED",
        "ADMINISTRATIVE SERVICE TARIFF LEVIED",
        "STOP PAYMENT INSTRUCTION CHARGE",
    ],
    "Refund": [
        "REFUND FROM AMAZON PAY RETURN {ref}",
        "REVERSAL OF FAILED UPI TXN MONEY {ref}",
        "REFUND FLIPKART ORDER CANCELLED RETURN {ref}",
        "CASHBACK RECEIVED CRED REWARDS BONUS {ref}",
        "CHARGEBACK REVERSAL FOR DISPUTED POS {ref}",
        "CANCELLED BOOKING REFUND PROCESSED {ref}",
        "RETURNED GOODS REIMBURSEMENT CREDIT {ref}",
        "DISPUTED SETTLEMENT REFUND REVERSED {ref}",
    ],
    "Other": [
        "MISCELLANEOUS SUNDRY EXPENSES {ref}",
        "UNKNOWN MERCHANT X9872 CODE {ref}",
        "GENERAL STORE MISC ITEMS {city}",
        "COMMUNITY CHARITY DONATION {ref}",
        "TEMPORARY ADJUSTMENT ENTRY {ref}",
        "CLEARING SUSPENSE ESCROW ENTRY {ref}",
        "MEMORANDUM NON OPERATIONAL ADJUSTMENT {ref}",
        "UNALLOCATED PROVISIONAL VOUCHER {ref}",
    ],
}

IFSC_CODES = ["HDFC0001234", "ICIC0000001", "SBIN0004321", "UTIB0000543", "KKBK0000123"]
HANDLES = ["okaxis", "okhdfcbank", "oksbi", "okicici", "paytm", "ybl"]
CITIES = ["MUMBAI", "PUNE", "BANGALORE", "DELHI", "HYDERABAD", "CHENNAI", "KOLKATA"]
MONTHS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN"]


def generate_training_data(n_samples: int = 500) -> pd.DataFrame:
    """Generate realistic synthetic bank transaction descriptions with labels."""
    random.seed(42)
    rows: list[dict[str, str]] = []

    for category, templates in CATEGORY_TEMPLATES.items():
        reps = max(2, (n_samples // (len(CATEGORY_TEMPLATES) * len(templates))) + 2)
        for _ in range(reps):
            for tmpl in templates:
                ref = str(random.randint(100000000000, 999999999999))
                card = f"{random.randint(4000, 5999)}XXXXXXXX{random.randint(1000, 9999)}"
                city = random.choice(CITIES)
                ifsc = random.choice(IFSC_CODES)
                handle = random.choice(HANDLES)
                month = random.choice(MONTHS)

                desc = tmpl.format(
                    ref=ref,
                    card=card,
                    city=city,
                    ifsc=ifsc,
                    handle=handle,
                    month=month,
                )

                # Random casing variations
                case_choice = random.random()
                if case_choice < 0.2:
                    desc = desc.lower()
                elif case_choice < 0.4:
                    desc = desc.title()

                rows.append({"description": desc, "category": category})

    df = pd.DataFrame(rows).drop_duplicates(subset=["description"])
    return df


def train_model(
    csv_path: str | Path | None = None,
    model_path: str | Path | None = None,
) -> float:
    """Train character n-gram TF-IDF + LogisticRegression classifier and save to disk."""
    csv_file = Path(csv_path) if csv_path else CSV_PATH
    model_file = Path(model_path) if model_path else MODEL_PATH

    csv_file.parent.mkdir(parents=True, exist_ok=True)
    model_file.parent.mkdir(parents=True, exist_ok=True)

    if not csv_file.exists():
        df = generate_training_data(n_samples=450)
        df.to_csv(csv_file, index=False)
    else:
        df = pd.read_csv(csv_file)

    # Pre-clean descriptions
    x_clean = [clean_description(str(d))["cleaned"] for d in df["description"]]
    y = df["category"]

    x_train, x_test, y_train, y_test = train_test_split(
        x_clean, y, test_size=0.2, random_state=42, stratify=y
    )

    pipeline = Pipeline([
        ("tfidf", TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 4), sublinear_tf=True, min_df=1)),
        ("clf", LogisticRegression(max_iter=1000, C=10.0, random_state=42)),
    ])

    pipeline.fit(x_train, y_train)

    y_pred = pipeline.predict(x_test)
    accuracy = float(accuracy_score(y_test, y_pred))

    joblib.dump(pipeline, model_file)
    print(f"Trained model on {len(x_train)} samples, held-out test accuracy: {accuracy:.1%}")
    return accuracy


if __name__ == "__main__":
    train_model()
