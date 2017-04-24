from flask_wtf import FlaskForm
from wtforms import FloatForm
from wtforms.validators import Required

class ConfigForm(FlaskForm):
    cryogenic_step = FloatForm('低温步长(A)', default=5.0, validators=[Required()])
    cryogenic_wait_time = FloatForm('低温等待时间(s)', default=10.0, validators=[Required()])
    roomtemp_step = FloatForm('常温步长(A)', default=1.0, validators=[Required()])
    roomtemp_wait_time = FloatForm('常温等待时间(s)', default=2.0, validators=[Required()])

