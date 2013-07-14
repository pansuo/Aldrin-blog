# Simple request handler

import webapp2
import cgi

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


class MainPage(webapp2.RequestHandler):
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
            self.write_form(self.request)
        
        else:
            self.redirect("/thanks")

        #self.response.headers['Content-Type'] = 'text/plain'
        #self.response.write(self.request)


class ThanksHandler(webapp2.RequestHandler):
    def get(self):
        self.response.write(Thanks_message)

class AlvinHandler(webapp2.RequestHandler):
    def get(self):
        self.response.write(alvin_picture)


ROT13form = """
<form method="post">
    <label style="font-size: 2em"><strong>Enter some text to ROT13:</strong></label>
    <br>
        <textarea name="text" cols="50" rows="5">%(text)s</textarea>
    <input type="submit">
</form>
"""

def rot13(s):
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

class ROT13Handler(webapp2.RequestHandler):
    def get(self):
        self.write_form()

    def post(self):
        user_text = self.request.get('text')
        rot13_text = rot13(user_text)
        self.write_form(rot13_text)

    def write_form(self, text=""):
        self.response.write(ROT13form % {'text': escape_html(text)})

application = webapp2.WSGIApplication([('/', MainPage), 
                                       ('/thanks', ThanksHandler), 
                                       ('/alvin', AlvinHandler), 
                                       ('/unit2/rot13', ROT13Handler)
                                      ], debug=True)