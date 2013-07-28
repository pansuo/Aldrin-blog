# Simple request handler

import webapp2
import cgi
import re
import jinja2
import os

template_dir = os.path.join(os.path.dirname(__file__), 'templates')
jinja_env = jinja2.Environment(loader = jinja2.FileSystemLoader(template_dir), 
                               autoescape = True)



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

class BaseHandler(webapp2.RequestHandler):
    def write(self, *a, **kw):
        self.response.out.write(*a, **kw)

    def render_str(self, template, **params):
        t = jinja_env.get_template(template)
        return t.render(params)

    def render(self, template, **kw):
        self.write(self.render_str(template, **kw))

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

        if not valid_username(user_username):
            username_error = "That is not a valid username."

        if not valid_password(user_password):
            password_error = "That is not a valid password."

        elif user_password != user_verify:
            verify_error = "Passwords don't match"

        if user_email and not valid_email(user_email):
            email_error = "That is not a valid email."

        if not (username_error or password_error or verify_error or email_error):
            self.redirect('/unit2/welcome?username=' + user_username)
        else:
            self.write_form(username=user_username, 
                            email=user_email,
                            username_error=username_error, 
                            password_error=password_error, 
                            verify_error=verify_error, 
                            email_error=email_error)


    def write_form(self, username="", email="", username_error="", password_error="", verify_error="", email_error=""):
        self.render('signup-form.html', {'username': username,
                                          'email': email,
                                          'username_error': username_error, 
                                          'password_error': password_error, 
                                          'verify_error': verify_error, 
                                          'email_error': email_error})

class WelcomeHandler(BaseHandler):
    def get(self):
        username = self.request.get('username')
        if valid_username(username):
            self.render('welcome.html', username=username)
        else:
            self.redirect('/unit2/signup')

class BlogHandler(BaseHandler):
    def get(self):
        self.render('blog.html')


application = webapp2.WSGIApplication([('/', PersonalWebsiteHandler), 
                                       ('/thanks', ThanksHandler), 
                                       ('/alvin', AlvinHandler), 
                                       ('/unit2/rot13', ROT13Handler), 
                                       ('/unit2/signup', SignupHandler), 
                                       ('/unit2/welcome', WelcomeHandler), 
                                       ('/blog', BlogHandler)
                                      ], debug=True)