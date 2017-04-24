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

            hdict['nodes'] = hor_nodes
            nodes_steerers.append(hdict)

            vdict = {}
            vdict['text'] = 'Vertical'
            ver_nodes = []
            for steer in steerers:
                if steer.name.startswith('DCV'):
                    ver_nodes.append(steer.to_json())
            vdict['nodes'] = ver_nodes
            nodes_steerers.append(vdict)

            steerer_dict['nodes'] = nodes_steerers
            nodes1.append(steerer_dict)

            bpm_dict = {}
            bpm_dict['text'] = 'Bpms'
            nodes_bpms = []
            bpms = s.bpms.all()
            exists = []
            for b in bpms:
                if b.name not in exists:
                    nodes_bpms.append(b.to_json())
                    exists.append(b.name)
            bpm_dict['nodes'] = nodes_bpms
            nodes1.append(bpm_dict)

            seq_dict['nodes'] = nodes1
            tree.append(seq_dict)
        return tree
        

    def __repr__(self):
        return '<Sequence %r>' % self.name

    @staticmethod
    def insert_sequences():
        for name in ['MEBT', 'CM1', 'CM2', 'CM3']:
            seq = Sequence(name=name)
            db.session.add(seq)
        db.session.commit()

class Steerer(db.Model):
    __tablename__ = 'steerers'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64))
    pv_name = db.Column(db.String(64), unique=True)
    location = db.Column(db.Integer)
    max_value = db.Column(db.Float, default=15)
    sequence_id = db.Column(db.Integer, db.ForeignKey('sequences.id'))

    def to_json(self):
        return {'text': self.name}

    def __repr__(self):
        return '<Steerer %r>' % self.pv_name

    @staticmethod
    def insert_steerers():
        hv = ('H', 'V')
        streerers = {
            'MEBT': ['MEBT_PS', (1, 2, 3, 4, 5, 6, 7)],
            'CM1': ['HCM1_PS', (9, 11, 13, 15, 17, 19)],
            'CM2': ['HCM2_PS', (20, 22, 24, 26, 28, 30)],
            'CM3': ['HCM3_PS', (31, 33, 35, 37, 39, 41)]
        }
        for seq in streerers:
            for i, l in enumerate(streerers[seq][1]):
                for j in range(2):
                    s = Steerer(name='DC%c%d' % (hv[j], i+1), pv_name='%s:DC%s_0%d:ISet' % (streerers[seq][0], hv[j], i+1), location=l, sequence=Sequence.query.filter_by(name=seq).first())
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
        return {'text': self.name}
    
    def __repr__(self):
        return '<Bpm %r>' % self.pv_name

    @staticmethod
    def insert_bpms():
        hv = ('X', 'Y')
        sequences = ['MEBT', 'CM1', 'CM2', 'CM3']
        bpms_location = [
            (1, 4, 5, 7, 8),
            (10, 12, 14, 16, 18),
            (21, 23, 25, 27, 29),
            (32, 34, 36, 38, 40)
        ]
        c = 0
        for i in range(len(sequences)):
            for l in bpms_location[i]:
                c += 1
                for j in range(2):
                    b = Bpm(name='bpm%d' % c, pv_name='Bpm:%d-%c11' % (c, hv[j]), location=l, sequence=Sequence.query.filter_by(name=sequences[i]).first())
                    db.session.add(b)
        db.session.commit()
