# Request handler

import webapp2, cgi, re, jinja2, os, time, datetime, hashlib, hmac, random, string, secret, sys, json, logging
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'libs'))


from geopy import geocoders
from geopy import distance
g = geocoders.GoogleV3()

from google.appengine.api import memcache
from google.appengine.ext import db
from google.appengine.ext import blobstore
from google.appengine.ext.webapp import blobstore_handlers

template_dir = os.path.join(os.path.dirname(__file__), 'templates')
jinja_env = jinja2.Environment(loader = jinja2.FileSystemLoader(template_dir), 
                               autoescape = True)

# Used to convert UTC to PDT
class Pacific_tzinfo(datetime.tzinfo):
    """Implementation of the Pacific timezone."""
    def utcoffset(self, dt):
        return datetime.timedelta(hours=-8) + self.dst(dt)

    def _FirstSunday(self, dt):
        """First Sunday on or after dt."""
        return dt + datetime.timedelta(days=(6-dt.weekday()))

    def dst(self, dt):
        # 2 am on the second Sunday in March
        dst_start = self._FirstSunday(datetime.datetime(dt.year, 3, 8, 2))
        # 1 am on the first Sunday in November
        dst_end = self._FirstSunday(datetime.datetime(dt.year, 11, 1, 1))

        if dst_start <= dt.replace(tzinfo=None) < dst_end:
            return datetime.timedelta(hours=1)
        else:
            return datetime.timedelta(hours=0)
    def tzname(self, dt):
        if self.dst(dt) == datetime.timedelta(hours=0):
            return "PST"
        else:
            return "PDT"


months = ['January', 
          'Februrary', 
          'March', 
          'April', 
          'May', 
          'June', 
          'July', 
          'August', 
          'September', 
          'October', 
          'November',
          'December']

month_abbvs = dict((m[:3].lower(), m) for m in months)

def valid_month(month):
    if month:
        if month.isdigit():
            month = int(month)
            if month >= 1 and month <= 12:
                return months[month-1]
        else:
            short_month = month[:3].lower()
            if short_month in month_abbvs:
                return month_abbvs.get(short_month)

def valid_day(day):
    if day and day.isdigit():
        day = int(day)
        if day >= 1 and day <= 31:
            return day

def valid_year(year):
    if year and year.isdigit():
        year = int(year)
        if year >= 1900 and year <= 2020:
            return year

def escape_html(s):
    return cgi.escape(s, quote = True)


form = """
<form method="post">
    Hi, what is your birthday?
    <br>
    <label>Month
        <input type="text" name="Month" value=%(month)s>
    </label>

    <label>Day
        <input type="text" name="Day" value=%(day)s>
    </label>

    <label>Year
        <input type="text" name="Year" value=%(year)s>
    </label>
    <br>
    <div style="color: red">%(error)s</div>
    <input type="submit">
</form>
"""

alvin_picture = """
<div>LOL HI ALVIN</div>
<img src="https://raw.github.com/aldrinagana/Snake/master/Snake/lol.jpg" />
"""

Thanks_message = """
Thanks! That is a valid day!
"""

USERNAME_RE = re.compile(r"^[a-zA-Z0-9_-]{3,20}$")
PASSWORD_RE = re.compile(r"^.{3,20}$")
EMAIL_RE = re.compile(r"^[\S]+@[\S]+\.[\S]+$")

def valid_username(username):
    return USERNAME_RE.match(username)

def valid_password(password):
    return PASSWORD_RE.match(password)

def valid_email(email):
    return EMAIL_RE.match(email)

def render_str(template, **params):
    t = jinja_env.get_template(template)
    return t.render(params)

def make_salt():
    return "".join(random.choice(string.letters) for x in range(5))

def make_pw_hash(name, pw, salt=make_salt()):
    h = hmac.new(str(name + pw)).hexdigest()
    return h

def validate_pw(name, pw, h):
    #salt = h.split("|")[1]
    if make_pw_hash(name, pw, secret.secretstr) == h:
        return True

def make_cookie(name, value, h=""):
    return '%s=%s|%s; Path=/' % (name, value, h)

class BaseHandler(webapp2.RequestHandler):
    def initialize(self, *a, **kw):
        webapp2.RequestHandler.initialize(self, *a, **kw)
        if self.logged_in():
            self.user = User.get_by_id(int(self.get_cookie("user_id").split("|")[0]))

        if self.request.url.endswith('.json'):
            self.format = 'json'
        else:
            self.format = 'html'

    def write(self, *a, **kw):
        self.response.out.write(*a, **kw)

    def render(self, template, **kw):
        if self.logged_in():
            user = User.get_by_id(int(self.get_cookie("user_id").split("|")[0]))
            self.write(render_str(template, user=user, **kw))
        else:
            self.write(render_str(template, **kw))

    def render_json(self, d):
        self.response.headers['Content-Type'] = 'application/json; charset=UTF-8'
        json_txt = json.dumps(d)
        self.write(json_txt)

    def logged_in(self):
        return self.validate_cookie(self.get_cookie("user_id"))

    def get_cookie(self, name):
        return self.request.cookies.get(name)

    def validate_cookie(self, cookie):
        user_id_cookie = self.get_cookie("user_id")
        if user_id_cookie:
            user_id = user_id_cookie.split("|")[0]
            pw_hash = user_id_cookie.split("|")[1]
            if user_id:
                user = User.get_by_id(int(user_id))
                if user and user.pw_hash == pw_hash:
                    return True


class PersonalWebsiteHandler(BaseHandler):
    def get(self):
        self.render('aldrinagana.html')

class MainPage(BaseHandler):
    def write_form(self, error="", month="", day="", year=""):
        self.response.write(form % {'error': error, 
                                    'month': escape_html(month),
                                    'day': escape_html(day), 
                                    'year': escape_html(year)
                                    })

    def get(self):
        #self.response.headers['Content-Type'] = 'text/plain'
        self.write_form()

    def post(self):
        user_month = self.request.get('Month')
        user_day = self.request.get('Day')
        user_year = self.request.get('Year')

        month = valid_month(user_month)
        day = valid_day(user_day)
        year = valid_year(user_year)

        if month == "April" and day == 14 and year == 1999:
            self.redirect("/alvin")
        elif not (month and day and year):
            self.write_form("That is an invalid day!", user_month, user_day, user_year)
        
        else:
            self.redirect("/thanks")

        #self.response.headers['Content-Type'] = 'text/plain'

class ThanksHandler(BaseHandler):
    def get(self):
        self.response.write(Thanks_message)

class AlvinHandler(BaseHandler):
    def get(self):
        self.response.write(alvin_picture)

class ROT13Handler(BaseHandler):
    def get(self):
        self.render('rot13-form.html')

    def post(self):
        user_text = self.request.get('text')
        rot13_text = self.rot13(user_text)
        self.write_form(rot13_text)

    def write_form(self, text=""):
        self.render('rot13-form.html', text=text)

    def rot13(self, s):
        result = ""
        for letter in s:
            letter_int = ord(letter)
            if letter_int >= 65 and letter_int <= 90:
                letter_int += 13
                if letter_int > 90:
                    letter_int %= 90
                    letter_int += 64
            elif letter_int >= 97 and letter_int <= 122:
                letter_int += 13
                if letter_int > 122:
                    letter_int %= 122
                    letter_int += 96
            result += chr(letter_int)
        return result

class SignupHandler(BaseHandler):
    def get(self):
        if self.logged_in():
            self.redirect('/blog')
        else:
            self.render('signup-form.html')

    def post(self):
        username_error = ""
        password_error = ""
        verify_error = ""
        email_error = ""

        user_username = self.request.get('username')
        user_password = self.request.get('password')
        user_verify = self.request.get('verify')
        user_email = self.request.get('email')

        hasError = False

        if not valid_username(user_username):
            username_error = "Not a valid username."
            hasError = True

        else:
            user = db.GqlQuery("SELECT * FROM User WHERE username = :1", user_username).get()
            if user:
                username_error = "That username is already taken."
                user_username = ""
                hasError = True

        if not valid_password(user_password):
            password_error = "Not a valid password."
            hasError = True

        elif user_password != user_verify:
            verify_error = "Passwords don't match"
            hasError = True

        if user_email: # and 
            if not valid_email(user_email): # and not user_email == secret.invitecode:
                email_error = "Not a valid email."
                hasError = True         


        if not (hasError):
            h = make_pw_hash(user_username, user_password)
            user = User(username=user_username, pw_hash=h, email="")
            user.put()
            user_id = user.key().id()
            self.response.headers.add_header('Set-Cookie', make_cookie('user_id', user_id, h))
            self.redirect('/blog/welcome')

        else:
            self.write_form(username=user_username, 
                            email=user_email,
                            username_error=username_error, 
                            password_error=password_error, 
                            verify_error=verify_error, 
                            email_error=email_error)

    def write_form(self, username="", email="", username_error="", password_error="", verify_error="", email_error=""):
        self.render('signup-form.html', username=username, 
                                        email=email, 
                                        username_error=username_error, 
                                        password_error=password_error,
                                        verify_error=verify_error, 
                                        email_error=email_error
                                        )

class LoginHandler(BaseHandler):
    def get(self):
        if self.logged_in():
            self.redirect('/blog')
        else:
            self.render('login.html')

    def post(self):
        login_error = ""
        user_username = self.request.get('username')
        user_password = self.request.get('password')
        user = db.GqlQuery("SELECT * FROM User WHERE username = :1", user_username).get()
        if user and validate_pw(user_username, user_password, user.pw_hash):
            self.response.headers.add_header('Set-Cookie', str(make_cookie('user_id', user.key().id(), user.pw_hash)))            
            self.redirect('/blog/welcome')
        else:
            self.render('login.html', login_error="Invalid login")

class LogoutHandler(BaseHandler):
    def get(self):
        self.response.headers.add_header('Set-Cookie', make_cookie('user_id', ""))
        self.redirect('/blog/signup')

class WelcomeHandler(BaseHandler):
    def get(self):
        if not self.logged_in():
            self.redirect('/blog/signup')
        else:
            self.render('welcome.html')

class GetImageHandler(BaseHandler):
    def get(self):
        post = BlogPosts.get_by_id(int(self.request.get("entity_id")))
        if post and post.picture:
            self.response.headers['Content-Type'] = "image/jpeg"
            self.write(post.picture)
        else:
            self.write("no picture")

class NewBlogPostHandler(BaseHandler):
    def get(self):
        upload_url = blobstore.create_upload_url('/upload')
        self.render('newpost.html')

    def post(self):
        user_subject = self.request.get('subject')
        user_content = self.request.get('content')
        user_location = self.request.get('location')
        user_address = self.request.get('address')
        #user_picture = self.request.get('picture').encode('utf-8')
        user_picture = db.Blob(self.request.get('picture'))


        if not (user_subject and user_content):
            error_message = "Please enter a subject and content."
            self.render('newpost.html', 
                        subject=user_subject, 
                        content=user_content, 
                        location=user_location,
                        address=user_address,  
                        error_message=error_message, 
                        )
        else:
            user_coords = None
            try:
                if user_address:
                    for _, coord in g.geocode(user_address, exactly_one=False):
                        coords = coord
                        break
                if coords:
                    user_coords = "%s, %s" % coords
            except:
                user_coords = None
                if user_address:
                    error_message = "Address not found."
                    self.render('newpost.html', 
                                subject=user_subject, 
                                content=user_content, 
                                location=user_location,
                                address=user_address,  
                                error_message=error_message, 
                                )
                    return                


            if user_coords and not user_location:
                user_location = user_address

            blog_post = BlogPosts(subject=user_subject, 
                                  content=user_content, 
                                  location=user_location, 
                                  address=user_address, 
                                  picture=user_picture, 
                                  coords=user_coords)
            blog_post.put()
            memcache.flush_all()
            post_id = str(blog_post.key().id())
            #self.redirect('/blog')
            self.redirect('/blog/%s' % post_id)

class PlacesHandler(BaseHandler):
    def get(self):
        image_url="http://maps.googleapis.com/maps/api/staticmap?center=Fremont,CA&zoom=9&scale=1&visual_refresh=true&size=600x600&sensor=false"
        posts = db.GqlQuery("SELECT * FROM BlogPosts")
        for post in posts:
            if post.coords:
                image_url += "&markers=" + str(post.coords)
        self.render('places.html', image_url=image_url)

class BlogHandler(BaseHandler):
    def render_front(self, blog_posts=""):
        posts, last_queried = BlogPosts.top_posts()
        self.render('blog.html', blog_posts=posts, last_queried=(datetime.datetime.utcnow() - last_queried).total_seconds())

    def get(self):
        if self.format == 'json':
            posts = BlogPosts.top_posts()
            self.render_json([post.as_dict() for post in posts])
        else:
            self.render_front()

class BlogPosts(db.Model):
    subject = db.StringProperty(required=True)
    content = db.TextProperty(required=True)
    created = db.DateTimeProperty(auto_now_add=True)
    picture = db.BlobProperty()
    location = db.StringProperty()
    address = db.StringProperty()
    coords = db.GeoPtProperty()

    def render(self):
        self._render_text = self.content.replace('\n', '<br>')
        pst_time = datetime.datetime.fromtimestamp(time.mktime(self.created.timetuple()), Pacific_tzinfo())
        return render_str("post.html", post=self, pst_time=pst_time)

    def as_dict(self):
        time_fmt = "%c"
        d = {'subject' : self.subject, 
             'content' : self.content, 
             'created' : self.created.strftime(time_fmt), 
             'picture' : self.picture, 
             'location' : self.location, 
             'address' : self.address, 
            }
        return d

    @staticmethod
    def top_posts(update=False):
        key = 'topa'
        x = memcache.get(key)
        if x:
            posts, last_queried = x
        else:
            posts = None
        if posts == None or update:
            logging.error("DB QUERY")
            posts = db.GqlQuery("SELECT * FROM BlogPosts ORDER BY created DESC LIMIT 10")
            posts = list(posts)
            last_queried = datetime.datetime.utcnow()
            memcache.set(key, (posts, last_queried))
        return posts, last_queried

    @staticmethod
    def get_post(post_id):
        key = str(post_id)
        x = memcache.get(key)
        if x:
            post, last_queried = x
        else:
            post = None
        if post == None:
            logging.error("DB QUERY")
            post = BlogPosts.get_by_id(int(post_id))
            last_queried = datetime.datetime.utcnow()
            memcache.set(key, (post, last_queried))
        return post, last_queried


class User(db.Model):
    username = db.StringProperty(required=True)
    pw_hash = db.StringProperty(required=True)
    email = db.StringProperty()

class PermalinkHandler(BaseHandler):
    def get(self, post_id):
        blog_post, last_queried = BlogPosts.get_post(post_id)
        if blog_post:
            if self.format == 'json':
                self.render_json(blog_post.as_dict())
            else: 
                self.render('permalink.html', post=blog_post, last_queried=(datetime.datetime.utcnow()-last_queried).total_seconds())
        else:
            self.error(404)

    def post(self, post_id):
        blog_post, _ = BlogPosts.get_post(post_id)
        blog_post.delete()
        memcache.flush_all()
        self.redirect('/blog/flush')
        self.redirect('/blog')

class AboutMeHandler(BaseHandler):
    def get(self):
        self.render_posts()

    def render_posts(self, blog_posts=""):
        posts = db.GqlQuery("SELECT * FROM BlogPosts ORDER BY created DESC")
        self.render('me.html', blog_posts=posts)

class FlushHandler(BaseHandler):
    def get(self):
        memcache.flush_all()
        self.redirect('/blog')

application = webapp2.WSGIApplication([('/', PersonalWebsiteHandler), 
                                       ('/thanks', ThanksHandler), 
                                       ('/alvin', AlvinHandler), 
                                       ('/unit2/rot13', ROT13Handler), 
                                       ('/blog/signup', SignupHandler),
                                       ('/blog/logout', LogoutHandler),
                                       ('/blog/login', LoginHandler),  
                                       ('/blog/welcome', WelcomeHandler),
                                       ('/blog/places', PlacesHandler), 
                                       ('/blog/?(?:\.json)?', BlogHandler), 
                                       ('/blog/newpost', NewBlogPostHandler), 
                                       ('/blog/([0-9]+)(?:\.json)?', PermalinkHandler), 
                                       ('/blog/me', AboutMeHandler),
                                       ('/blog/flush', FlushHandler),  
                                       ('/img', GetImageHandler)
                                      ], debug=True)