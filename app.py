from flask import Flask, request, jsonify, render_template
import pandas as pd
from datetime import timedelta

from seats import have_seats , change_datetime, model

app = Flask(__name__)

@app.route('/')
def home():
    print("We start the program here")
    return render_template('index.html')

@app.route('/predict',methods=['POST'])
def predict():
    print("Inside predict(). POST method success")
    switch_str = {"shift":request.form['shift'],
                  "date":request.form['date'],
                  "start_time":request.form['start_time'],
                  "end_time":request.form['end_time'],
                  "confirmation":request.form['confirmation'],
                  "cut":request.form['cut'] }
    switch = change_datetime.change(switch_str)
    # time_until string
    time_until_str = change_datetime.time_until(switch)
    
    # shift string
    if (switch['shift']=="gck"):
        shift_str = "You have a GC kitchen shift."
    elif (switch['shift']=="gcb"):
        shift_str = "You have a GC bar sales shift."
    elif (switch['shift']=="gcr"):
        shift_str = "You have a GC runner shift."
    elif (switch['shift']=="gch"):
        shift_str = "You have a GC host shift."
    elif (switch['shift']=="gcs"):
        shift_str = "You are a GC supervisor."
    
    #result string
    result_str = ""
    if (switch['shift'] == 'gcs'):
        result_str = result_str + "As a supervisor, it is less likely your shift will be cut. "
    elif (switch['confirmation'] == 'yes'):
        result_str = result_str + "As your shift has been confirmed, it is less likely your shift will be cut further. "
    elif (switch['cut'] == 'yes'):
        result_str = result_str + "As your shift has already been cut, it is less likely your shift will be cut further. "
    else:
        result_str = "Be wary! "
        
    result_str = result_str + "Here is the predictive percentage that your shift will be cut further:"
    
    df, function = have_seats.grab(switch['date'])
    
    if (type(df) == "str"):
        return render_template('prediction.html', time_til=(time_until_str))

    #remove all non-shift sessions of day
    print(type(df))
    print(df)
    print(type(switch))
    print(switch)
    df=df[(switch['start_time'] - timedelta(minutes=20)) < df['end_time']]
    df=df[switch['end_time'] > df['end_time']]
    
    movies_str = ["[Past or non-public session]"]*10
    for i, rows in df.iterrows():
        start_hr = str(rows['session_time'].hour)
        if (rows['session_time'].minute >= 10):
            start_min = str(rows['session_time'].minute)
        else:
            start_min = "0" + str(rows['session_time'].minute)
            
        end_hr = str(rows['end_time'].hour)
        if (rows['end_time'].minute >= 10):
            end_min = str(rows['end_time'].minute) 
        else:
            end_min = "0" + str(rows['end_time'].minute) 
        
        movies_str[i] = rows["movie"] + " " + start_hr + ":" + start_min + " - " + end_hr + ":" + end_min + ": "
        movies_str[i] = movies_str[i] + str(100*round(rows['taken_percent'],2))+ "%."

    # seats full string
    s_pc = 100*(sum(df['taken_percent'])/len(df['taken_percent']))
    seats_full_str = "Currently, there are " + str(round(s_pc,2)) + "% of seats booked in the sessions on during your shifts:"
    # percentage string
    percent_str = model.make_model(switch, df, function)

    return render_template('prediction.html', 
                           shift_type=(shift_str),
                           time_til=(time_until_str),
                           seats_full=(seats_full_str),
                           result=(result_str),
                           movies_0=(movies_str[0]),
                           movies_1=(movies_str[1]),
                           movies_2=(movies_str[2]),
                           movies_3=(movies_str[3]),
                           movies_4=(movies_str[4]),
                           movies_5=(movies_str[5]),
                           movies_6=(movies_str[6]),
                           movies_7=(movies_str[7]),
                           movies_8=(movies_str[8]),
                           movies_9=(movies_str[9]),
                           percent=(percent_str))


if __name__ == "__main__":
    app.run(debug=True)
