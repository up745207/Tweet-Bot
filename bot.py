from flask import Flask, render_template, flash, redirect, url_for
from config import Config
from forms import LoginForm
from google.cloud import vision
from google.cloud.vision import types
import datetime
import tweepy
import math
import io
import os

#Google API configuration files
os.environ["GOOGLE_APPLICATION_CREDENTIALS"]="apikey.json"

app = Flask(__name__)
app.config.from_object(Config)

consumer_key = 'x'
consumer_secret = 'x'
access_token = 'x'
access_token_secret = 'x'

auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
auth.set_access_token(access_token, access_token_secret)
api = tweepy.API(auth, wait_on_rate_limit=True, wait_on_rate_limit_notify=True)

global_name = "blank"
@app.route('/', methods=['GET', 'POST'])
def login(error=None):
    form = LoginForm()
    if form.validate_on_submit():
        return redirect(url_for('results', result_data = form.username.data))
    return render_template('login.html', title='Home', form=form)


@app.route("/results/<result_data>")
def results(result_data=None):
    global global_name
    u = api.get_user(screen_name=result_data)
    global_name = u.screen_name

    #***Account activity***
    ##Calculate number of days since account creation > total tweets > x = tweets per day
    delta = datetime.datetime.now() - u.created_at
    days = delta.days
    per_day = u.statuses_count / int(days)
    ### Probability Calculations, if 10% over average then high, within 10% up or down of average then medium, else low, twice as muc = very high
    avg = 22
    if per_day > (avg+(avg/10)):
        if per_day > avg*2:
            activity_outcome = "Very High"
            menu_1 = 'danger'
        else:
            activity_outcome = "High"
            menu_1 = 'warning'
    elif (avg-(avg/10)) <= per_day <= (avg+(avg/10)):
        activity_outcome = "Medium"
        menu_1 = 'success'
    else:
        activity_outcome = "Low"
        menu_1 = 'info'

    #***Image Reused***


### Start of talking to google
    client = vision.ImageAnnotatorClient()
    interactions = 5
# Loads the image into memory
    send = str(u.profile_image_url_https)
    send = send.replace('_normal','')
    image = types.Image()
    image.source.image_uri = send
    web_detection = client.web_detection(image=image).web_detection

### returning data
    full = len(web_detection.full_matching_images)
    partial = len(web_detection.partial_matching_images)
    entity = len(web_detection.web_entities)
    page = len(web_detection.pages_with_matching_images)
# calculation for the image matching based op total number of images returned.
    if full + partial != 0:
        if full + partial > 15:
            image_outcome = "Very High"
            menu_2 = 'danger'
        else:
            if full + partial > 10:
                image_outcome = "High"
                menu_2 = 'warning'
            else:
                if full + partial > 5:
                    image_outcome = "Medium"
                    menu_2 = 'success'
    else:
        image_outcome = "Low"
        menu_2 = 'info'

# grab the latest 100 tweets from the user then calculate average interaction per tweet
# exclude retweets as viral/popular tweets skew results too much
#200 is the largest sample size allowed by twitter api
    for tweet in tweepy.Cursor(api.user_timeline, id=u.screen_name, include_rts=False).items(200):
        interactions_per_tweet = tweet.retweet_count + tweet.favorite_count / 200.0
        interactions_per_follower = round(interactions_per_tweet / u.followers_count, 2)
#Probability caulations

    if interactions_per_follower != 0:
        if 0.9 <= interactions_per_follower <= 3.3:
            lowpost = "High"
            menu_3 = 'warning'

        elif 0.01 <= interactions_per_follower <= 0.9:
            lowpost = "Medium"
            menu_3 = 'success'

        else:
            lowpost = "Very High"
            menu_3 = 'danger'
    else:
        lowpost = "Low"
        menu_3 = 'info'

    return render_template('results.html', activity=activity_outcome, image=image_outcome, lowpost=lowpost, full=full, partial=partial, entity=entity, page=page, result=u.screen_name, perday=per_day, menu_1=menu_1, menu_2=menu_2, perfollower=interactions_per_follower, menu_3=menu_3)

@app.route('/about')
def about():
    return render_template('about.html', title='About')

#errors
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def server_error(e):
    return render_template('500.html'), 500



if __name__ == "__main__":
	app.run(host='0.0.0.0')
