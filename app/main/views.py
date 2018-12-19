from flask import render_template, request 
from .. import cache
from . import main
from app.models import Sequence, Steerer
import json, epics
import numpy as np
import time
from .forms import InputForm


def response_matrix(steerers_set, steerers_rb, locations, bpms, r_step, c_step, rt_upper_limit, cryo_upper_limit):
    rows = len(bpms)
    cols = len(steerers_set)
    loop_num = 2
    res = np.zeros((rows, cols))
    bpm_old_values = np.zeros(rows)
    fc1 = 'LEBT_BD:FC_01:In'
    for i in range(loop_num):
        for j, b in enumerate(bpms):
            time.sleep(0.01)
            bpm_old_values[j] += epics.caget(b)
        while True:
            time.sleep(1)
            if epics.caget(fc1) == 0:
                break

    bpm_old_values /= loop_num

    for i, s in enumerate(steerers_set):
        old_str_val = epics.caget(s)
        rb_pv = steerers_rb[i]
        print('response', s)
        if s.startswith('EBT', 1):
            step = r_step
            diff_limit = 0.1
        else: 
            step = c_step
            diff_limit = 0.5

        if old_str_val > 0:
            step = -step

        test_current = old_str_val + step
        epics.caput(s, test_current)
        while True:
            time.sleep(0.5)
            diff = abs(test_current - epics.caget(rb_pv))
            if diff < diff_limit:
                break
        
        bpm_avgs = np.zeros(len(bpms))

        for k in range(loop_num):
            for j, b in enumerate(bpms):
                print(b, epics.caget(b))
                time.sleep(0.01)
                if bpms[b][0] > locations[i]:
                    bpm_avgs[j] += epics.caget(b) - bpm_old_values[j]
            while True:
                time.sleep(1)
                if int(epics.caget(fc1)) == 0:
                    break
        res[:, i] = (bpm_avgs / loop_num) / step

        epics.caput(s, old_str_val)
        while True:
            time.sleep(0.5)
            diff = abs(old_str_val - epics.caget(rb_pv))
            if diff < diff_limit:
                break
    return res

@main.route('/')
def index():
    form = InputForm()
    tree = Sequence.to_json()
    return render_template('index_bak.html', tree=json.dumps(tree), form=form)

@main.route('/corrector-strength', methods=['POST'])
def corrector_strength():
    singular_value_low_limit = float(request.form['low_limit'])
    U = cache.cache.get('U')
    s = cache.cache.get('s')
    V = cache.cache.get('V')
    print('strength', U, s, V)
    steerer_set_pv = cache.cache.get('steerer_set_pv')
    steerer_rb_pv = cache.cache.get('steerer_rb_pv')
    bpm_pv = cache.cache.get('bpm_pv')
    steer_num = len(steerer_set_pv)
    bpm_vals = cache.cache.get('bpm_vals')
    orbit_to = cache.cache.get('orbit_to')
    old_corr_values = cache.cache.get('old_corr_values')
    rt_upper_limit = cache.cache.get('rt_upper_limit')
    cryo_upper_limit = cache.cache.get('cryo_upper_limit')
    bpm_num = len(bpm_pv)
    if singular_value_low_limit < 1e-6:
        for i in range(len(s)):
            S = np.zeros((steer_num, bpm_num))
            s_temp = s[s > s[-1-i]]
            S[:len(s_temp), :len(s_temp)] = np.diag(1 / s_temp)
            steer_strengths = -np.dot(V.T, np.dot(S, np.dot(U.T, bpm_vals - orbit_to))) 
            for j, corr in enumerate(steerer_set_pv):
                steer_strength = steer_strengths[j] + old_corr_values[j] 
                if (corr.startswith('EBT', 1) and abs(steer_strength) > rt_upper_limit) or (abs(steer_strength) > cryo_upper_limit):
                    break
            else:
                break
    else:
        s = s[s > singular_value_low_limit]
        S = np.zeros((steer_num, bpm_num))
        S[:len(s), :len(s)] = np.diag(1 / s)
        steer_strengths = -np.dot(V.T, np.dot(S, np.dot(U.T, bpm_vals - orbit_to)))
    result = {}
    for i, corr in enumerate(steerer_set_pv):
        steer_strength = steer_strengths[i] + old_corr_values[i] 
        steer_strength_clip = min(rt_upper_limit, abs(steer_strength)) * np.sign(steer_strength) if corr.startswith('EBT', 1) else min(cryo_upper_limit, abs(steer_strength)) * np.sign(steer_strength)
        print(steer_strength)
        epics.caput(corr, steer_strength_clip)
        steer = Steerer.query.filter_by(pv_set_name=corr).first()
        seqname = steer.sequence.name
        if seqname not in result:
            result[seqname] = []
        print(seqname, steer.name)
        result[seqname].append((steer.name, steer_strength))
        time.sleep(0.2)
    residual_orbit = 0xffff
    min_residual_corrs = {}
    while True:
        bpm_values = []
        for bpm in bpm_pv:
            bpm_values.append(epics.caget(bpm))
        current_residual_orbit = np.average(np.array(bpm_values)**2)
        if current_residual_orbit < residual_orbit:
            residual_orbit = current_residual_orbit
            for corr in steerer_rb_pv:
                min_residual_corrs[corr] = epics.caget(corr)
        time.sleep(0.2)
        if abs(steer_strength_clip - epics.caget(steerer_rb_pv[i])) < 0.5:
            break 

    for corr_pv, value in min_residual_corrs.items():
        epics.caput(corr_pv, value)
    
    nested_list = ''
    for seq in result:
        nested_list += '<li>' + seq 
        seq_list = ''
        for steer_name, strength in result[seq]:
            with open('corrector-strength.log', 'a') as f:
                f.write('{0}: {1}\n'.format(steer_name, strength))
            seq_list = seq_list + '<li>%s: %.2f</li>' % (steer_name, strength)
        seq_list = '<ul>' + seq_list + '</ul>'
        nested_list += seq_list + '</li>'
    nested_list = '<ul>' + nested_list + '</ul>'
    return nested_list

@main.route('/orbit-correction', methods=['POST'])
def orbit_correction():
    jsdata = request.form['tree']
    c_step = float(request.form['c_step'])
    r_step = float(request.form['r_step'])
    rt_upper_limit = float(request.form['rt_upper_limit'])
    cryo_upper_limit = float(request.form['cryo_upper_limit'])
    
    data = json.loads(jsdata)
    steerer_set_pv = []
    locations = []
    steerer_rb_pv = []
    bpm_pv = {}
    for seqname in data:
        seq = Sequence.query.filter_by(name=seqname).first()
        steerers = seq.steerers
        bpms = seq.bpms
        #for st in data[seqname]['steerers']:
        for st in data[seqname].get('steerers', {}):
            s = steerers.filter_by(name=st).first()
            steerer_set_pv.append(s.pv_set_name)
            locations.append(s.location)
            steerer_rb_pv.append(s.pv_rb_name)
        #for bpm in data[seqname]['bpms']:
        for bpm in data[seqname].get('bpms', {}):
            bpm_name, bpm_orbit = list(bpm.keys())[0], list(bpm.values())[0]
            b = bpms.filter_by(name=bpm_name).first()
            bpm_pv[b.pv_name] = (b.location, bpm_orbit)

    rep_matrix = response_matrix(steerer_set_pv, steerer_rb_pv, locations, bpm_pv, 
                                 r_step, c_step, rt_upper_limit, cryo_upper_limit) 
    steer_num = len(steerer_set_pv)
    bpm_num = len(bpm_pv)
    bpm_vals = []
    old_corr_values = np.zeros(steer_num)
    for index, corr in enumerate(steerer_set_pv):
        old_corr_values[index] = epics.caget(corr)
        time.sleep(0.2)

    for b in bpm_pv:
        bpm_avg = []
        for i in range(5):
            bpm_avg.append(epics.caget(b))
            time.sleep(0.2)
        bpm_vals.append(np.average(bpm_avg))
    bpm_vals = np.array(bpm_vals)
    orbit_to = [float(bpm_pv[k][1]) for k in bpm_pv]

    U, s, V = np.linalg.svd(rep_matrix, full_matrices=True)
    print('rep_matrix', rep_matrix)

    #S = np.zeros((steer_num, bpm_num))
    #S[:len(s), :len(s)] = np.diag(1 / s)
    #steer_strengths = -np.dot(V.T, np.dot(S, np.dot(U.T, bpm_vals - orbit_to)))
    cache.cache.set('bpm_vals',  bpm_vals)
    cache.cache.set('U', U)
    cache.cache.set('s', s)
    cache.cache.set('V', V)
    cache.cache.set('steerer_set_pv', steerer_set_pv)
    cache.cache.set('steerer_rb_pv', steerer_rb_pv)
    cache.cache.set('bpm_pv', bpm_pv)
    cache.cache.set('orbit_to', orbit_to)
    cache.cache.set('old_corr_values', old_corr_values)
    cache.cache.set('rt_upper_limit', rt_upper_limit)
    cache.cache.set('cryo_upper_limit', cryo_upper_limit)

    #result = {}
    #for i, corr in enumerate(steerer_pv):
    #    steer = Steerer.query.filter_by(pv_name=corr).first()
    #    seqname = steer.sequence.name
    #    if seqname not in result:
    #        result[seqname] = []
    #    result[seqname].append((steer.name, steer_strengths[i]))
    #
    #nested_list = ''
    #for seq in result:
    #    nested_list += '<li>' + seq 
    #    seq_list = ''
    #    for steer_name, strength in result[seq]:
    #        print(strength)
    #        seq_list = seq_list + '<li>%s: %s</li>' % (steer_name, strength)
    #    seq_list = '<ul>' + seq_list + '</ul>'
    #    nested_list += seq_list + '</li>'
    #nested_list = '<ul>' + nested_list + '</ul>'

    singular_value_tab = ['<table class="table">', '<tr>']

    for i, e in enumerate(s):
        if i % 6 == 0:
            singular_value_tab.append('</tr><tr><td>%.2e</td>' % e)
        else:
            singular_value_tab.append('<td>%.2f</td>' % e)   

    singular_value_tab.extend(['</tr>', '</table>']) 
    
    if singular_value_tab:
        svtab = ''.join(singular_value_tab)
        svtab = svtab.replace('<tr></tr>', '')
    return svtab  

