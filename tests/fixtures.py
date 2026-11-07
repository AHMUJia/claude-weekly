"""Synthetic inputs only; never presented as real work."""
from copy import deepcopy


def sample(empty=False):
    period = {'start':'2026-12-30','end':'2027-01-05','timezone':'Asia/Singapore','carry_in':'previous_turn'}
    data = {'schema_version':1,'status':'ready','period':period,'sources':{'stats':'stats.json'},
            'headline':'测试数据，不代表真实工作','workstreams':[],'outputs':[],
            'decisions':[],'priorities':[],'reflection':'','lessons':[],'pages':{}}
    stats = {'start':'2026-12-30T00:00:00+08:00','end':'2027-01-05T23:59:59+08:00','multi_day':True,'sessions':[]}
    if empty:
        return data,stats
    for i,(key,name,day,tokens,turns) in enumerate([('session-a','菌群算法','12-31',900_000_000,181),('session-b','样本复核','01-02',200_000_000,8)]):
        stats['sessions'].append({'key':key,'title':name,'from':day+' 09:00','to':day+' 17:00',
                                  'usage_main':{'test-model':{'input':tokens-500,'output':500}},
                                  'usage_by_day':{day:tokens},'user_turns':[{'time':day+' 09:20','text':'仅供测试'} for _ in range(turns)],
                                  'cwd':'F:/test','subagents':[]})
        data['workstreams'].append({'id':f'line-{i}','name':name,'title':name+'记录','icon':'data',
                                    'session_keys':[key],'summary':'测试汇总','body':'- 实际运行结果的测试替身。'})
    data['outputs'] = [{'id':f'item-{i}','workstream':f'line-{i%2}','label':f'测试成果 {i+1}','short':f'交付 {i+1}',
                        'description':'用于跨周期渲染测试','evidence':'synthetic:test-only'} for i in range(3)]
    data['priorities'] = [{'level':'P1','label':'尽量完成','items':[{'title':'验证新样本','short':'数据复核','detail':'仅供测试的计划'}]}]
    return data,stats


def extended():
    data,stats = sample()
    data['pages']['performance'] = {'title':'本期回归验证','workstream':'line-0',
                                    'regression':{'before':80,'after':105,'passed':101}}
    data['pages']['pipeline'] = {'title':'样本处理进度','workstream':'line-1',
                                 'statuses':[{'id':x,'label':label,'short':label} for x,label in [('ready','完成'),('check','复核'),('wait','待办'),('hold','暂停')]],
                                 'rows':[{'name':f'样本 {i+1}','note':'测试记录','status':x,'result':label} for i,(x,label) in enumerate([('ready','已核对'),('check','核验中'),('wait','待确认'),('hold','暂停')])],
                                 'next_action':'复核剩余样本'}
    widget = {'type':'flow','title':'图表重建','workstream':'line-0','source_count':3,'source_label':'组数据',
              'outputs':[{'value':12,'label':'张结果图'}]}
    data['pages']['results'] = {'title':'本期交付','widgets':[deepcopy(widget) for _ in range(5)]}
    return data,stats
