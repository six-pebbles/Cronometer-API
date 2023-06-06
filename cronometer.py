import requests
from bs4 import BeautifulSoup
import re
import sqlite3

# The day or days to pull cronometer logs from
start_date = "2023-05-09"
end_date = "2023-05-09"

# Creds
username = '[your username here]'
password = '[your password here]'

# HTMLLoginURL is the full URL to the Cronometer login page.
HTMLLoginURL = "https://cronometer.com/login/"

# APILoginURL is the full URL for login requests.
APILoginURL = "https://cronometer.com/login"

# GWTBaseURL is the full URL for accessing the GWT API.
GWTBaseURL = "https://cronometer.com/cronometer/app"

# APIExportURL is the full URL for requesting data exports.
APIExportURL = "https://cronometer.com/export"

GWTHeader = "2D6A926E3729946302DC68073CB0D550"
GWTContentType = "text/x-gwt-rpc; charset=UTF-8"
GWTModuleBase  = "https://cronometer.com/cronometer/"
GWTPermutation = "7B121DC5483BF272B1BC1916DA9FA963"

def parse_csrf(html):
    soup = BeautifulSoup(html, 'html.parser')
    input_element = soup.find('input', {'name': 'anticsrf'})
    cookie_value = input_element['value']
    return cookie_value

def login_request(csrf_token, session): 
    form = {
        'anticsrf': csrf_token,
        'username': username,
        'password': password
    }
    #submit form to APILoginURL
    response = session.post(APILoginURL, data=form)
    print(response.text)
    return session

def gwt_request(session): 
    headers = {
        "content-type": GWTContentType,
        "x-gwt-module-base": GWTModuleBase,
        "x-gwt-permutation": GWTPermutation
    }

    GWTAuthenticate = "7|0|5|https://cronometer.com/cronometer/|" + GWTHeader + "|com.cronometer.shared.rpc.CronometerService|authenticate|java.lang.Integer/3438268394|1|2|3|4|1|5|5|-300|"
    response = session.post(GWTBaseURL, data=GWTAuthenticate, headers=headers)
    if "The call failed on the server; see server log for details" in response.text: 
        print("[-] Likely problem with headers, may need to update GWTHeader based on app version")
        return(False)
    user_id = re.search(r"\/\/OK\[(\d+),", response.text).group(1)
    print("userid =", user_id)
    return(user_id)

def generate_auth_token(session, user_id):
    for cookie in session.cookies:
        if cookie.name == "sesnonce":
            nonce = cookie.value
    GWTGenerateAuthToken = "7|0|8|https://cronometer.com/cronometer/|" + GWTHeader + "|com.cronometer.shared.rpc.CronometerService|generateAuthorizationToken" + "|java.lang.String/2004016611|I|com.cronometer.shared.user.AuthScope/2065601159|" + nonce + "|1|2|3|4|4|5|6|6|7|8|" + user_id + "|3600|7|2|"

    headers = {
        "content-type": GWTContentType,
        "x-gwt-module-base": GWTModuleBase,
        "x-gwt-permutation": GWTPermutation
    }

    GWTTokenRegex = r'"(?P<token>.*)"'
    response = session.post(GWTBaseURL, headers=headers, data=GWTGenerateAuthToken)
    auth_token = re.search(GWTTokenRegex, response.text).group(1)
    print("auth_token =", auth_token)
    return(auth_token)


def export_daily_nutrition(session, start_date, end_date, user_id): 
    token = generate_auth_token(session, user_id)

    headers = {
        "sec-fetch-dest": "document",
        "sec-fetch-mode": "navigate",
        "sec-fetch-site": "same-origin"
    }

    data = {
        "nonce": token,
        "generate": "dailySummary",
        "start": start_date,
        "end": end_date
    }
    # response = session.get(APIExportURL, data=data, headers=headers)
    formated_url = f"{APIExportURL}?nonce={token}&generate=dailySummary&start={start_date}&end={end_date}"
    response = session.get(formated_url, headers=headers)
    if response.status_code == 200:
        print(response.text)
        return(response.text)
    else:
        breakpoint()
    print(response.status_code)



def export_to_SQL(data):

    # Connect to database
    conn = sqlite3.connect('cronometer.db')
    c = conn.cursor()

    # Create table
    c.execute('''CREATE TABLE IF NOT EXISTS daily_intake
                (Date TEXT, Energy REAL, Alcohol REAL, Caffeine REAL, Water REAL, B1 REAL, B2 REAL, B3 REAL, B5 REAL, B6 REAL, B12 REAL, Folate REAL, Vitamin_A REAL, Vitamin_C REAL, Vitamin_D REAL, Vitamin_E REAL, Vitamin_K REAL, Calcium REAL, Copper REAL, Iron REAL, Magnesium REAL, Manganese REAL, Phosphorus REAL, Potassium REAL, Selenium REAL, Sodium REAL, Zinc REAL, Carbs REAL, Fiber REAL, Starch REAL, Sugars REAL, Added_Sugars REAL, Net_Carbs REAL, Fat REAL, Cholesterol REAL, Monounsaturated REAL, Polyunsaturated REAL, Saturated REAL, Trans_Fats REAL, Omega_3 REAL, Omega_6 REAL, Cystine REAL, Histidine REAL, Isoleucine REAL, Leucine REAL, Lysine REAL, Methionine REAL, Phenylalanine REAL, Protein REAL, Threonine REAL, Tryptophan REAL, Tyrosine REAL, Valine REAL, Completed TEXT)''')

    # Parse data and insert into table
    data = data.splitlines()[1]
    formatted_data = data.split(',')
    date = formatted_data[0]

    # Ensures there is only ever one row for each date
    c.execute("DELETE FROM daily_intake WHERE Date = ?", (date,))

    c.execute("INSERT INTO daily_intake VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                formatted_data)

    # Commit changes and close connection
    conn.commit()
    conn.close()




def main():
    s = requests.Session()
    response = s.get(HTMLLoginURL)
    if response.status_code == 200: 
        csrf_token = parse_csrf(response.text)
        print(csrf_token)
        s = login_request(csrf_token, s)
        user_id = gwt_request(s)
        data = export_daily_nutrition(s, start_date, end_date, user_id)
        export_to_SQL(data)

        
    
if __name__ == "__main__":
    main()