from selenium import webdriver
from selenium.webdriver.common.by import By
from datetime import datetime, timedelta
import pandas as pd
import os

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
        runtime = -1
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
            pass
    else:
        if (df2.shape[0] - df1.shape[0] > 1):
            pd.concat([df1,df])
            function=True
        elif (df1.shape[0] - df2.shape[0] > 1):
            pd.concat([df2,df])
            function=True
        else:
            pass

    df = pd.concat([df1,df2])
    return df, function

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
        
        filename = 'finalized_model.sav'
        loaded_model = pickle.load(open(filename, 'rb'))

        chance = 100
        return "There is a "+str(chance)[0:5]+"% chance that your shift could be cut. Hugs and Kisses!!! C:"
