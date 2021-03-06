from flask import Flask, session, url_for, redirect, request, render_template, abort, flash, Markup
import werkzeug
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
import bcrypt
import os
import markdown
from flask_babel import Babel, gettext

app = Flask(__name__)
babel = Babel(app)
app.secret_key = os.environ["COOKIE_SECRET_KEY"]
UPLOAD_FOLDER = './static'
ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg', 'gif', 'svg'])
reverse_proxy_app = werkzeug.middleware.proxy_fix.ProxyFix(app=app, x_for=1, x_proto=0, x_host=1, x_port=0, x_prefix=0)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db.sqlite'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['LANGUAGES'] = {
    'en': 'English',
    'it': 'Italian'
}
db = SQLAlchemy(app)
app.config.from_object(__name__)


class User(db.Model):
    uid = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String, nullable=False, unique=True)
    password = db.Column(db.LargeBinary, nullable=False)
    nome = db.Column(db.String, nullable=False)
    cognome = db.Column(db.String, nullable=False)
    titolo = db.Column(db.String, nullable=False)
    ruolo = db.Column(db.String, nullable=False)
    bio = db.Column(db.String, nullable=False)

    def __init__(self, nome, cognome, titolo, ruolo, email, password, bio):
        self.nome = nome
        self.cognome = cognome
        self.titolo = titolo
        self.ruolo = ruolo
        self.email = email
        self.bio = bio
        p = bytes(password, encoding="utf-8")
        self.password = bcrypt.hashpw(p, bcrypt.gensalt())

    def __repr__(self):
        return "{}-{}".format(self.uid, self.email)


class Prodotto(db.Model):
    pid = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String, nullable=False)
    descrizione = db.Column(db.String, nullable=False)
    descrizione_breve = db.Column(db.String, nullable=False)
    showcase = db.Column(db.Boolean, nullable=False)
    image = db.Column(db.String, nullable=False)

    def __init__(self, nome, descrizione, descrizione_breve, image):
        self.nome = nome
        self.descrizione = descrizione
        self.descrizione_breve = descrizione_breve
        self.showcase = False
        self.image = image

    def __repr__(self):
        return "{}-{}".format(self.pid, self.nome)


class Messaggio(db.Model):
    mid = db.Column(db.Integer, primary_key=True)
    data = db.Column(db.DateTime, nullable=False)
    contenuto = db.Column(db.String, nullable=False)

    def __init__(self, data, contenuto):
        self.data = data
        self.contenuto = contenuto

    def __repr__(self):
        return "{}-{}".format(self.mid, self.data)


def login(email, password):
    user = User.query.filter_by(email=email).first()
    try:
        return bcrypt.checkpw(bytes(password, encoding="utf-8"), user.password)
    except AttributeError:
        # Se non esiste l'Utente
        return False


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def generate_markdown(raw):
    return Markup(markdown.markdown(raw))


def generate_date(date):
    return "{}/{}/{} {}:{}".format(date.day, date.month, date.year, date.hour, date.minute)


def find_user(email):
    return User.query.filter_by(email=email).first()


@app.route('/')
def page_home():
    if 'username' not in session:
        return redirect(url_for('page_main'))
    else:
        session.pop('username')
        return redirect(url_for('page_main'))


@app.route('/welcome')
def page_main():
    css = url_for("static", filename="style.css")
    highlight = Prodotto.query.filter_by(showcase=True).all()
    prodotti = Prodotto.query.order_by(Prodotto.nome.asc()).all()
    team = User.query.all()
    latest = Messaggio.query.order_by(Messaggio.mid.desc()).first()
    return render_template("main.htm", css=css, highlight=highlight, prodotti=prodotti, team=team,
                           latestDate=latest.data, latestContent=generate_markdown(latest.contenuto),
                           latestMid=latest.mid)


@app.route('/welcome/mobile')
def page_phone_home():
    css = url_for("static", filename="style.css")
    prodotti = Prodotto.query.all()
    team = User.query.all()
    latest = Messaggio.query.order_by(Messaggio.mid.desc()).first()
    return render_template("phone_main.htm", css=css, prodotti=prodotti, team=team, latestDate=latest.data,
                           latestContent=generate_markdown(latest.contenuto), latestMid=latest.mid)


@app.route('/products')
def page_products():
    css = url_for("static", filename="style.css")
    products = Prodotto.query.all()
    return render_template("products.htm", css=css)


@app.route('/product_inspect/<int:pid>')
def page_product_inspect(pid):
    css = url_for("static", filename="style.css")
    users = User.query.all()
    prodotto = Prodotto.query.get_or_404(pid)
    desc, req, lic, down = prodotto.descrizione.split("|")
    desc = generate_markdown(desc)
    req = generate_markdown(req)
    lic = generate_markdown(lic)
    down = generate_markdown(down)
    return render_template("product_inspect.htm", users=users, prodotto=prodotto, css=css, desc=desc, req=req, lic=lic,
                           down=down)


@app.route('/blogpost/write/', methods=['GET', 'POST'])
def page_blogpost_write():
    if 'username' not in session:
        return abort(403)
    utente = find_user(session['username'])
    if request.method == "GET":
        return render_template("Amministrazione/Blogposts/blogpost_add.htm", utente=utente)
    nuovo = Messaggio(datetime.today(), request.form.get('messaggio'))
    db.session.add(nuovo)
    db.session.commit()
    return redirect(url_for("page_amministrazione"))


@app.route('/blogpost/edit/<int:mid>', methods=['GET', 'POST'])
def page_blogpost_edit(mid):
    if 'username' not in session:
        return abort(403)
    messaggio = Messaggio.query.get_or_404(mid)
    utente = find_user(session['username'])
    if request.method == "GET":
        return render_template("Amministrazione/Blogposts/blogpost_add.htm", utente=utente, messaggio=messaggio)
    messaggio.contenuto = request.form.get('messaggio')
    db.session.commit()
    return redirect(url_for("page_blogpost_list"))


@app.route('/blogpost/remove/<int:mid>')
def page_blogpost_remove(mid):
    if 'username' not in session:
        return abort(403)
    messaggio = Messaggio.query.get_or_404(mid)
    db.session.delete(messaggio)
    db.session.commit()
    return redirect(url_for('page_blogpost_list'))


@app.route('/blogposts')
def page_blogpost_list():
    if 'username' not in session:
        return abort(403)
    utente = find_user(session['username'])
    messaggi = Messaggio.query.all()
    return render_template("Amministrazione/Blogposts/blogpost_list.htm", utente=utente, messaggi=messaggi)


@app.route('/members')
def page_members():
    css = url_for("static", filename="style.css")
    users = User.query.all()
    return render_template("members.htm", users=users, css=css)


@app.route('/amministrazione', methods=["POST", "GET"])
def page_amministrazione():
    if request.method == 'GET' and 'username' in session:
        utente = find_user(session['username'])
        css = url_for("static", filename="style.css")
        return render_template("Amministrazione/amministrazione.htm", css=css, utente=utente)
    else:
        if login(request.form['email'], request.form['password']):
            session['username'] = request.form['email']
            return redirect(url_for('page_amministrazione'))
        else:
            abort(403)


@app.route('/product_add', methods=["POST", "GET"])
def page_product_add():
    if 'username' not in session:
        return abort(403)
    if request.method == 'GET':
        utente = find_user(session['username'])
        css = url_for("static", filename="style.css")
        return render_template("Amministrazione/Prodotti/product_add.htm", css=css, utente=utente)
    else:
        if 'file' not in request.files:
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        print(request.form.get('dbreve'))
        prodotto = Prodotto(request.form['nome'], request.form['destesa'], request.form['dbreve'], str(file.filename))
        db.session.add(prodotto)
        db.session.commit()
        return redirect(url_for('page_amministrazione'))


@app.route('/prodotto_del/<int:pid>')
def page_prodotto_del(pid):
    if 'username' not in session:
        return abort(403)
    prodotto = Prodotto.query.get_or_404(pid)
    try:
        os.remove("static/{}".format(prodotto.image))
    except:
        pass
    db.session.delete(prodotto)
    db.session.commit()
    return redirect(url_for('page_prodotti_list'))


@app.route('/blogpost/get/<int:upper>')
def page_blogpost_get(upper):
    messaggi = Messaggio.query.filter(Messaggio.mid < upper, Messaggio.mid > upper - 10).all()
    ans = {}
    for messaggio in messaggi:
        if messaggio.mid == upper:
            continue
        else:
            ans[messaggio.mid] = {'contenuto': generate_markdown(messaggio.contenuto),
                                  'data': generate_date(messaggio.data), 'mid': messaggio.mid}
    return ans


@app.route('/prodotto_vetrina/<int:pid>')
def page_prodotto_vetrina(pid):
    if 'username' not in session:
        return abort(403)
    prodotto = Prodotto.query.get_or_404(pid)
    prodotto.showcase = not prodotto.showcase
    db.session.commit()
    return redirect(url_for('page_prodotti_list'))


@app.route('/prodotti_list')
def page_prodotti_list():
    if 'username' not in session:
        abort(403)
    utente = find_user(session['username'])
    prodotti = Prodotto.query.all()
    css = url_for("static", filename="style.css")
    return render_template("Amministrazione/Prodotti/prodotti_list.htm", css=css, utente=utente, prodotti=prodotti)


@app.route('/prodotto_edit/<int:pid>', methods=["POST", "GET"])
def page_prodotto_edit(pid):
    if 'username' not in session:
        return abort(403)
    if request.method == 'GET':
        utente = find_user(session['username'])
        prodotto = Prodotto.query.get_or_404(pid)
        css = url_for("static", filename="style.css")
        return render_template("Amministrazione/Prodotti/product_edit.htm", css=css, utente=utente, prodotto=prodotto)
    else:
        prodotto = Prodotto.query.get_or_404(pid)
        prodotto.nome = request.form['nome']
        prodotto.descrizione_breve = request.form['dbreve']
        prodotto.descrizione = request.form['destesa']
        prodotto.downlink = request.form['download']
        db.session.commit()
        return redirect(url_for('page_prodotti_list'))


@app.route('/prodotto/toggle/<int:pid>')
def page_prodotto_toggle(pid):
    if 'username' not in session:
        return abort(403)
    prodotto = Prodotto.query.get_or_404(pid)
    prodotto.showcase = not prodotto.showcase
    db.session.commit()
    return redirect(url_for('page_prodotti_list'))


@app.route("/personale_add", methods=["POST", "GET"])
def page_personale_add():
    if 'username' not in session:
        return abort(403)
    if request.method == 'GET':
        utente = find_user(session['username'])
        css = url_for("static", filename="style.css")
        return render_template("Amministrazione/Personale/personale_add.htm", css=css, utente=utente)
    else:
        utente = User(request.form['nome'], request.form['cognome'], request.form['titolo'], request.form['ruolo'],
                      request.form['password'], request.form['email'], request.form['bio'])
        db.session.add(utente)
        db.session.commit()
        return redirect(url_for('page_amministrazione'))


@app.route("/personale_list")
def page_personale_list():
    if 'username' not in session:
        return abort(403)
    utente = find_user(session['username'])
    css = url_for("static", filename="style.css")
    personale = User.query.all()
    return render_template("Amministrazione/Personale/personale_list.htm", css=css, utente=utente, personale=personale)


@app.route("/personale_del/<int:id>")
def page_personale_del(id):
    if 'username' not in session:
        return abort(403)
    utente = User.query.get_or_404(id)
    db.session.delete(utente)
    db.session.commit()
    return redirect(url_for("page_personale_list"))


@app.route("/personale_edit/<int:id>", methods=["POST", "GET"])
def page_personale_edit(id):
    if 'username' not in session:
        return abort(403)
    if request.method == 'GET':
        utente = find_user(session['username'])
        user = User.query.get_or_404(id)
        css = url_for("static", filename="style.css")
        return render_template("Amministrazione/Personale/personale_edit.htm", css=css, utente=utente, user=user)
    user = User.query.get_or_404(id)
    user.nome = request.form['nome']
    user.cognome = request.form['cognome']
    user.titolo = request.form['titolo']
    user.ruolo = request.form['ruolo']
    if request.form['password'] != "":
        p = bytes(request.form['password'], encoding="utf-8")
        user.password = bcrypt.hashpw(p, bcrypt.gensalt())
    user.email = request.form['email']
    user.bio = request.form['bio']
    db.session.commit()
    return redirect(url_for("page_personale_list"))


if __name__ == "__main__":
    # Se non esiste il database viene creato
    if not os.path.isfile("db.sqlite"):
        utente = User("Sgozzoli", "Caione", "Antanizzatore", "Vicesindaco", "lorenzo.balugani@fermitech.info",
                      "password", "Lei ha clacsonato?")
        message = Messaggio(datetime.now(), "Il servizio è stato avviato. Ciao mondo!")
        db.create_all()
        db.session.add(utente)
        db.session.add(message)
        db.session.commit()
    app.run(debug=True, host="0.0.0.0")
