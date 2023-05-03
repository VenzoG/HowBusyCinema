from selenium import webdriver
from selenium.webdriver.common.by import By
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta, MO
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
    "Anzac Day": (4, 25),
    "Christmas Day": (12, 25),
    "Boxing Day": (12, 26),
    "Rolling Date Holiday": None
    }
    holidays = []
    
    for name, date_rule in nsw_holidays.items():
        if date_rule is not None:
            month, day = date_rule
            holiday_date = datetime(year, month, day)
            if (date.date() == holiday_date.date()):
                return True, name + "! Public Holiday! Happy penalty rates! \n"
        else:
            pass
            easter = is_easter(date.year)
            easter_sun = datetime(date.year, easter[0], easter[1])
            easter_sat = easter_sun - timedelta(days=1)
            easter_fri = easter_sun - timedelta(days=2)
            easter_mon = easter_sun + timedelta(days=1)
            if ((date.date() == easter_sun.date()) | (date.date() == easter_fri.date()) | 
                (date.date() == easter_sat.date()) | (date.date() == easter_mon.date()) ):
                return True, "Easter long weekend! No restaurants open on Friday or Sunday so be careful :( \n"
            
            queens_bday = datetime(date.year, 1, 1, 0, 0, 0) + relativedelta(month=6, weekday=MO(2))
            queens_bday_sun = queens_bday - timedelta(days=1)
            queens_bday_sat = queens_bday - timedelta(days=2)
            if (date.date() == queens_bday.date()):
                return True, "Queens Birthday Long Weekend! Long Live Queen (RuPaul) Charles! \n"
            
            bank_holiday = datetime(date.year, 1, 1, 0, 0, 0) + relativedelta(month=8, weekday=MO(1))
            bank_holiday 
            if (date.date() == bank_holiday.date()):
                return True, "Bank holiday long weekend! Where's all our money going anyways?.. \n"
            
    return False

def is_easter(year):
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = ((h + l - 7 * m + 114) % 31) + 1
    return month, day

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
        weather_temp = data['main']['feels_like']-273.15
        
        if (weather_prediction == "Clear" & weather_temp >= 20):
            return 0, "The weather is predicted for clear and warm. Beach weather and fewer ticket sales! \n"
        elif (weather_prediction == "Clouds" | weather_prediction == "Fog" | weather_prediction == "Haze" | weather_temp < 20):
            return 1, "The weather is predicted to be a bit down. Could go either way! \n"
        else: 
            return 2, "The weather is predicted to be shit. Sharknado-esque really. Leaks incoming. \n"

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
        result_str = ""
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

        weather, weather_str = weather_pred(switch['start_time'])
        result_str += weather_str
        
        if (switch['cut']=='yes'):
            already_cut = 1
        elif (switch['cut']=='no'):
            already_cut = 0

        pre_sale_high = df['taken_percent'].min()

        time_until_shift = (switch['start_time'] - datetime.now()).total_seconds()/3600

        day_of_week = switch['start_time'].weekday()
        if (day_of_week >= 4):
            result_str += "Your shift is on the weekend! It'll be a cold day at Hogwarts if you get cut. \n"
        else:
            result_str += "Weekday shift! A cut is more likely due to that. \n"

        public_holiday, public_str = match_nsw_holiday(switch['date'],switch['date'].year)
        result_str += public_str

        if (switch['school_holidays']=='yes'):
            school_holiday = 1
            result_str += "School holidays! Brace yourself... particularly for the daytime family movies... \n"
        elif (switch['school_holidays']=='no'):
            school_holiday = 0
            
        freshness=int(df['new_release'].max())
        
        if (freshness == 1):
            result_str += "Our records indicate a movie is in opening week during your shift! This makes it less likely you'll be cut.\n"

        hours=(switch['start_time'] - switch['end_time']).total_seconds()/3600

        data_row = [shift_run, shift_super, shift_kitchen, weather, already_cut, pre_sale_high, 
                    time_until_shift, day_of_week, public_holiday, school_holiday, freshness, hours]

        loaded_model = pickle.load(open('model.pkl', 'rb'))
        
        chance = loaded_model.predict([data_row])
        percent_str = "There is a "+str(chance)[1:6]+"% chance that your shift could be cut. Hugs and Kisses!!! C:"
        
        return percent_str, result_str
