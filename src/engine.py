"""Dialectical orchestration and its single-call control; no planner or ARS."""
from copy import deepcopy
import time

from src.baseline.single import system_prompt
from src.data.loader import ModelInput
from src.dialectical import debate
from src.dialectical.prompts import adversarial_system_prompt
from src.io_utils import canonical
from src.labels import labels_for
from src.schemas import report_schema

class Engine:
    def __init__(self,llm,*,task,mode='adaptive',adaptive_policy='adversarial',use_patterns=True):
        labels_for(task)
        if mode not in ('single','adaptive'):raise ValueError('Mode must be single or adaptive')
        if adaptive_policy!='adversarial':raise ValueError('Only the original adversarial dialectical flow is supported')
        if type(use_patterns) is not bool:raise ValueError('use_patterns must be boolean')
        self.llm,self.task,self.mode=llm,task,mode
        self.adaptive_policy,self.use_patterns=adaptive_policy,use_patterns

    def run(self,model_input,metadata):
        if not isinstance(model_input,ModelInput):raise TypeError('Engine accepts only label-free ModelInput')
        started=time.monotonic()
        protocol='none' if self.mode=='single' else self.adaptive_policy

        def ask(role,stage,reports,history,instruction,schema=None,question=None,validator=None,extra=None):
            payload={'input':model_input.as_dict(),'reports':deepcopy(reports),'history':deepcopy(history),
                'instruction':instruction,'question':question,'plan':None,**deepcopy(extra or {})}
            if self.mode=='single':prompt=system_prompt(self.task,self.use_patterns)
            else:
                prompt=adversarial_system_prompt(role,self.task,use_patterns=self.use_patterns)
            return self.llm.generate(system_prompt=prompt,user_prompt=canonical(payload),
                schema=schema or report_schema(self.task),
                metadata={**metadata,'task':self.task,'role':role,'stage':stage,'protocol':protocol},validator=validator)

        if self.mode=='single':
            verdict=ask('Single','single',{},[],'Predict the task label.')
            return dict(prediction=verdict['prediction'],planner_protocol='none',plan=None,
                initial_agents={},deliberation=[],final_agents={},
                arbiter=verdict,stop_reason='single',latency_seconds=time.monotonic()-started)
        prosecutor,defender,arbiter,reason=debate.execute(
            ask,model_input,self.task,use_patterns=self.use_patterns)
        return dict(framework='adversarial',prediction=arbiter['prediction'],planner_protocol=protocol,plan=None,
            prosecutor=prosecutor,defender=defender,initial_agents={'Prosecutor':prosecutor},
            deliberation=[{'round':0,'role':'Defender',**defender}],
            final_agents={'Prosecutor':prosecutor,'Defender':defender},arbiter=arbiter,stop_reason=reason,
            latency_seconds=time.monotonic()-started)
