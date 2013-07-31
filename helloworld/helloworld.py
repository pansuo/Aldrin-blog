# Request handler

import webapp2, cgi, re, jinja2, os, time, datetime, hashlib, hmac, random, string

from google.appengine.ext import db

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
    if make_pw_hash(name, pw) == h:
        return True

def make_cookie(name, value, h=""):
    return '%s=%s|%s; Path=/' % (name, value, h)


class BaseHandler(webapp2.RequestHandler):
    def write(self, *a, **kw):
        self.response.out.write(*a, **kw)

    def render(self, template, **kw):
        if self.logged_in():
            user = User.get_by_id(int(self.get_cookie("user_id").split("|")[0]))
            self.write(render_str(template, user=user, **kw))
        else:
            self.write(render_str(template, **kw))

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
                if user.pw_hash == pw_hash:
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
        #self.response.write(self.request)

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

        if user_email and not valid_email(user_email):
            email_error = "Not a valid email."
            hasError = True

        if not (hasError):
            h = make_pw_hash(user_username, user_password)
            user = User(username=user_username, pw_hash=h, email=user_email)
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
        self.render('login.html')

    def post(self):
        login_error = ""
        user_username = self.request.get('username')
        user_password = self.request.get('password')
        user = db.GqlQuery("SELECT * FROM User WHERE username = :1", user_username).get()
        if user and validate_pw(user_username, user_password, user.pw_hash):
            self.redirect('/blog/welcome')
        else:
            self.render('login.html', login_error="Invalid login")

class LogoutHandler(BaseHandler):
    def get(self):
        self.response.headers.add_header('Set-Cookie', make_cookie('user_id', ""))
        self.redirect('/blog/signup')


class WelcomeHandler(BaseHandler):
    def get(self):
        user_id_cookie = self.get_cookie("user_id")
        if user_id_cookie:
            user_id = user_id_cookie.split("|")[0]
            user = User.get_by_id(int(user_id))
        if not user_id_cookie or not user:
            self.redirect('/blog/signup')
            return
        else:
            self.render('welcome.html')

class NewBlogPostHandler(BaseHandler):
    def get(self):
        self.render('newpost.html', subject="", content="")

    def post(self):
        user_subject = self.request.get('subject')
        user_content = self.request.get('content')
        if not (user_subject and user_content):
            error_message = "Please enter a title and content"
            self.render('newpost.html', subject=user_subject, content=user_content, error_message=error_message)
        else:
            blog_post = BlogPosts(subject=user_subject, content=user_content)
            blog_post.put()
            post_id = str(blog_post.key().id())
            self.redirect('/blog')
            #self.redirect('/blog/%s' % post_id)

class BlogHandler(BaseHandler):
    def render_front(self, blog_posts=""):
        posts = db.GqlQuery("SELECT * FROM BlogPosts ORDER BY created DESC")
        self.render('blog.html', blog_posts=posts)

    def get(self):
        self.render_front()

class BlogPosts(db.Model):
    subject = db.StringProperty(required = True)
    content = db.TextProperty(required = True)
    created = db.DateTimeProperty(auto_now_add = True)

    def render(self):
        self._render_text = self.content.replace('\n', '<br>')
        pst_time = datetime.datetime.fromtimestamp(time.mktime(self.created.timetuple()), Pacific_tzinfo())
        return render_str("post.html", post=self, pst_time=pst_time)

class User(db.Model):
    username = db.StringProperty(required=True)
    pw_hash = db.StringProperty(required=True)
    email = db.StringProperty()


class PermalinkHandler(BaseHandler):
    def get(self, post_id):
        blog_post = BlogPosts.get_by_id(int(post_id))
        if blog_post:
            self.render('permalink.html', post=blog_post)
        else:
            self.error(404)

class AboutMeHandler(BaseHandler):
    def get(self):
        self.render_posts()

    def render_posts(self, blog_posts=""):
        posts = db.GqlQuery("SELECT * FROM BlogPosts ORDER BY created DESC")
        self.render('me.html', blog_posts=posts)

application = webapp2.WSGIApplication([('/', PersonalWebsiteHandler), 
                                       ('/thanks', ThanksHandler), 
                                       ('/alvin', AlvinHandler), 
                                       ('/unit2/rot13', ROT13Handler), 
                                       ('/blog/signup', SignupHandler),
                                       ('/blog/logout', LogoutHandler),
                                       ('/blog/login', LoginHandler),  
                                       ('/blog/welcome', WelcomeHandler), 
                                       ('/blog', BlogHandler), 
                                       ('/blog/newpost', NewBlogPostHandler), 
                                       ('/blog/([0-9]+)', PermalinkHandler), 
                                       ('/blog/me', AboutMeHandler)
                                      ], debug=True)