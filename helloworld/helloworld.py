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
        day = valid_month(user_day)
        year = valid_year(user_year)

        if not (month and day and year):
            self.write_form("That is an invalid day!", user_month, user_day, user_year)
        else:
            self.response.write("Thanks! %(month)s %(day)s, %(year)s is a valid day!" % {"month": user_month, "day": user_day, "year": user_year})

        #self.response.headers['Content-Type'] = 'text/plain'
        #self.response.write(self.request)


application = webapp2.WSGIApplication([('/', MainPage)], debug=True)