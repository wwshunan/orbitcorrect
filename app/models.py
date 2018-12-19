from . import db

class Sequence(db.Model):
    __tablename__ = 'sequences'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True)
    steerers = db.relationship('Steerer', backref='sequence', lazy='dynamic')
    bpms = db.relationship('Bpm', backref='sequence', lazy='dynamic')

    @staticmethod
    def to_json():
        tree = []
        sequences = Sequence.query.all()
        for s in sequences:
            steerers = s.steerers.all()
            seq_dict = {}
            seq_dict['text'] = s.name
            nodes1 = []

            steerer_dict = {}
            steerer_dict['text'] = 'Steerers'
            nodes_steerers = []

            hdict = {}
            hdict['text'] = 'Horizontal'
            hor_nodes = []
            for steer in steerers:
                if steer.name.startswith('DCH'):
                    hor_nodes.append(steer.to_json())

            hdict['items'] = hor_nodes
            nodes_steerers.append(hdict)

            vdict = {}
            vdict['text'] = 'Vertical'
            ver_nodes = []
            for steer in steerers:
                if steer.name.startswith('DCV'):
                    ver_nodes.append(steer.to_json())
            vdict['items'] = ver_nodes
            nodes_steerers.append(vdict)

            steerer_dict['items'] = nodes_steerers
            nodes1.append(steerer_dict)

            bpm_dict = {}
            bpm_dict['text'] = 'Bpms'
            nodes_bpms = []

            hdict = {}
            hdict['text'] = 'Horizontal'
            hor_nodes = []
            bpms = s.bpms.all()
            for bpm in bpms:
                if bpm.name.startswith('X'):
                    hor_nodes.append(bpm.to_json())
            hdict['items'] = hor_nodes
            nodes_bpms.append(hdict)

            vdict = {}
            vdict['text'] = 'Vertical'
            ver_nodes = []
            for bpm in bpms:
                if bpm.name.startswith('Y'):
                    ver_nodes.append(bpm.to_json())
            vdict['items'] = ver_nodes
            nodes_bpms.append(vdict)
            bpm_dict['items'] = nodes_bpms
            nodes1.append(bpm_dict)

            seq_dict['items'] = nodes1
            tree.append(seq_dict)
        return tree
        

    def __repr__(self):
        return '<Sequence %r>' % self.name

    @staticmethod
    def insert_sequences():
        for name in ['MEBT', 'CM1', 'CM2', 'CM3', 'CM4', 'HEBT']:
            seq = Sequence(name=name)
            db.session.add(seq)
        db.session.commit()

class Steerer(db.Model):
    __tablename__ = 'steerers'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64))
    pv_set_name = db.Column(db.String(64), unique=True)
    pv_rb_name = db.Column(db.String(64))
    location = db.Column(db.Integer)
    max_value = db.Column(db.Float, default=15)
    sequence_id = db.Column(db.Integer, db.ForeignKey('sequences.id'))

    def to_json(self):
        return {'text': self.name}

    def __repr__(self):
        return '<Steerer %r>' % self.pv_set_name

    @staticmethod
    def insert_steerers():
        hv = ('H', 'V')
        streerers = {
            'MEBT': ['MEBT_PS', (1, 2, 3, 4, 5, 6, 7)],
            'CM1': ['HCM1_PS', (9, 11, 13, 15, 17, 19)],
            'CM2': ['HCM2_PS', (20, 22, 24, 26, 28, 30)],
            'CM3': ['HCM3_PS', (31, 33, 35, 37, 39)],
            'CM4': ['HCM4_PS', (40, 42, 44, 46, 48, 50)],
            'HEBT': ['HEBT_PS', (52, 53, 55)]
        }
        for seq in streerers:
            for i, l in enumerate(streerers[seq][1]):
                for j in range(2):
                    set_name=('%s:DC%s_0%d:Iset:ao' if seq == 'CM4' else '%s:DC%s_0%d:ISet') % (streerers[seq][0], hv[j], i+1)
                    rb_name=('%s:DC%s_0%d:IMon:ai' if seq == 'CM4' else '%s:DC%s_0%d:IMon') % (streerers[seq][0], hv[j], i+1)
                    s = Steerer(name='DC%c%d' % (hv[j], i+1), pv_set_name=set_name, pv_rb_name=rb_name, location=l, sequence=Sequence.query.filter_by(name=seq).first())
                    db.session.add(s)
        db.session.commit()

class Bpm(db.Model):
    __tablename__ = 'bpms'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64))
    pv_name = db.Column(db.String(64), unique=True)
    location = db.Column(db.Integer)
    sequence_id = db.Column(db.Integer, db.ForeignKey('sequences.id'))

    def to_json(self):
        return {'text': self.name, 'value': 0}
    
    def __repr__(self):
        return '<Bpm %r>' % self.pv_name

    @staticmethod
    def insert_bpms():
        hv = ('X', 'Y')
        sequences = ['MEBT', 'CM1', 'CM2', 'CM3', 'CM4', 'HEBT']
        bpms_location = [
            (1, 4, 5, 7, 8),
            (10, 12, 14, 16, 18),
            (21, 23, 25, 27, 29),
            (32, 34, 36, 38, 41),
            (43, 45, 47, 49, 51),
            (54, 56)
        ]
        c = 0
        for i in range(len(sequences)):
            for l in bpms_location[i]:
                c += 1
                for j in range(2):
                    b = Bpm(name='%c-bpm%d' % (hv[j], c), pv_name='Bpm:%d-%c11' % (c, hv[j]), 
                            location=l, sequence=Sequence.query.filter_by(name=sequences[i]).first())
                    db.session.add(b)
        db.session.commit()
