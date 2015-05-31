
import nd.db
import sqlite3
import logging, logging.handlers

from bottle import route, template, run, redirect, request, static_file, response, Bottle
import bottle.ext.sqlite

from argparse import ArgumentParser
import os.path

NB_NEWSPAPERS_PER_PAGE = 12

# the options available
parser = ArgumentParser(description='The np webserver.')
parser.add_argument("-l", "--logs", type=str, default="server.log", help="The log file to be used")
parser.add_argument("-d", "--db", type=str, default="newspapers", help="The database used to store metadata")

options = parser.parse_args()
db_name = '%s.db' % options.db
db_folder = options.db

app = Bottle()
plugin = bottle.ext.sqlite.Plugin(dbfile=db_name)
app.install(plugin)

# create the application's logger
logger = logging.getLogger('')
logger.setLevel(logging.INFO)
logHandler = logging.handlers.RotatingFileHandler(options.logs, maxBytes=1024*1024, backupCount=5)
formatter = logging.Formatter('%(levelname)s:%(asctime)s: %(message)s', datefmt='%d.%m.%Y %H:%M')
logHandler.setFormatter(formatter)
logger.addHandler(logHandler)

LOGGED_IN_COOKIE = "logged-in"
LOGGED_IN_AS = "logged-as"
def check_auth_or_redirect(db):
    username = request.get_cookie(LOGGED_IN_AS)

    hash = db.check_auth(username)
    if hash != None:
        if request.get_cookie(LOGGED_IN_COOKIE, secret=hash) == "1":
            return

    username = 'someone' if username == None else username
    logger.warning('Intrusion tried by %s [%s]',
                   username, request.remote_addr)
    redirect('/login')

@app.route('/')
def index():
    redirect('/login')

@app.route('/login', method="ANY")
def login(db):
    db = nd.db.DB(db)
    loginError = False
    ret = dict(path=request.urlparts.path,
               loginError=False,
               name='NPs')

    if 'username' in request.forms:
        username = request.forms.get('username') or ''
        ret['username'] = username
        password = request.forms.get('password') or ''

        hash = db.check_auth(username, password)
        if hash != None:
            response.set_cookie(LOGGED_IN_AS, username, max_age=3600)
            response.set_cookie(LOGGED_IN_COOKIE, "1", secret=hash, max_age=3600)
            logger.info('User %s logged in successfully [%s]',
                        username, request.remote_addr)
            redirect('/newspapers/')
        else:
            logger.warning('Bad credentials given by %s [%s]',
                           username, request.remote_addr)
            ret['loginError'] = True

    return template('login.tpl', ret)

@app.route('/logout')
def logout():
    username = request.get_cookie(LOGGED_IN_AS)
    logger.info('User %s logs out', username)
    response.delete_cookie(LOGGED_IN_AS)
    response.delete_cookie(LOGGED_IN_COOKIE)
    redirect('/login')

@app.route('/newspapers/<name:re:.*>')
def newspapers(name, db):
    db = nd.db.DB(db)

    display = request.query.display or 'list'
    check_auth_or_redirect(db)

    from_np_no = request.query.from_np or '0'
    if from_np_no != None and from_np_no.isdigit():
        from_np_no = int(from_np_no)

    name = name if name != '' else None
    from_nb = (from_np_no, NB_NEWSPAPERS_PER_PAGE+1)
    issues = db.issues(name, from_nb=from_nb)

    previous = max(from_np_no-NB_NEWSPAPERS_PER_PAGE, 0)
    if previous == from_np_no:
        previous = None

    next = from_np_no+NB_NEWSPAPERS_PER_PAGE
    if len(issues) <= NB_NEWSPAPERS_PER_PAGE:
        next = None
    else:
        issues = issues[:-1]

    return template('newspapers.tpl',
                    dict(issues=issues,
                         newspapers=db.newspapers(),
                         current_newspaper=name,
                         path=request.urlparts.path,
                         display=display,
                         other_page_numbers=(previous,next),
                         current_page=from_np_no))

@app.route('/thumbnail/<id:re:\d+>')
def thumbnail(id, db):
    db = nd.db.DB(db)

    check_auth_or_redirect(db)
    issues = db.issues(id=id)

    if issues and issues[0].thumbnail_path():
        thpath = os.path.join(db_folder, issues[0].thumbnail_path())
        if os.path.isfile(thpath):
            return static_file(issues[0].thumbnail_path(), root=db_folder)
        else:
            return static_file('no_thumbnail.png', root='static')

@app.route('/issue/<id:re:\d+>')
def newspaper(id, db):
    db = nd.db.DB(db)
    check_auth_or_redirect(db)
    username = request.get_cookie(LOGGED_IN_AS)

    issues = db.issues(id=id)
    if not issues:
        logger.error('Invalid newspaper pointed by "%s" [%s]',
                     request.fullpath, request.remote_addr)
        redirect('/newspapers/')
    else:
        issue = issues[0]
        logger.info('User %s downloads %s [%s]',
                    username, issue, request.remote_addr)
        filename = '%s %s.pdf' % (issue.title(), issue.date())
        return static_file(issue.path(), root=db_folder,
                           download=filename,
                           mimetype='application/pdf')

@app.route('/static/<filename:re:.+>')
def static(filename):
    return static_file(filename, root='static')

run(app, server='cherrypy', host='0.0.0.0', port=8080)

