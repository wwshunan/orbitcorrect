from flask import render_template, request
from . import main
from app.models import Sequence
import json, epics
import numpy as np
import time

def response_matrix(steerers, bpms, rwait_time, cwait_time, r_step, c_step):
    rows = len(bpms)
    cols = len(steerers)
    res = np.zeros((rows, cols))
    bpm_old = []
    for b in bpms:
        bpm_avg = []
        for i in range(5):
            bpm_avg.append(epics.caget(b))
            time.sleep(0.2)
        bpm_old.append(np.average(bpm_avg))
    for i, s in enumerate(steerers):
        old_str_val = epics.caget(s)
        if s.startswith('MEBT'):
            step = r_step
            epics.caput(s, old_str_val + step)
            time.sleep(rwait_time)
        else:
            step = c_step
            epics.caput(s, old_str_val + step)
            time.sleep(cwait_time)
        for j, b in enumerate(bpms):
            if bpms[b] > steerers[s]:
                bpm_avg = []
                for i in range(5):
                    bpm_avg.append(epics.caget(b))
                    time.sleep(0.2)
                res[j, i] = (np.average(bpm_avg) - bpm_old[j]) / step

        if s.startswith('MEBT'):
            epics.caput(s, old_str_val)
            time.sleep(rwait_time)
        else:
            epics.caput(s, old_str_val)
            time.sleep(cwait_time)
    return res

@main.route('/')
def index():
    tree = Sequence.to_json()
    return render_template('index_bak.html', tree=json.dumps(tree))

@main.route('/orbit-correction', methods=['POST'])
def orbit_correction():
    jsdata = request.form['data']
    data = json.loads(jsdata)
    steerer_pv = {}
    bpm_pv = {}
    for seqname in data:
        seq = Sequence.query.filter_by(name=seqname).first()
        steerers = seq.steerers
        bpms = seq.bpms
        for e in data[seqname]:
            if e.startswith('DC'):
                s = steerers.filter_by(name=e).first()
                steerer_pv[s.pv_name] = s.location
            else:
                b = bpms.filter_by(name=e).all()
                bpm_pv[b[0].pv_name] = b[0].location
                bpm_pv[b[1].pv_name] = b[1].location

    rep_matrix = response_matrix(steerer_pv, bpm_pv, rwait_time, 
                                 cwait_time, r_step, c_step) 
    steer_num = len(steerer_pv)
    bpm_num = len(bpm_pv)
    bpm_vals = []
    for b in bpm_pv:
        bpm_avg = []
        for i in range(5):
            bpm_avg.append(epics.caget(b))
            time.sleep(0.2)
        bpm_vals.append(np.average(bpm_avg))
    bpm_vals = np.array(bpm_vals)

    U, s, V = np.linalg.svd(rep_matrix, full_matrices=True)
    S = np.zeros((steer_num, bpm_num))
    S[:len(s), :len(s)] = np.diag(1 / s)
    steer_strengths = -np.dot(V.T, np.dot(S, np.dot(U.T, bpm_vals)))

    result = {}
    for s in steerer_pv:
        steer = Steer.query.filter_by(pv_name=s).first()
        seqname = steer.sequence.name
        if seqname not in result:
            result[seqname] = []
        result[seqname].append(steer.name)
    
    nested_list = ''
    for seq in result:
        nested_list += '<li>' + seq 
        seq_list = ''
        for steer_name in result[seq]:
            seq_list = seq_list + '<li>%s</li>' % steer_name
        seq_list = '<ul>' + seq_list + '</ul>'
        nested_list += seq_list + '</li>'
    nested_list = '<ul>' + nested_list + '</ul>'

    return nested_list
