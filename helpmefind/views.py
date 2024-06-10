from django.shortcuts import render
from django.core.files.storage import FileSystemStorage
from django.http import HttpResponse

from .models import symptoms,cities

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.neighbors import KNeighborsClassifier
from sklearn import preprocessing 
from django.conf import settings
import requests
import json
import math
import joblib

findSpecialist = joblib.load('C:/Users/Admin/OneDrive - St. Clair College/Documents/DAB/DAB304 Lecture/Healthcare Group Project/helpme/helpmefind/findSpecialist.joblib')
label_encoder = joblib.load('C:/Users/Admin/OneDrive - St. Clair College/Documents/DAB/DAB304 Lecture/Healthcare Group Project/helpme/helpmefind/findSpecialistlabel.joblib')

def Specialty(test): 
    SpecialitiesCountDf = pd.read_csv("C:/Users/Admin/OneDrive - St. Clair College/Documents/DAB/DAB304 Lecture/Healthcare Group Project/SpecialitiesCountDf.csv")
    label_encoder = preprocessing.LabelEncoder() 
    # Encode labels in column 'species'. 
    SpecialitiesCountDf['Specialty']= label_encoder.fit_transform(SpecialitiesCountDf['Specialty']) 
    y = SpecialitiesCountDf["Specialty"]
    X = SpecialitiesCountDf.drop(["Specialty"], axis=1)
    X = X.reindex(sorted(X.columns), axis=1)
#    X[X != 0] = 1
    X_train, X_test, Y_train, Y_test = train_test_split(X, y,  test_size=0.2)
    classifier = KNeighborsClassifier(n_neighbors = 5, metric="jaccard")
    classifier.fit(X_train, Y_train)
    X_test = pd.DataFrame(test) # [{"cough":1,"fever":1,"painful breathing":1,"chill":1,"excessive thirst":1}]
    X_test[X_train.columns[~X_train.columns.isin(X_test.columns)]] = 0
    X_test = X_test.reindex(sorted(X_test.columns), axis=1)
    return label_encoder.inverse_transform(classifier.predict(X_test))

def join_strings(data, chunk_size):
    joined_strings = []
    for i in range(0, len(data), chunk_size):
        joined_strings.append('|'.join(data[i:i+chunk_size]))
    return joined_strings

def getDocList(pred,city, origin):
    df = pd.read_csv("C:/Users/Admin/OneDrive - St. Clair College/Documents/DAB/DAB304 Lecture/Healthcare Group Project/helpme/helpmefind/docList.csv")
    df = df[(df["pri_spec"]==pred)&(df["City/Town"]==city)]
    df["ZIP Code"] = df["ZIP Code"].astype('str').str[:5]
    zipUnique = df["ZIP Code"].unique()
    destinations = join_strings(zipUnique, 25)
    responses = []
    aPI_Key = __YOUR GOOGLE API KEY__
    for d in destinations:
        x = requests.get("https://maps.googleapis.com/maps/api/distancematrix/json?origins="+origin+"&destinations="+d+"&units=imperial&key="+aPI_Key)
        responses.append(json.loads(x.text))
    distanceDict = {"ZIP Code":[], "Distance":[],"Duration":[]}
    for response in responses:
        distanceDict["ZIP Code"].append(list(pd.Series(response["destination_addresses"]).str.split(",").str[1].str.split(" ").str[-1].str.lstrip().str.rstrip()))
        for row in response["rows"][0]["elements"]:
            try:
                distanceDict["Distance"].append(row["distance"]["text"].split(" ")[0])
                distanceDict["Duration"].append(row["duration"]["text"].split(" ")[0])
            except:
                distanceDict["Distance"].append(np.nan)
                distanceDict["Duration"].append(np.nan)
    distanceDict["ZIP Code"] = [item for sublist in distanceDict["ZIP Code"] for item in sublist]
    distanceDf = pd.DataFrame(distanceDict)
    distanceDf = distanceDf.dropna()
    mergedDf = df.merge(distanceDf, on = "ZIP Code")
    mergedDf["Distance"] = mergedDf["Distance"].astype("float")
    mergedDf["Duration"] = mergedDf["Duration"].astype("float")
    mergedDf.sort_values(by=["Distance","Duration"], inplace=True)
    return mergedDf

    
def find_doctor(request):  
    symps = symptoms.objects.all()
    listSymps = []
    for symp in symps:
        listSymps.append(symp.symptom)
    citie = cities.objects.all()
    listCity = []
    for ci in citie:
        listCity.append(ci.city)
    if request.method == 'POST':
        listSelectedSympt = []
        for i in range(5):
            i = i+1
            temp = "select"+str(i)
            listSelectedSympt.append(request.POST.get(temp))
        test = [{key: 1 for key in listSelectedSympt}]
        X_test = pd.DataFrame(test) # [{"cough":1,"fever":1,"painful breathing":1,"chill":1,"excessive thirst":1}]
        columns = np.setdiff1d(listSymps,list(X_test.columns))
        X_test[columns] = 0
        X_test.columns = X_test.columns.astype(str)
        X_test = X_test.reindex(sorted(X_test.columns), axis=1)
        pred = label_encoder.inverse_transform(findSpecialist.predict(X_test))
        city = request.POST.get("select6")
        origin = request.POST.get("zipcode")
#        df = pd.read_csv("C:/Users/Admin/OneDrive - St. Clair College/Documents/DAB/DAB304 Lecture/Healthcare Group Project/helpme/helpmefind/docList.csv")
#        df = df[(df["pri_spec"]==pred[0])&(df["City/Town"]==city)]
        df = getDocList(pred[0],city, origin)
        df1 = df.head(10)
        csv_data = df.to_csv(str(settings.BASE_DIR)+"/media/fullData.csv",index=False)
        top_csv_data = df1.to_csv(str(settings.BASE_DIR)+"/media/data.csv",index=False)
        response1 = HttpResponse(csv_data,content_type='text/csv')
        response1['Content-Disposition'] = 'attachment; filename="data.csv"'
        response2 = HttpResponse(top_csv_data,content_type='text/csv')
        response2['Content-Disposition'] = 'attachment; filename="data.csv"'
#        response.write(csv_data)
        return render(request, 'index.html', {'listSymps': listSymps, 'listCity': listCity, 'pred': pred[0], 'response2': '/media/fullData.csv', 'response1': '/media/data.csv'})

    else:
        return render(request, 'index.html',{"listSymps":listSymps,"listCity":listCity})
    return render(request, 'index.html',{"listSymps":listSymps})
