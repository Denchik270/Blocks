import pyrebase

firebase_config = {
    "apiKey": "API_КЛЮЧ_ОТСЮДА",
    "authDomain": "project-id.firebaseapp.com",
    "databaseURL": "https://project-id.firebaseio.com",
    "projectId": "project-id",
    "storageBucket": "project-id.appspot.com",
    "messagingSenderId": "xxx",
    "appId": "xxx"
}

firebase = pyrebase.initialize_app(firebase_config)
db = firebase.database()
