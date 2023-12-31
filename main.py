from flask import Flask, render_template, redirect, url_for, flash, current_app, abort
from flask_bootstrap import Bootstrap
from flask_ckeditor import CKEditor
from datetime import date
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from forms import CreatePostForm, RegisterForm, LoginForm, CommentForm
from functools import wraps
from flask_gravatar import Gravatar
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get("SECRET_KEY", "8BYkEfBA6O6donzWlSihBXox7C0sKR6b")
ckeditor = CKEditor(app)
Bootstrap(app)

gravatar = Gravatar(app,
                    size=100,
                    rating='g',
                    default='retro',
                    force_default=False,
                    force_lower=False,
                    use_ssl=False,
                    base_url=None)
##CONNECT TO DB
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DATABASE_URL",  "sqlite:///blog.db")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


##CONFIGURE TABLES

class BlogPost(db.Model):
    __tablename__ = "blog_posts"
    id = db.Column(db.Integer, primary_key=True)
    author = relationship("User", back_populates="posts")
    title = db.Column(db.String(250), unique=True, nullable=False)
    subtitle = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text, nullable=False)
    img_url = db.Column(db.String(250), nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey("blog_user.id"))
    comments = relationship("Comment", back_populates="blog")


# db.create_all()
class User(UserMixin, db.Model):
    __tablename__ = "blog_user"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(250), nullable=False)
    email = db.Column(db.String(250), nullable=False, unique=True)
    password = db.Column(db.String(250), nullable=False)
    posts = relationship("BlogPost", back_populates="author")
    comments = relationship("Comment", back_populates="user")


class Comment(db.Model):
    __tablename__ = "comment"
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)
    user = relationship("User", back_populates="comments")
    user_id = db.Column(db.Integer, db.ForeignKey("blog_user.id"))
    blog_id = db.Column(db.Integer, db.ForeignKey("blog_posts.id"))
    blog = relationship("BlogPost", back_populates="comments")


with app.app_context():
    db.create_all()

login_manager = LoginManager()
login_manager.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


def admin(func):
    @wraps(func)
    def admin_only(*args, **kwargs):
        if current_user.is_authenticated and current_user.id == 1:
            return func(*args, **kwargs)
        else:
            abort(403, description="You shall not pass")

    return admin_only


@app.route('/')
def get_all_posts():
    posts = BlogPost.query.all()
    return render_template("index.html", all_posts=posts)


@app.route('/register', methods=["GET", "POST"])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        new_name = form.name.data
        new_email = form.email.data
        if db.session.execute(db.select(User).where(User.email == new_email)).scalar():
            flash("Email already registered. Log in instead!")
            return redirect("/login")
        else:
            new_pass = generate_password_hash(form.password.data)
            new_user = User(name=new_name, email=new_email, password=new_pass)
            with app.app_context():
                db.session.add(new_user)
                db.session.commit()
                login_user(new_user)
            return redirect("/")
    return render_template("register.html", form=form)


@app.route('/login', methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data
        with app.app_context():
            user = db.session.execute(db.select(User).where(User.email == email)).scalar()
            if user:
                password = form.password.data
                if check_password_hash(user.password, password):
                    login_user(user)
                    return redirect("/")
                else:
                    flash("Wrong password")
            else:
                flash("User not found")
    return render_template("login.html", form=form)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('get_all_posts'))


@app.route("/post/<int:post_id>", methods=["GET", "POST"])
def show_post(post_id):
    form = CommentForm()
    requested_post = BlogPost.query.get(post_id)
    list_comment = db.session.execute(db.select(Comment).where(Comment.blog_id == post_id)).scalars()
    if form.validate_on_submit():
        if current_user.is_authenticated:
            comment = form.body.data
            new_comment = Comment(text=comment, user=current_user, blog=requested_post)
            db.session.add(new_comment)
            db.session.commit()
        else:
            flash("Login required")
            return redirect("/login")
    return render_template("post.html", post=requested_post, form=form, comment=list_comment)


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/contact")
def contact():
    return render_template("contact.html")


@app.route("/new-post", methods=["GET", "POST"])
@admin
def add_new_post():
    form = CreatePostForm()
    if form.validate_on_submit():
        new_post = BlogPost(
            title=form.title.data,
            subtitle=form.subtitle.data,
            body=form.body.data,
            img_url=form.img_url.data,
            author=current_user,
            date=date.today().strftime("%B %d, %Y")
        )
        with app.app_context():
            db.session.add(new_post)
            db.session.commit()
        return redirect(url_for("get_all_posts"))
    return render_template("make-post.html", form=form)


@app.route("/edit-post/<int:post_id>", methods=["GET", "POST"])
@admin
def edit_post(post_id):
    post = BlogPost.query.get(post_id)
    edit_form = CreatePostForm(
        title=post.title,
        subtitle=post.subtitle,
        img_url=post.img_url,
        body=post.body
    )
    if edit_form.validate_on_submit():
        post.title = edit_form.title.data
        post.subtitle = edit_form.subtitle.data
        post.img_url = edit_form.img_url.data
        post.body = edit_form.body.data
        db.session.commit()
        return redirect(url_for("show_post", post_id=post.id))

    return render_template("make-post.html", form=edit_form)


@app.route("/delete/<int:post_id>")
@admin
def delete_post(post_id):
    post_to_delete = BlogPost.query.get(post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_posts'))


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
