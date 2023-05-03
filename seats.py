from selenium import webdriver
from selenium.webdriver.common.by import By
from datetime import datetime, timedelta
import pandas as pd
import os
import pickle
import urllib.request
import json

#https://www.andressevilla.com/running-chromedriver-with-python-selenium-on-heroku/
chrome_options = webdriver.ChromeOptions() #"CHROMEDRIVER_VERSION"
chrome_options.binary_location = os.environ.get("GOOGLE_CHROME_BIN")
chrome_options.add_argument("--headless")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument('--disable-gpu')
driver = webdriver.Chrome(executable_path=os.environ.get("CHROMEDRIVER_PATH"), chrome_options=chrome_options)

# setup the driver
#from webdriver_manager.chrome import ChromeDriverManager
#from selenium.webdriver.chrome.service import Service
#s=Service(ChromeDriverManager().install())
#driver = webdriver.Chrome(service=s)
#driver.maximize_window()
#driver.implicitly_wait(10);

# Now you can start using Selenium

def get_seats(date):
    t_year = str(date.year)

    if date.month >= 10:
        t_month = str(date.month)
    else:
        t_month = "0" + str(date.month)

    if date.day >= 10:
        t_day = str(date.day)
    else:
        t_day = "0" + str(date.day)
    
    driver.implicitly_wait(10);
    driver.get("https://www.eventcinemas.com.au/Sessions#cinemas=64&exp=GC&date=" + t_year + "-" + t_month+ "-"+ t_day);
    
    sess_list = []
    movies = driver.find_elements(By.XPATH, "//*[@class='movie-list-item movie-container-item']")

    if (len(movies) == 0):
        return "unconfirmed", False
    
    for i in range(len(movies)):
        movies_list = driver.find_elements(By.XPATH, "//*[@class='movie-list-item movie-container-item']")
        m = movies_list[i]
        m_name = m.get_attribute('data-name')
        print("MOVIE NAME: ", m_name)


        #get runtime of movie
        print("//*[@data-name='"+m_name+"']/div[2]/div/a")
        driver.find_element(By.XPATH, '//*[@data-name="'+m_name+'"]/div[2]/div/a').click()
        print("CURRENT RUNTIME INVESTIIGATION FOR THIS MOVIE: ", driver.current_url)
        desktop_elements = driver.find_elements(By.XPATH, "//*[@class='prop ']/span")
        text_elements = driver.find_elements(By.XPATH, "//*[@class='prop ']/p")
        runtime = 120
        release_date = -1
        cinema=-1
        freshness=False
        if (len(desktop_elements) > 0):
            for i, element in enumerate(desktop_elements):
                print(element.text)
                print(text_elements[i].text)
                if (element.text == "Running Time:"):
                    runtime = int(text_elements[i].text[0:3])
                    cinema=0
                if (element.text == "Release Date:"):
                    release_date_str = text_elements[i].text
                    release_date = datetime.strptime(release_date_str, "%d/%m/%Y")
              
        driver.back()

        # once movie is isolated, determine which data-screentype=GC elements are present
        sessions = driver.find_elements(By.XPATH, 
        '//*[@data-name="'+m_name+'"]/div[2]/div[2]/div[1]/div/*[@data-screentype="GC"]')

        #details for session
        for sess in sessions:
            sess_yr = int(sess.get_attribute("data-time")[0:4])
            sess_mth = int(sess.get_attribute("data-time")[5:7])
            sess_day = int(sess.get_attribute("data-time")[8:10])
            sess_hr = int(sess.get_attribute("data-time")[11:13])
            sess_min = int(sess.get_attribute("data-time")[14:17])
            sess_time = datetime(sess_yr, sess_mth, sess_day, sess_hr, sess_min)
            end_time = sess_time + timedelta(minutes=runtime)

            freshness = (sess_time-release_date <= timedelta(days=7))

            seats = int(sess.get_attribute("data-seatsavailable"))

            sess_row = {"session_time":sess_time, "end_time":end_time, "cinema":cinema, "movie":m_name, "runtime":runtime, "new_release":freshness, "seats_available":seats}
            sess_list.append(sess_row)
            print("*SESSION DETAILS*", sess_row)

    df = pd.DataFrame(sess_list)
    df.sort_values("session_time", inplace=True)
    df.reset_index(inplace=True)
    df.drop(["index"], axis=1, inplace=True)
    df.loc[0, "cinema"] = 1
    df['taken_percent'] = 1-df['seats_available']/40
    df0 = df.copy()

    # cinema1 and cinema2 split
    df1 = pd.DataFrame().add(df.loc[0])
    df2 = pd.DataFrame().add(df.loc[0])

    df1 = pd.concat([df1,pd.DataFrame(df.loc[0]).T])
    df.drop(0,inplace=True)
    curr_end = df1.iloc[-1]['end_time']
    for i, row in df.iterrows():
        next_end = df.loc[i, "session_time"]
        curr_end_min  = curr_end + timedelta(minutes = 19)
        curr_end_max =  curr_end + timedelta(minutes = 55)
        print(next_end, curr_end_min, curr_end_max)
        if (curr_end_min <= next_end and curr_end_max >= next_end):
            df1 = pd.concat([df1,pd.DataFrame(df.loc[i]).T])
            df.drop(i, inplace=True)
            curr_end = df1.iloc[-1]['end_time']

    df2 = pd.DataFrame().add(df.iloc[0])
    df2 = pd.DataFrame().add(df.iloc[0])
    df2 = pd.concat([df2,pd.DataFrame(df.iloc[0]).T])
    df.drop(1,inplace=True)
    curr_end = df2.iloc[0]['end_time']
    for i, row in df.iterrows():
        next_end = df.loc[i, "session_time"]
        curr_end_min  = curr_end + timedelta(minutes = 19)
        curr_end_max =  curr_end + timedelta(minutes = 55)
        print(next_end, curr_end_min, curr_end_max)
        if (curr_end_min <= next_end and curr_end_max >= next_end):
            df2 = pd.concat([df2,pd.DataFrame(df.loc[i]).T])
            df.drop(i, inplace=True)
            curr_end = df2.iloc[-1]['end_time']
    
    #is there a function on
    function = False
    if (df1.iloc[0]['session_time'].weekday()>=5):
        if (df2.shape[0] - df1.shape[0] > 0):
            pd.concat([df1,df])
            function=True
        elif (df1.shape[0] - df2.shape[0] > 0):
            pd.concat([df2,df])
            function=True
        else:
            pd.concat([df1,df])
    else:
        if (df2.shape[0] - df1.shape[0] > 1):
            pd.concat([df1,df])
            function=True
        elif (df1.shape[0] - df2.shape[0] > 1):
            pd.concat([df2,df])
            function=True
        else:
            pd.concat([df1,df])

    df = pd.concat([df1,df2])
    print("CNT", df0)
    return df0, function

def match_nsw_holiday(date, year):
    nsw_holidays = {
    "New Year's Day": (1, 1),
    "Australia Day": (1, 26),
    "Good Friday": None,
    "Easter Monday": None,
    "Anzac Day": (4, 25),
    "Queen's Birthday": relativedelta(month=6, day=1, weekday=MO(+2)),
    "Bank Holiday": relativedelta(month=8, day=1, weekday=MO),
    "Christmas Day": (12, 25),
    "Boxing Day": (12, 26)
    }
    holidays = []
    
    for name, date_or_rule in nsw_holidays.items():
        if date_or_rule is not None:
            month, day = date_or_rule
            holiday_date = datetime.date(year, month, day)
        else:
            holiday_date = easter(year) + dateutil.relativedelta.relativedelta(**date_or_rule)
        holidays.append((name, holiday_date))
        
    for holiday in holidays:
        if (date == holiday):
            return True
    
    return False

def weather_pred(target_date):
    try:
        api_key="6ffb5271db4b5ca4290007c711567ad9"
        city = "Sydney"
        country_code = "au"
        unix_timestamp = target_date.timestamp()
        url = f"https://api.openweathermap.org/data/2.5/weather?q={city},{country_code}&dt={unix_timestamp}&appid={api_key}"

        response = urllib.request.urlopen(url)
        data = json.loads(response.read())
        weather_prediction=data['weather'][0]['main']
        
        if (weather_prediction == "Clear"):
            return 0
        elif (weather_prediction == "Clouds" | weather_prediction == "Fog" | weather_prediction == "Haze"):
            return 1 
        else: 
            return 2

    except Error:
        return 0;

class have_seats():
    def __init__(self):
        pass
    
    def grab(switch):
        df, function = get_seats(switch)
        return df, function

class change_datetime():
    def __init__(self):
        pass
    
    def change(switch_str):
        date_str = switch_str['date']
        switch_str['date'] = datetime(year=int(date_str[0:4]),
                                            month=int(date_str[5:7]),
                                            day=int(date_str[8:10]))
        
        start_str = switch_str['start_time']
        switch_str['start_time'] = datetime(year=int(date_str[0:4]),
                                            month=int(date_str[5:7]),
                                            day=int(date_str[8:10]),
                                            hour=int(start_str[0:2]), 
                                            minute=int(start_str[3:5]))
        end_str = switch_str['end_time']
        switch_str['end_time'] = datetime(year=int(date_str[0:4]),
                                            month=int(date_str[5:7]),
                                            day=int(date_str[8:10]),
                                            hour=int(end_str[0:2]), 
                                            minute=int(end_str[3:5]))
        return switch_str
    
    def time_until(switch):
        time_til_shift = (switch['start_time'] - datetime.now())
        time_until_str = "There are still " + str(time_til_shift.days) + " days and " + str(round(time_til_shift.seconds/60/60))  + " hours until your shift. "
        return time_until_str
    
class model():
    def __init__(self):
        pass
    
    def make_model(switch, df, function):
        
        shift_run=0
        shift_super=0
        shift_kitchen=0

        if (switch['shift']=="gck"):
            shift_kitchen=1
        elif (switch['shift']=="gcb"):
            shift_run=1
        elif (switch['shift']=="gcr"):
            shift_run=1
        elif (switch['shift']=="gch"):
            shift_run=1
        elif (switch['shift']=="gcs"):
            shift_super=1

        weather= weather_pred(switch['start_time'])
    
        if (switch['cut']=='yes'):
            already_cut = 1
        elif (switch['cut']=='no'):
            already_cut = 0

        pre_sale_high = df['taken_percent'].mean()

        time_until_shift = (switch['start_time'] - datetime.now()).total_seconds()/3600

        day_of_week = switch['start_time'].weekday()

        public_holiday = match_nsw_holiday(switch['date'],switch['date'].year)

        if (switch['school_holidays']=='yes'):
            school_holiday = 1
        elif (switch['school_holidays']=='no'):
            school_holiday = 0
            
        freshness=int(df['new_release'].max())

        hours=(switch['start_time'] - switch['end_time']).total_seconds()/3600

        data_row = [shift_run, shift_super, shift_kitchen, weather, already_cut, pre_sale_high, 
                    time_until_shift, day_of_week, public_holiday, school_holiday, freshness, hours]

        loaded_model = pickle.load(open('model.pkl', 'rb'))
        
        chance = loaded_model.predict([data_row])
        return "There is a "+str(chance)[1:5]+"% chance that your shift could be cut. Hugs and Kisses!!! C:"
