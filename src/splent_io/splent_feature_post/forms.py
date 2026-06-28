from flask_wtf import FlaskForm
from wtforms import SubmitField


class SplentFeaturePostForm(FlaskForm):
    submit = SubmitField("Save splent_feature_post")
