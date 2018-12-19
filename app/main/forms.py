#coding=utf-8
from wtforms import Form, FloatField
from wtforms.validators import Required

class InputForm(Form):
    cryogenic_step = FloatField(u'低温踢轨电流 (A)', default=25.0, validators=[Required()])
    cryo_upper_limit = FloatField(u'低温电流上限 (A)', default=65, validators=[Required()])
    roomtemp_step = FloatField(u'常温踢轨电流(A)', default=4.0, validators=[Required()])
    rt_upper_limit = FloatField(u'常温电流上限 (A)', default=15.0, validators=[Required()])

