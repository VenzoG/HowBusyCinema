from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from datetime import datetime, timedelta
import pandas as pd
import os

chrome_options = webdriver.ChromeOptions()
chrome_options.binary_location = os.environ.get("GOOGLE_CHROME_BIN")
chrome_options.add_argument("--headless")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--no-sandbox")
driver = webdriver.Chrome(executable_path=os.environ.get("CHROMEDRIVER_PATH"), chrome_options=chrome_options)

# Now you can start using Selenium

def get_seats(date):
    t_year = str(date.year)

    if date.month > 10:
        t_month = str(date.month)
    else:
        t_month = "0" + str(date.month)

    t_day = str(date.day)
    
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
        cinema=-1
        if (len(desktop_elements) > 0):
            for i, element in enumerate(desktop_elements):
                print(element.text)
                print(text_elements[i].text)
                if (element.text == "Running Time:"):
                    runtime = int(text_elements[i].text[0:3])
                    cinema=0
                    break
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

            seats = int(sess.get_attribute("data-seatsavailable"))

            sess_row = {"session_time":sess_time, "end_time":end_time, "cinema":cinema, "movie":m_name, "runtime":runtime, "seats_available":seats}
            sess_list.append(sess_row)
            print("*SESSION DETAILS*", sess_row)

    df = pd.DataFrame(sess_list)
    df.sort_values("session_time", inplace=True)
    df.reset_index(inplace=True)
    df.drop(["index"], axis=1, inplace=True)
    df.loc[0, "cinema"] = 1
    df['taken_percent'] = 1-df['seats_available']/40
    curr_sess=0
    

    
    while (df['cinema'].min() == 0):
        # start with cinema 1 stream
        if (df['cinema'].value_counts()[1] == 1):
            print("CURR CINEMA = 1")
            curr_cinema=1 
        # else, understand the cinema 2 stream
        else:
            print("CURR CINEMA = 2")
            curr_cinema=2
            # find un assigned cinema row
            for row in df.iterrows():
                if (row[1]['cinema']==1):
                    continue
                else:
                    print("CURR_SESS = ", row[0])
                    curr_sess = row[0]
                    df.loc[row[0], 'cinema'] = curr_cinema
                    break

        while (curr_sess != -1):
            # determine cleaning period and likelihood of next session
            print("DETERMINING NEW SET")
            new_assign=0
            curr_end = df.loc[curr_sess, "end_time"]
            curr_end_min  = curr_end + timedelta(minutes = 19)
            curr_end_max =  curr_end + timedelta(minutes = 45)
            # check in rows where the cinema is not equal to 0
            for row in df[df['cinema']==0].iterrows():
                print("CHECKING ROW")
                next_end = row[1]['session_time']
                print(curr_end_min, curr_end_max)
                print(next_end)
                if (curr_end_min < next_end and curr_end_max > next_end):
                    print("*CINEMA CHANGE*")
                    df.loc[row[0], 'cinema'] = curr_cinema
                    curr_sess = row[0]
                    new_assign=1
                    break

            # if we cannot find a row to assign a new session, break
            if (new_assign==0):
                curr_sess=-1
                print("CANNOT FIND NEW SET")

        curr_sess = 0 
        while (curr_sess != -1):
        # determine cleaning period and likelihood of next session
            print("DETERMINING NEW SET WITH EXPANDED PARAMETERS FOR CLEANUP OF SPARES")
            new_assign=0
            # these are the changed lines of code
            curr_end = df[df['cinema']==0].iloc[curr_sess]["end_time"]
            curr_cinema = df.loc[(df[df['cinema']==0].index[0]-1), 'cinema']
            if (curr_cinema == 1):
                curr_cinema=2
            elif (curr_cinema == 2):
                curr_cinema=1
            print("****Cinema*******", curr_cinema)

            curr_end_min  = curr_end + timedelta(minutes = 20)
            curr_end_max =  curr_end + timedelta(minutes = 70)
            # check in rows where the cinema is not equal to 0 for proceeding session
            for row in df.iterrows():
                print("CHECKING ROW")
                next_end = row[1]['session_time']
                print(curr_end_min, curr_end_max)
                print(next_end)
                if (curr_end_min < next_end and curr_end_max > next_end):
                    print("*CINEMA CHANGE OF PREVIOUSLY BLANK ROW*")
                    df.loc[df[df['cinema']==0].index[0], 'cinema'] = curr_cinema
                    if (len(df[df['cinema']==0]) != 0):
                        new_assign=1
                    break

        # determine cleaning period and likelihood of previous session
            print("DETERMINING NEW SET WITH EXPANDED PARAMETERS FOR CLEANUP OF SPARES - PREVIOUS SESSION MATCH")
            new_assign=0
            # these are the changed lines of code
            curr_end = df[df['cinema']==0].iloc[curr_sess]["session_time"]
            curr_cinema = df.loc[(df[df['cinema']==0].index[0]-1), 'cinema']
            if (curr_cinema == 1):
                curr_cinema=2
            else:
                curr_cinema=1
            print("****Cinema*******", curr_cinema)

            curr_end_min  = curr_end + timedelta(minutes = 20)
            curr_end_max =  curr_end + timedelta(minutes = 70)

            # check in rows where cinema is assigned for preceeding session
            for row in df.iterrows():
                print("CHECKING ROW")
                next_end = row[1]['end_time']
                print(curr_end_min, curr_end_max)
                print(next_end)
                if (curr_end_min < next_end and curr_end_max > next_end):
                    print("*CINEMA CHANGE OF PREVIOUSLY BLANK ROW*")
                    df.loc[df[df['cinema']==0].index[0], 'cinema'] = curr_cinema
                    if (len(df[df['cinema']==0]) != 0):
                        new_assign=1
                    break

            # if we cannot find a row to assign a new session, break
            if (new_assign==0):
                curr_sess=-1
                print("CANNOT FIND NEW SET")
    
    #is there a function on
    prev_cinema = 2
    function = False
    for row in df.iterrows():
        if (prev_cinema != row[1]['cinema']):
            prev_cinema = row[1]['cinema']
        else:
            print("DISCREPENCY DETECTED")
            print("There may be a private session, two consecutive sessions are located in the same cinema.")
            function = True
    
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

        return "[Placeholder! Percentage predictive model isn't done yet.]"
