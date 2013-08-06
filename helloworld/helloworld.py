# Request handlers for http://helloworld-aldrin.appspot.com
from __future__ import with_statement

import webapp2, cgi, re, jinja2, os, time, datetime, hashlib, hmac, random, string, secret, sys, json, logging, email, urllib
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'libs'))

from geopy import geocoders
from geopy import distance
g = geocoders.GoogleV3()

from google.appengine.api import memcache
from google.appengine.api import mail
from google.appengine.api import files
from google.appengine.ext import db
from google.appengine.ext import blobstore
from google.appengine.ext.webapp import blobstore_handlers
from google.appengine.ext.webapp.mail_handlers import InboundMailHandler

template_dir = os.path.join(os.path.dirname(__file__), 'templates')
jinja_env = jinja2.Environment(loader = jinja2.FileSystemLoader(template_dir), 
                               autoescape = True)

# Handler for incoming mail
class IncomingEmailHandler(InboundMailHandler):
    subject_prefix = "[blog] "
    address_prefix = "Address: "
    location_prefix = "Location: "
    content_prefix = "Content: "

    # When email is received, the email is automatically parsed for subject, location, address, content, and picture input
    # If input is valid, the data will be stored into the database and automatically posted to the blog
    def receive(self, mail_message):
        logging.error("Received message from %s" % mail_message.sender)

        # Get email subject. Subject must start with the subject prefix to be valid
        if not hasattr(mail_message, 'subject'):
            return 
        email_subject = mail_message.subject
        logging.error("subject = " + email_subject)
        if not email_subject.startswith(self.subject_prefix):
            return
        else:
            email_subject = email_subject.replace(self.subject_prefix, "")

        # Get email body
        plaintext_bodies = mail_message.bodies('text/plain')
        email_body = None
        for y, x in plaintext_bodies:
            email_body = x.decode()
            logging.error("body = " + x.decode())
            break

        # Parse the email body for location, address, and content
        email_dict = self.parse_body(email_body)
        logging.error("parsed body")

        logging.error("checked for content")
        # If no location but address is present, location = address
        if not email_dict['location'] and email_dict['address']:
            email_dict['location'] = email_dict['address'] 
        logging.error("location = address")
        # Given the address in the email, get gps coordinates
        logging.error("parsed get coords")        
        user_coords = None
        try:
            if email_dict['address']:
                for _, coord in g.geocode(email_dict['address'], exactly_one=False):
                    coords = coord
                    break
                if coords:
                    user_coords = "%s, %s" % coords
        except: # exception if coordinates not found
            user_coords = None

        # Get email attachment
        blob_key = None

        """
        logging.error(dir(mail_message))
        if hasattr(mail_message, 'attachments'):
            logging.error("GOT EMAIL ATTACHMENT")
            for filename, contents in mail_message.attachments:
                logging.error(dir(filename))
                user_picture = contents.decode()
                break

            if user_picture:
                file_name = files.blobstore.create(mime_type="image/jpeg")
                with files.open(file_name, 'a') as f:
                    f.write(user_picture)
                files.finalize(file_name)
                blob_key = files.blobstore.get_blob_key(file_name)
        else:
            blob_key = None
        """

        mail = mail_message.original
        maintype = mail.get_content_maintype()
        if maintype == 'multipart':
            for part in mail.get_payload():
                logging.error(part.get_content_maintype())
                content_type = part.get_content_maintype()
                if content_type == 'image' or content_type == 'video':
                    if content_type == 'image':
                        mime_type = 'image/jpeg'
                    else:
                        mime_type = 'video/quicktime'
                    user_picture = part.get_payload(decode=True)
                    if user_picture:
                        file_name = files.blobstore.create(mime_type=mime_type)
                        with files.open(file_name, 'a') as f:
                            f.write(user_picture)
                        files.finalize(file_name)
                        blob_key = files.blobstore.get_blob_key(file_name)                   





        # Put contents into Blogposts object
        blog_post = BlogPosts(subject=email_subject, 
                              content=email_dict['content'],
                              location=email_dict['location'], 
                              address=email_dict['address'], 
                              coords=user_coords, 
                              blob_key=blob_key
                            )

        # Send post to database and flush memcache
        blog_post.put()
        memcache.flush_all()

    # Parses the email body to find location, address, and content. Returns a dictionary.
    def parse_body(self, message):
        body_dict = {'location': "", 
                     'address': "", 
                     'content': ""
                     }
        body_parts = message.replace("\r", "").split("\n")
        for part in body_parts:
            if part.startswith(self.location_prefix):
                body_dict['location'] = part.replace(self.location_prefix, "")
            if part.startswith(self.address_prefix):
                body_dict['address'] = part.replace(self.address_prefix, "")
            if part.startswith(self.content_prefix):
                body_dict['content'] = part.replace(self.content_prefix, "")
        return body_dict

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

# Regular expressions for username, password, and email
USERNAME_RE = re.compile(r"^[a-zA-Z0-9_-]{3,20}$")
PASSWORD_RE = re.compile(r"^.{3,20}$")
EMAIL_RE = re.compile(r"^[\S]+@[\S]+\.[\S]+$")

# self-explanatory...
def valid_username(username):
    return USERNAME_RE.match(username)

def valid_password(password):
    return PASSWORD_RE.match(password)

def valid_email(email):
    return EMAIL_RE.match(email)

# Renders string in html
def render_str(template, **params):
    t = jinja_env.get_template(template)
    return t.render(params)

# makes salt for password hashing
def make_salt():
    return "".join(random.choice(string.letters) for x in range(5))

# Returns password hash string
def make_pw_hash(name, pw, salt=make_salt()):
    h = hmac.new(str(name + pw)).hexdigest()
    return h

# Hashes name and pw and returns True if hash(name, pw) == h
def validate_pw(name, pw, h):
    #salt = h.split("|")[1]
    if make_pw_hash(name, pw, secret.secretstr) == h:
        return True

# Makes a cookie with name, value, and secure hash
def make_cookie(name, value, h=""):
    return '%s=%s|%s; Path=/' % (name, value, h)

# Base handler for the entire website. Does cool stuff.
class BaseHandler(webapp2.RequestHandler):

    # Checks to see if the user is logged in or if usr is requesting html or json
    def initialize(self, *a, **kw):
        webapp2.RequestHandler.initialize(self, *a, **kw)
        if self.logged_in():
            self.user = User.get_by_id(int(self.get_cookie("user_id").split("|")[0]))

        if self.request.url.endswith('.json'):
            self.format = 'json'
        else:
            self.format = 'html'

    # writes stuff
    def write(self, *a, **kw):
        self.response.out.write(*a, **kw)

    # Renders html and sends data so template can read it
    def render(self, template, **kw):
        if self.logged_in():
            user = User.get_by_id(int(self.get_cookie("user_id").split("|")[0]))
            self.write(render_str(template, user=user, **kw))
        else:
            self.write(render_str(template, **kw))

    # Renders json page using the d object
    def render_json(self, d):
        self.response.headers['Content-Type'] = 'application/json; charset=UTF-8'
        json_txt = json.dumps(d)
        self.write(json_txt)

    # Returns true if user is logged in
    def logged_in(self):
        return self.validate_cookie(self.get_cookie("user_id"))

    # Gets cookie with name = name
    def get_cookie(self, name):
        return self.request.cookies.get(name)

    # Returns true if the user's cookie is a valid cookie. Checks if id and pw_hash match.
    def validate_cookie(self, cookie):
        user_id_cookie = self.get_cookie("user_id")
        if user_id_cookie:
            user_id = user_id_cookie.split("|")[0]
            pw_hash = user_id_cookie.split("|")[1]
            if user_id:
                user = User.get_by_id(int(user_id))
                if user and user.pw_hash == pw_hash:
                    return True


# Handler for '/'
# Home Page
class PersonalWebsiteHandler(BaseHandler):
    def get(self):
        self.render('aldrinagana.html')

# Handler for '/signup'
# Sign up page
class SignupHandler(BaseHandler):
    # Renders signup page, if user is already logged in, redirect to blog
    def get(self):
        if self.logged_in():
            self.redirect('/blog')
        else:
            self.render('signup-form.html')

    # Evaluates signup form submitted by user
    def post(self):
        # Initialize error strings
        username_error = ""
        password_error = ""
        verify_error = ""
        email_error = ""

        # Get values from form
        user_username = self.request.get('username')
        user_password = self.request.get('password')
        user_verify = self.request.get('verify')
        user_email = self.request.get('email')

        hasError = False

        # Validate username
        if not valid_username(user_username):
            username_error = "Not a valid username."
            hasError = True
        else: # Check if user name is already taken
            user = db.GqlQuery("SELECT * FROM User WHERE username = :1", user_username).get()
            if user:
                username_error = "That username is already taken."
                user_username = ""
                hasError = True

        # Validate password and make sure they match
        if not valid_password(user_password):
            password_error = "Not a valid password."
            hasError = True
        elif user_password != user_verify:
            verify_error = "Passwords don't match"
            hasError = True

        # Email is optional. Validate it.
        if user_email: # and 
            if not valid_email(user_email): # and not user_email == secret.invitecode:
                email_error = "Not a valid email."
                hasError = True         

        # If no errors...
        if not (hasError):
            # Hash username and password and store into database
            h = make_pw_hash(user_username, user_password)
            user = User(username=user_username, pw_hash=h, email="")
            user.put()

            # Set the user's cookie 
            user_id = user.key().id()
            self.response.headers.add_header('Set-Cookie', make_cookie('user_id', user_id, h))

            # Redirect to welcome page
            self.redirect('/blog/welcome')

        # There are errors...rewrite the form with the error messages and input values
        else:
            self.write_form(username=user_username, 
                            email=user_email,
                            username_error=username_error, 
                            password_error=password_error, 
                            verify_error=verify_error, 
                            email_error=email_error)

    # Writes the signup form
    def write_form(self, username="", email="", username_error="", password_error="", verify_error="", email_error=""):
        self.render('signup-form.html', username=username, 
                                        email=email, 
                                        username_error=username_error, 
                                        password_error=password_error,
                                        verify_error=verify_error, 
                                        email_error=email_error
                                        )

# Handler for '/blog/login'
# Login page
class LoginHandler(BaseHandler):
    # Render login page. If already logged in, redirect to blog
    def get(self):
        if self.logged_in():
            self.redirect('/blog')
        else:
            self.render('login.html')

    # Evaluate login form
    def post(self):
        # Initialize error and get entered username and password
        login_error = ""
        user_username = self.request.get('username')
        user_password = self.request.get('password')

        # Attempt to get user information from database. If succeed, validate password, set cookie, and redirect to welcome
        user = db.GqlQuery("SELECT * FROM User WHERE username = :1", user_username).get()
        if user and validate_pw(user_username, user_password, user.pw_hash):
            self.response.headers.add_header('Set-Cookie', str(make_cookie('user_id', user.key().id(), user.pw_hash)))            
            self.redirect('/blog/welcome')

        # login failed, render form again 
        else:
            self.render('login.html', login_error="Invalid login")

# Handler for '/blog/logout'
# Logout page
class LogoutHandler(BaseHandler):
    # Erase user cookie. That's it.
    def get(self):
        self.response.headers.add_header('Set-Cookie', make_cookie('user_id', ""))
        self.redirect('/blog/signup')

# Handler for '/blog/welcome'
# Welcome page
class WelcomeHandler(BaseHandler):
    # If not logged in, redirect to signup lage. Otherwise, show welcome page.
    def get(self):
        if not self.logged_in():
            self.redirect('/blog/signup')
        else:
            self.render('welcome.html')

# Handler for '/img'
# Image pages for pictures
class GetImageHandler(BaseHandler):
    # Print picture
    def get(self):
        # Set response header so browser knows it's a picture
        self.response.headers['Content-Type'] = "image/jpeg"

        # Get id from url 
        entity_id = self.request.get("entity_id")

        # Find the picture in the cache
        key = "img_" + entity_id
        picture = memcache.get(key)

        # Print the picture. If not in cache, get picture and store in cache.
        if picture == None:
            post = BlogPosts.get_by_id(int(entity_id))
            if post and post.picture:
                self.write(post.picture)
                memcache.set(key, post.picture)
            else:
                self.write("no picture")
        else:
            self.write(picture)

# Handler for '/blog/newpost'
# New Post Page
class NewBlogPostHandler(BaseHandler):
    # Render the new post page
    def get(self):
        self.render('newpost.html')

    # Evaluate new post form
    def post(self):
        # Get values from submitted form
        user_subject = self.request.get('subject')
        user_content = self.request.get('content')
        user_location = self.request.get('location')
        user_address = self.request.get('address')
        user_picture = self.request.get('picture')
        is_video = self.request.get('is_video')
        if is_video:
            mime_type = "video/quicktime"
        else:
            mime_type = "image/jpeg"

        blob_key = None
        if user_picture:
            file_name = files.blobstore.create(mime_type=mime_type)
            with files.open(file_name, 'a') as f:
                f.write(user_picture)
            files.finalize(file_name)
            blob_key = files.blobstore.get_blob_key(file_name)


        # Subject and content required. If not present, print error and re-render
        if not (user_subject and user_content):
            error_message = "Please enter a subject and content."
            self.render('newpost.html', 
                        subject=user_subject, 
                        content=user_content, 
                        location=user_location,
                        address=user_address,  
                        error_message=error_message, 
                        )

        # So far so good...    
        else:
            # Given the address, try to find the gps coordinates of it.
            user_coords = None
            try:
                if user_address:
                    for _, coord in g.geocode(user_address, exactly_one=False):
                        coords = coord
                        break
                    if coords:
                        user_coords = "%s, %s" % coords

            # No coordinates found, address invalid, print error and re-render form
            except:
                user_coords = None
                error_message = "Address not found."
                self.render('newpost.html', 
                            subject=user_subject, 
                            content=user_content, 
                            location=user_location,
                            address=user_address,  
                            error_message=error_message, 
                            )
                return                

            # If address is present but no location name, location = name
            if user_coords and not user_location:
                user_location = user_address

            # Store data into blog post object, put into database and flush the cache
            blog_post = BlogPosts(subject=user_subject, 
                                  content=user_content, 
                                  location=user_location, 
                                  address=user_address, 
                                  picture=user_picture, 
                                  coords=user_coords, 
                                  blob_key=blob_key
                                  )
            blog_post.put()
            memcache.flush_all()
            
            # Redirect to permalind page of the post...or back to the blog
            post_id = str(blog_post.key().id())
            #self.redirect('/blog')
            self.redirect('/blog/%s' % post_id)


# Handler for '/blog/places'
# Places page
class PlacesHandler(BaseHandler):
    # Get posts from database, for each set of coordinates, add it to the url, render picture
    def get(self):
        image_url="http://maps.googleapis.com/maps/api/staticmap?center=Fremont,CA&zoom=9&scale=1&visual_refresh=true&size=600x600&sensor=false"
        posts = db.GqlQuery("SELECT * FROM BlogPosts")
        for post in posts:
            if post.coords:
                image_url += "&markers=" + str(post.coords)
        self.render('places.html', image_url=image_url)

# Handler for '/blog'
# Main blog page
class BlogHandler(BaseHandler):
    # Render the top most recent posts. Print when the database was last queried.
    def render_front(self, blog_posts=""):
        posts, last_queried = BlogPosts.top_posts()
        self.render('blog.html', blog_posts=posts, last_queried=(datetime.datetime.utcnow() - last_queried).total_seconds())

    # if requesting json, print the json, otherwise print the html
    def get(self):
        if self.format == 'json':
            posts = BlogPosts.top_posts()
            self.render_json([post.as_dict() for post in posts])
        else:
            self.render_front()

# Datastore object for a blog post
class BlogPosts(db.Model):
    # Subject and content are required, 'created' is the created time, everything else is optional
    subject = db.StringProperty(required=True)
    content = db.TextProperty()
    created = db.DateTimeProperty(auto_now_add=True)
    blob_key = blobstore.BlobReferenceProperty()
    location = db.StringProperty()
    address = db.StringProperty()
    coords = db.GeoPtProperty()

    # Renders the individual html for each post.
    def render(self):
        self._render_text = self.content.replace('\n', '<br>')
        pst_time = datetime.datetime.fromtimestamp(time.mktime(self.created.timetuple()), Pacific_tzinfo())
        return render_str("post.html", post=self, pst_time=pst_time)

    # Returns the post in the form of a dictionary, to be later converted to json
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

    # Returns a tuple of the top posts and the time that the database was last queried
    @staticmethod
    def top_posts(update=False):
        # Gets posts from memcache, if not in memcache, query db and store result in memcache
        key = 'top'
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

    # Returns a tuple of the post and last queried time, given the post_id
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

# Datastore object for a User
class User(db.Model):
    # username and encrypted password required, email optional
    username = db.StringProperty(required=True)
    pw_hash = db.StringProperty(required=True)
    email = db.StringProperty()

# Handler for '/blog/([0-9]+)(?:\.json)?'
# Permalink page for each post
class PermalinkHandler(BaseHandler):
    # Get the post with the given post_id 
    def get(self, post_id):
        blog_post, last_queried = BlogPosts.get_post(post_id)
        if blog_post:
            if self.format == 'json':
                self.render_json(blog_post.as_dict())
            else: 
                self.render('permalink.html', post=blog_post, last_queried=(datetime.datetime.utcnow()-last_queried).total_seconds())
        else:
            self.error(404)

    # Called when delete button is pressed
    # Delete post, fush cache, and redirect to blog
    def post(self, post_id):
        blog_post, _ = BlogPosts.get_post(post_id)
        blog_post.delete()
        memcache.flush_all()
        self.redirect('/blog/flush')
        self.redirect('/blog')

# Handler for '/blog/aboutme'
# About Me Page
class AboutMeHandler(BaseHandler):
    def get(self):
        self.render('me.html')

# Handler for '/blog/flush'
# Page to manually flush the cache
class FlushHandler(BaseHandler):
    # Fush cache and redirect to blog
    def get(self):
        memcache.flush_all()
        self.redirect('/blog')

class ServeHandler(blobstore_handlers.BlobstoreDownloadHandler):
    def get(self, resource):
        resource = str(urllib.unquote(resource))
        blob_info = blobstore.BlobInfo.get(resource)
        logging.error("BLOB CONTENT TYPE " + blob_info.content_type)
        self.send_blob(blob_info)

# All mappings of the entire website.
# Each tuple is made up of the url suffix and it's corresponding handler
application = webapp2.WSGIApplication([('/', PersonalWebsiteHandler), 
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
                                       ('/img', GetImageHandler),
                                       ('/serve/([^/]+)?', ServeHandler),  
                                        IncomingEmailHandler.mapping()
                                      ], debug=True)