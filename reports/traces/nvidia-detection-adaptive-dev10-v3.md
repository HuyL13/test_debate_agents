# Failed detection adaptive v3 and resume

Six completed samples; planner failed on 237:5509 in the initial run and one resume. This run is not included in complete-run metrics.

## Log 1: 237:4907 / Factual / initial

valid=False; cache_hit=False; error=URLError

[Full request/response](C:/Users/yoga/Downloads/cocolofa_pard/outputs/nvidia-detection-adaptive-dev10-v3/raw_calls.jsonl:1)

```json
null
```

## Log 2: 237:4907 / Factual / initial

valid=False; cache_hit=False; error=URLError

[Full request/response](C:/Users/yoga/Downloads/cocolofa_pard/outputs/nvidia-detection-adaptive-dev10-v3/raw_calls.jsonl:2)

```json
null
```

## Log 3: 237:4907 / Factual / initial

valid=False; cache_hit=False; error=URLError

[Full request/response](C:/Users/yoga/Downloads/cocolofa_pard/outputs/nvidia-detection-adaptive-dev10-v3/raw_calls.jsonl:3)

```json
null
```

## Log 4: 237:4907 / Factual / initial

valid=True; cache_hit=False; error=None

[Full request/response](C:/Users/yoga/Downloads/cocolofa_pard/outputs/nvidia-detection-adaptive-dev10-v3/raw_calls.jsonl:4)

```json
"{\"prediction\":\"Non-Fallacious\",\"confidence\":0.9,\"content\":\"\\\"People should just agree that everyone deserves the same right. No one should get more then others.\\\"\"}"
```

## Log 5: 237:4907 / Logical / initial

valid=True; cache_hit=False; error=None

[Full request/response](C:/Users/yoga/Downloads/cocolofa_pard/outputs/nvidia-detection-adaptive-dev10-v3/raw_calls.jsonl:5)

```json
"{\n  \"prediction\": \"Non-Fallacious\",\n  \"confidence\": 0.95,\n  \"content\": \"People should just agree that everyone deserves the same right. No one should get more then others. Lets stay respectful for the best options.\"\n}"
```

## Log 6: 237:4907 / Contextual / initial

valid=True; cache_hit=False; error=None

[Full request/response](C:/Users/yoga/Downloads/cocolofa_pard/outputs/nvidia-detection-adaptive-dev10-v3/raw_calls.jsonl:6)

```json
"{\"prediction\":\"Non-Fallacious\",\"confidence\":0.99,\"content\":\"The target comment presents a normative claim that everyone should receive equal rights and that no one should receive more, without offering an argument or evidence to support this position. Since it does not contain an argumentative structure that could be evaluated for logical consistency or errors, it does not exhibit a logical fallacy.\"}"
```

## Log 7: 237:4907 / Planner / plan

valid=True; cache_hit=False; error=None

[Full request/response](C:/Users/yoga/Downloads/cocolofa_pard/outputs/nvidia-detection-adaptive-dev10-v3/raw_calls.jsonl:7)

```json
"{\"protocol\":\"round_robin\",\"topic\":\"fallaciousness of target comment\",\"reason\":\"The comment makes a normative claim without presenting reasoning that could be evaluated for logical validity. It does not exhibit a logical fallacy.\",\"order\":[\"Factual\",\"Logical\",\"Contextual\"],\"affirmative\":[],\"negative\":[],\"examiner\":\"Contextual\",\"max_rounds\":1}"
```

## Log 8: 237:4907 / Factual / rr_0

valid=True; cache_hit=False; error=None

[Full request/response](C:/Users/yoga/Downloads/cocolofa_pard/outputs/nvidia-detection-adaptive-dev10-v3/raw_calls.jsonl:8)

```json
"{\"prediction\":\"Non-Fallacious\",\"confidence\":0.98,\"content\":\"The comment is a straightforward normative statement: \\\"People should just agree that everyone deserves the same right. No one should get more than others.\\\" It does not present an argument, premises, or evidence, so there is no logical structure that could contain a fallacy. At most, the commenter misses a premise that merits justification of why a universal ‘same right’ should be accepted—e.g., the claim that rights are naturally equal for all—nor does it overgeneralize beyond its content. Therefore the comment is not logically fallacious.\"}"
```

## Log 9: 237:4907 / Logical / rr_0

valid=True; cache_hit=False; error=None

[Full request/response](C:/Users/yoga/Downloads/cocolofa_pard/outputs/nvidia-detection-adaptive-dev10-v3/raw_calls.jsonl:9)

```json
"{\"prediction\":\"Non-Fallacious\",\"confidence\":0.99,\"content\":\"The target comment does not provide any premises or reasoning, merely states a normative stance that everyone should receive equal rights. While it omits a concrete justification—such as a premise that rights are intrinsically equal or that equality of rights is morally required—this omission does not itself constitute a logical fallacy. The statement simply lacks argumentative support rather than containing an invalid inference. Hence, the comment is non-fallacious.\"}"
```

## Log 10: 237:4907 / Contextual / rr_0

valid=True; cache_hit=False; error=None

[Full request/response](C:/Users/yoga/Downloads/cocolofa_pard/outputs/nvidia-detection-adaptive-dev10-v3/raw_calls.jsonl:10)

```json
"{\"prediction\":\"Non-Fallacious\",\"confidence\":0.96,\"content\":\"The comment states an unquestioned normative claim (“everyone deserves the same right”) without explaining *which* right it refers to or *why* it should be equally granted. A fuller justification would need a premise such as: *rights are grounded in human dignity and therefore should be distributed equally* or an explicit acknowledgment that the rights in question are the civil, legal, and moral rights that arise in the context of Costa Rica’s upcoming election (particularly those affecting LGBTQI individuals). The omission of that premise makes the statement an incomplete argument, but it does not introduce an invalid inference or logical fallacy. The limitation is thus about missing context and justification, not about a fallacious structure.\"}"
```

## Log 11: 237:4907 / Arbiter / final

valid=True; cache_hit=False; error=None

[Full request/response](C:/Users/yoga/Downloads/cocolofa_pard/outputs/nvidia-detection-adaptive-dev10-v3/raw_calls.jsonl:11)

```json
"{\"prediction\":\"Non-Fallacious\",\"confidence\":1.0,\"content\":\"The comment simply states a normative claim and a polite request. It does not present premises, an inference, or any argumentative structure that could be evaluated for validity, so it contains no logical fallacy.\"}"
```

## Log 12: 237:4908 / Factual / initial

valid=True; cache_hit=False; error=None

[Full request/response](C:/Users/yoga/Downloads/cocolofa_pard/outputs/nvidia-detection-adaptive-dev10-v3/raw_calls.jsonl:12)

```json
"{\"prediction\":\"Fallacious\",\"confidence\":0.99,\"content\":\"{\\\"label\\\":\\\"Fallacious\\\"}\"}"
```

## Log 13: 237:4908 / Logical / initial

valid=True; cache_hit=False; error=None

[Full request/response](C:/Users/yoga/Downloads/cocolofa_pard/outputs/nvidia-detection-adaptive-dev10-v3/raw_calls.jsonl:13)

```json
"{\n  \"prediction\": \"Fallacious\",\n  \"confidence\": 0.95,\n  \"content\": \"The comment commits a False Dilemma: it presents only two mutually exclusive outcomes—either Fabricio (who allegedly “eliminates rights”) wins or Carlos guarantees equal rights—while ignoring any other possible election results or candidates. The quoted reasoning 'Obviously, we elect evil and allow Fabricio to eliminate the rights of those he does not agree with or we vote for Carlos and guarantee equal rights for all' directly supports the inference that these are the only two options, which is an invalid oversimplification..\"\n}"
```

## Log 14: 237:4908 / Contextual / initial

valid=True; cache_hit=False; error=None

[Full request/response](C:/Users/yoga/Downloads/cocolofa_pard/outputs/nvidia-detection-adaptive-dev10-v3/raw_calls.jsonl:14)

```json
"{\"prediction\":\"Fallacious\",\"confidence\":0.87,\"content\":\"The comment asserts only two possible outcomes of the election—either “evil” Fabricio who will eliminate rights, or Carlos who guarantees equal rights—while implying there are no other options. This presents a **false dilemma** by reducing a complex electoral decision to two extremes, ignoring any moderate or alternative candidates. The span “Obviously, we elect evil and allow Fabricio to eliminate the rights … or we vote for Carlos and guarantee equal rights for all” supports the inference that there are only these two choices. The reasoning therefore commits a logical fallacy. (Additional evidence that the claim about Fabricio's intentions is unsupported could further support the fallaciousness, but the primary issue is the false dilemma.)\"}"
```

## Log 15: 237:4908 / Planner / plan

valid=True; cache_hit=False; error=None

[Full request/response](C:/Users/yoga/Downloads/cocolofa_pard/outputs/nvidia-detection-adaptive-dev10-v3/raw_calls.jsonl:15)

```json
"{\"protocol\":\"cross_examination\",\"topic\":\"LGBTQI Rights Defenders Sound Alarm over Costa Rica's Presidential Election\",\"reason\":\"All agents agreed the comment commits a False Dilemma, therefore a cross‑examination protocol captures the unanimous assessment without division.\",\"order\":[\"Contextual\",\"Factual\",\"Logical\"],\"affirmative\":[],\"negative\":[],\"examiner\":\"Contextual\",\"max_rounds\":1}"
```

## Log 16: 237:4908 / Contextual / ce_0_question

valid=True; cache_hit=False; error=None

[Full request/response](C:/Users/yoga/Downloads/cocolofa_pard/outputs/nvidia-detection-adaptive-dev10-v3/raw_calls.jsonl:16)

```json
"{\"question\":\"Does the claim that only ‘Fabricio’ or ‘Carlos’ can win, without mentioning any other potential candidates, accurately represent all viable options in the election?\",\"content\":\"The comment presents a false dilemma by stating: “Obviously, we elect evil and allow Fabricio to eliminate the rights of those he does not agree with or we vote for Carlos and guarantee equal rights for all.” This inference relies on the premise that only these two outcomes are possible, ignoring the existence of other candidates or electoral outcomes. The support for this inference is the span: “Obviously, we elect evil ... or we vote for Carlos and guarantee equal rights for all.” By reducing a multi‑candidacy election to two mutually exclusive choices, the comment commits a logical fallacy. Therefore, the target comment is **Fallacious**.\"}"
```

## Log 17: 237:4908 / Factual / ce_answer_0

valid=True; cache_hit=False; error=None

[Full request/response](C:/Users/yoga/Downloads/cocolofa_pard/outputs/nvidia-detection-adaptive-dev10-v3/raw_calls.jsonl:17)

```json
"{\"prediction\":\"Fallacious\",\"confidence\":0.98,\"content\":\"The comment limits the choice to only two options—‘Fabricio’ as a negative force or ‘Carlos’ as a positive force—by the wording: “Obviously, we elect evil and allow Fabricio … or we vote for Carlos and guarantee equal rights for all.” This overlooks any other candidates or electoral outcomes that could exist, thus presenting an inaccurate dichotomy. The inference that these are the only viable options is unsupported and constitutes a false dilemma. Therefore the target comment is fallacious.\"}"
```

## Log 18: 237:4908 / Logical / ce_answer_0

valid=True; cache_hit=False; error=None

[Full request/response](C:/Users/yoga/Downloads/cocolofa_pard/outputs/nvidia-detection-adaptive-dev10-v3/raw_calls.jsonl:18)

```json
"{\"prediction\":\"Fallacious\",\"confidence\":0.97,\"content\":\"The target comment’s assertion—that the only viable election outcomes are a Fabricio win that eliminates rights or a Carlos win that guarantees equal rights—does not accurately represent all possible options in the election. The comment establishes a premise that only two outcomes exist and then concludes that these are the only viable options. This premise lacks any evidence that other candidates or electoral outcomes are impossible, so the inference is invalid. Hence the comment commits a false dilemma, making the claim Fallacious.\"}"
```

## Log 19: 237:4908 / Contextual / ce_0_reflection

valid=True; cache_hit=False; error=None

[Full request/response](C:/Users/yoga/Downloads/cocolofa_pard/outputs/nvidia-detection-adaptive-dev10-v3/raw_calls.jsonl:19)

```json
"{\"question\":null,\"content\":\"The responses directly addressed the question by concluding that the claim does not accurately represent all viable options and that the comment commits a false dilemma. The consensus indicates the question has been resolved.\"}"
```

## Log 20: 237:4908 / Arbiter / final

valid=True; cache_hit=False; error=None

[Full request/response](C:/Users/yoga/Downloads/cocolofa_pard/outputs/nvidia-detection-adaptive-dev10-v3/raw_calls.jsonl:20)

```json
"{\"prediction\":\"Fallacious\",\"confidence\":0.99,\"content\":\"The comment presents only two extreme election outcomes—Fabricio as evil or Carlos as righteous—though other candidates or outcomes are possible. This unfounded binary misrepresents the full range of options, constituting a false dilemma, and therefore the target comment is fallacious.\"}"
```

## Log 21: 237:5209 / Factual / initial

valid=True; cache_hit=False; error=None

[Full request/response](C:/Users/yoga/Downloads/cocolofa_pard/outputs/nvidia-detection-adaptive-dev10-v3/raw_calls.jsonl:21)

```json
"{\"prediction\":\"Fallacious\",\"confidence\":0.82,\"content\":\"I think this election is about good and evil in Costa Rica.  The country has always been a great example of strong modern views and stable stances in Central America.  If the singer is elected it is going to take a giant leap back.   The economy will also take a hit.  This area has always been tolerant and that has help the country in so many ways.  The country needs to vote for good and vote away evil.\"}"
```

## Log 22: 237:5209 / Logical / initial

valid=True; cache_hit=False; error=None

[Full request/response](C:/Users/yoga/Downloads/cocolofa_pard/outputs/nvidia-detection-adaptive-dev10-v3/raw_calls.jsonl:22)

```json
"{\"prediction\":\"Fallacious\",\"confidence\":0.75,\"content\":\"The comment presents a binary framing of the election as a choice between good and evil, implying there are no other options to consider, which is a False Dilemma (false dichotomy). It also makes causal claims (“If the singer is elected it will take a giant leap back” and “The economy will also take a hit”) without any evidence, which is a form of unsupported inference. The premises used: 1) “The country has always been a great example….”, 2) “If the singer is elected it is going to take a giant leap back. The economy will also take a hit”, 3) “This area has always been tolerant and that has helped the country in so many ways.” The conclusion drawn is: “The country needs to vote for good and vote away evil.” The leap from the premises to this conclusion is invalid because it relies on an unsubstantiated moral binary and causal claims, thereby making the argument fallacious.\"}"
```

## Log 23: 237:5209 / Contextual / initial

valid=True; cache_hit=False; error=None

[Full request/response](C:/Users/yoga/Downloads/cocolofa_pard/outputs/nvidia-detection-adaptive-dev10-v3/raw_calls.jsonl:23)

```json
"{\"prediction\":\"Fallacious\",\"confidence\":0.92,\"content\":\"The comment presents a false dichotomy by framing the election as a battle of good versus evil, and it calls for a binary decision (“vote for good and vote away evil”) without evidence. It also makes causal claims (the economy will take a hit if the singer is elected) unsupported by data, amounting to an appeal to emotion and an unsupported assertion. Thus the reasoning is logically fallacious.\"}"
```

## Log 24: 237:5209 / Planner / plan

valid=True; cache_hit=False; error=None

[Full request/response](C:/Users/yoga/Downloads/cocolofa_pard/outputs/nvidia-detection-adaptive-dev10-v3/raw_calls.jsonl:24)

```json
"{\"protocol\":\"cross_examination\",\"topic\":\"logical fallacy detection\",\"reason\":\"The target comment presents an unsubstantiated moral dichotomy (good vs evil) and causal claims about the economy without evidence, making the reasoning fallacious. The consensus among all three agents is that the comment is fallacious, therefore we do not need a point–counterpoint split; a cross‑examination protocol is suitable for clarifying the agreement and documenting the final decision.\",\"order\":[\"Factual\",\"Logical\",\"Contextual\"],\"affirmative\":[],\"negative\":[],\"examiner\":\"Factual\",\"max_rounds\":3}"
```

## Log 25: 237:5209 / Factual / ce_0_question

valid=True; cache_hit=False; error=None

[Full request/response](C:/Users/yoga/Downloads/cocolofa_pard/outputs/nvidia-detection-adaptive-dev10-v3/raw_calls.jsonl:25)

```json
"{\"question\":\"What evidence supports the claim that the economy will take a hit if the singer is elected, and how does that evidence justify a binary good‑vs‑evil framing of the election?\",\"content\":\"The target comment states, “If the singer is elected it is going to take a giant leap back. The economy will also take a hit,” but it does not cite any data or sources linking the singer's policies to economic outcomes. It then insists that voters must choose “good” versus “evil,” implying that only these two options exist and that one choice will secure economic stability while the other will doom the country. Without supporting evidence for the causal link, the reasoning commits a fallacy: it presents an unsupported binary choice (false dichotomy) and makes causal claims without evidence (unsupported inference). Thus, the logic of the argument is fallacious.*\"}"
```

## Log 26: 237:5209 / Logical / ce_answer_0

valid=True; cache_hit=False; error=None

[Full request/response](C:/Users/yoga/Downloads/cocolofa_pard/outputs/nvidia-detection-adaptive-dev10-v3/raw_calls.jsonl:26)

```json
"{\"prediction\":\"Fallacious\",\"confidence\":0.93,\"content\":\"The target comment contains the following premises:\\n- \\u001cIf the singer is elected it is going to take a giant leap back.\\n- \\u001cThe economy will also take a hit.\\nThe conclusion drawn is:\\n- \\u001cThe country needs to vote for good and vote away evil.\\nThe argument fails because it presents an unsupported causal link between the singer’s election and economic outcomes, and it frames the entire election as a binary good‑vs‑evil choice with no evidence or consideration of other possibilities. This constitutes an unsupported inference (lack of evidence for the causal claim) and a false dichotomy (imposing only two moral options). Therefore the reasoning is logically fallacious.\"}"
```

## Log 27: 237:5209 / Contextual / ce_answer_0

valid=True; cache_hit=False; error=None

[Full request/response](C:/Users/yoga/Downloads/cocolofa_pard/outputs/nvidia-detection-adaptive-dev10-v3/raw_calls.jsonl:27)

```json
"{\"prediction\":\"Fallacious\",\"confidence\":0.93,\"content\":\"The target comment states that if the singer is elected the economy will take a hit and frames the election as a binary good‑vs‑evil choice; neither claim is supported by any data or cited sources, and the reasoning relies on an unsupported causal link and a false dichotomy. This demonstrates a logical fallacy. \"}"
```

## Log 28: 237:5209 / Factual / ce_0_reflection

valid=True; cache_hit=False; error=None

[Full request/response](C:/Users/yoga/Downloads/cocolofa_pard/outputs/nvidia-detection-adaptive-dev10-v3/raw_calls.jsonl:28)

```json
"{\"question\":null,\"content\":\"All three prior agents concur that the claim is fallacious: it presents an unsupported causal link between the singer’s election and economic outcomes and imposes a binary good‑vs‑evil framing without evidence or recognition of other possibilities. Since the question of whether the comment is fallacious has been settled, no further interrogative question is required.\"}"
```

## Log 29: 237:5209 / Arbiter / final

valid=True; cache_hit=False; error=None

[Full request/response](C:/Users/yoga/Downloads/cocolofa_pard/outputs/nvidia-detection-adaptive-dev10-v3/raw_calls.jsonl:29)

```json
"{\"prediction\":\"Fallacious\",\"confidence\":0.96,\"content\":\"The comment asserts that electing the singer will cause a “giant leap back” and hit the economy, yet provides no data, citations, or logical steps linking the singer’s policies to those outcomes. It also frames the election strictly as a “good vs. evil” choice, ignoring any other possibilities or nuances. This unsubstantiated causal claim and binary framing amount to an unsupported inference and a false dichotomy, making the reasoning logically fallacious.\"}"
```

## Log 30: 237:5208 / Factual / initial

valid=True; cache_hit=False; error=None

[Full request/response](C:/Users/yoga/Downloads/cocolofa_pard/outputs/nvidia-detection-adaptive-dev10-v3/raw_calls.jsonl:30)

```json
"{\n  \"prediction\": \"Non-Fallacious\",\n  \"confidence\": 0.8,\n  \"content\": \"The target comment simply states a normative principle about voting rather than making a structured argument that would allow a formal logical fallacy to be identified. It does not present a claim with incompatible evidence, nor does it over-generalise from insufficient data, nor does it contain an internally inconsistent factual claim. Therefore, based solely on the supplied text, the comment does not exhibit a clear logical fallacy.\"\n}"
```

## Log 31: 237:5208 / Logical / initial

valid=True; cache_hit=False; error=None

[Full request/response](C:/Users/yoga/Downloads/cocolofa_pard/outputs/nvidia-detection-adaptive-dev10-v3/raw_calls.jsonl:31)

```json
"{\n  \"prediction\": \"Non-Fallacious\",\n  \"confidence\": 0.99,\n  \"content\": \"Premises: 1) It is an election. 2) People must vote according to how they feel.  Conclusion: The appropriate outcome is to determine which candidate best represents the voters and the country as a whole. The comment states a straightforward principle about elections without making an invalid inference or appealing to any logical fallacy.\\nExplanation: The claim simply asserts the general principle that in an election voters should cast ballots reflecting their personal judgment, and that the result should be a candidate who best represents collective interests. There is no causal leap, false dilemma, or unsupported generalization. Thus the reasoning is logically sound.\\n\"\n}"
```

## Log 32: 237:5208 / Contextual / initial

valid=True; cache_hit=False; error=None

[Full request/response](C:/Users/yoga/Downloads/cocolofa_pard/outputs/nvidia-detection-adaptive-dev10-v3/raw_calls.jsonl:32)

```json
"{\"prediction\":\"Non-Fallacious\",\"confidence\":1.0,\"content\":\"The comment states a general principle about elections: that people should vote based on how they feel about who best represents them and the country. This is a straightforward assertion about voting behavior and does not contain a logical fallacy; it neither misapplies reasoning nor omits necessary context to distort a conclusion.\"}"
```

## Log 33: 237:5208 / Planner / plan

valid=True; cache_hit=False; error=None

[Full request/response](C:/Users/yoga/Downloads/cocolofa_pard/outputs/nvidia-detection-adaptive-dev10-v3/raw_calls.jsonl:33)

```json
"{\n  \"protocol\": \"cross_examination\",\n  \"topic\": \"The comment: 'It is an election and people must vote how they feel. Who will best represent them and the country as a whole.'\",\n  \"reason\": \"All supplied predictions are identical (Non‑Fallacious). A cross‑examination protocol is chosen to verify consistency and allow any revealed inconsistency to be challenged.\",\n  \"order\": [\"Contextual\", \"Factual\", \"Logical\"],\n  \"affirmative\": [],\n  \"negative\": [],\n  \"examiner\": \"Logical\",\n  \"max_rounds\": 3\n}"
```

## Log 34: 237:5208 / Logical / ce_0_question

valid=False; cache_hit=False; error=Refused, truncated, or non-final response

[Full request/response](C:/Users/yoga/Downloads/cocolofa_pard/outputs/nvidia-detection-adaptive-dev10-v3/raw_calls.jsonl:34)

```json
"{\"question\":\"What evidence supports the claim that merely voting according to one’s personal feelings will result in electing the candidate who best represents the voters and the country as a whole?\"  \n\n\n\n \r\n\r\n\r\n \r  \r\n\r\n\r\n\r\n\r\n  \r\n\r\n\r\n\r\n  \r\n\r\n\r\n  \r\n\r\n\r\n\r\n  \r\n\r\n\r\n\r\n  \r\n\r\n\r\n\r\n  \r\n\r\n  \r\n\r\n\r\n\r\n\n\n \r \r \n \r \n \r \n \r \n \r \n \r \n \r \n \r \n \r \n \r \n \r  \r\t\t  \n  \r \n \r  \r \n \r  \r \n \r  \r \n \r  \r \n \r  \r \n \r  \r \n \r  \r \n \r  \r \n \r  \r \n \r  \r \n \r  \r \n \r  \r \n \r  \r \n \r  \r \n \r  \r \n \r  \r \n \r  \r \n \r  \r \n \r  \n\n\n\n\r  \n\n\n\n\n\n\n  \n\n\n\n\n  \n\n\n\n\n\n\n\n  \n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n\n\n  \n\n\n\n\n\n\n\n\n  \n\n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n  \n\n\n\n\n\n\n \n  \n\n\n\n  \n\n\n\n\n\n\n\n\n\n\n\n\n\n\n  \n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n  \n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n  \n\n\n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n \r  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n \r  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n \r \n  \n\n\n\n\n\n\n\n\n \r  \n\n\n\n\n\n \r  \n\n\n\n\n\n\n \r  \n\n\n\n\n\n\n \r  \n\n\n\n\n\n\n \r  \n\n\n\n\n\n\n \r  \n\n\n\n\n\n\n \r  \n\n\n\n\n\n\n\n\n  \n\n\n\n\n\n\n \r  \n\n\n\n\n\n\n \r  \n\n\n\n\n\n\n \r  \n\n\n\n\n\n\n\n\n  \n\n\n\n\n\n\n \r  \n\n\n\n\n\n\n \r  \n\n\n\n\n\n\n \r  \n\n\n\n\n\n\n \r  \n\n\n\n\n\n\n \r  \n\n\n\n\n\n\n \r  \n\n\n\n\n\n\n \r  \n\n\n\n\n\n\n \r  \n\n\n\n\n\n\n \r  \n\n\n\n\n\n\n \r  \n\n\n\n\n\n\n \r  \n\n\n\n\n\n\n \r  \n\n\n\n\n\n\n  \n\n\n\n  \n\n\n\n\n\n\n\n\n \r  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n \r  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n  \n\n\n\n  \n\n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n \r  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n   \n\n  \n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n\n\n  \n\n\n\n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n \r  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n      \n\n  \n\n\n\n\n\n\n   \n  \n\n\n\n  \n\n\n\n\n\n\n    \n  \n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n      \n\n  \n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n  \n\n\n\n\n\n\n\n  \n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n\n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n      \n\n  \n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n            \n   \n  \n\n\n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n  \n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n  \n\n\n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n\n\n\n\n  \n\n\n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n  \n\n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n \n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n    \n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n\n\n  \n\n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n   \n   \n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n   \n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n    \t\t\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n   \n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n\n\n  \n\n\n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n \r  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n         \n  \n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n  \n\n\n\n\n\n\n"
```

## Log 35: 237:5208 / Logical / ce_0_question

valid=True; cache_hit=False; error=None

[Full request/response](C:/Users/yoga/Downloads/cocolofa_pard/outputs/nvidia-detection-adaptive-dev10-v3/raw_calls.jsonl:35)

```json
"{\"question\":\"Who is being represented in the statement that 'people must vote how they feel'?\",\"content\":\"The claim suggests individuals vote in accordance with personal feeling; however, the premise that a feeling can determine who 'best represents' the country lacks evidence that such feelings correspond to objective representation. The inference about determining the best representative is unsupported if the feeling alone is inadequate proxy. The claim lays out the reasoning as premises: (1) it is an election; (2) voters must vote how they feel; conclusion: whoever best represents the voters/country will emerge. The argument assumes a direct link between feeling and best representation without justification.\"}"
```

## Log 36: 237:5208 / Contextual / ce_answer_0

valid=True; cache_hit=False; error=None

[Full request/response](C:/Users/yoga/Downloads/cocolofa_pard/outputs/nvidia-detection-adaptive-dev10-v3/raw_calls.jsonl:36)

```json
"{\"prediction\":\"Non-Fallacious\",\"confidence\":0.97,\"content\":\"The statement ‘people must vote how they feel’ is a general claim about voting behavior. The pronoun *them* in the following sentence— ‘Who will best represent them and the country as a whole’—refers to the voters (the people who are casting the ballot). Thus the representation being sought is for the voters themselves and for the country as an entire entity. The comment makes no claim that it applies to any other group, so the represented parties are just the electorate and the state.*\"}"
```

## Log 37: 237:5208 / Factual / ce_answer_0

valid=True; cache_hit=False; error=None

[Full request/response](C:/Users/yoga/Downloads/cocolofa_pard/outputs/nvidia-detection-adaptive-dev10-v3/raw_calls.jsonl:37)

```json
"{\"prediction\":\"Non-Fallacious\",\"confidence\":0.97,\"content\":\"The target comment does not present a formal argument with premises and a conclusion that could be logically invalid; it merely states a normative claim (“people must vote how they feel”) and poses a question about representation. It does not involve an unsupported inference, overgeneralization, or internal inconsistency that would constitute a fallacy. Therefore, based on the supplied text, the comment is non‑fallacious.\"}"
```

## Log 38: 237:5208 / Logical / ce_0_reflection

valid=True; cache_hit=False; error=None

[Full request/response](C:/Users/yoga/Downloads/cocolofa_pard/outputs/nvidia-detection-adaptive-dev10-v3/raw_calls.jsonl:38)

```json
"{\"question\":null,\"content\":\"The earlier responses correctly identified that the pronoun ‘them’ refers to the voters—who are represented by the candidate that best aligns with their collective interest.  Thus the question has been answered and no further interrogation is required.\"}"
```

## Log 39: 237:5208 / Arbiter / final

valid=True; cache_hit=False; error=None

[Full request/response](C:/Users/yoga/Downloads/cocolofa_pard/outputs/nvidia-detection-adaptive-dev10-v3/raw_calls.jsonl:39)

```json
"{\"prediction\":\"Non-Fallacious\",\"confidence\":1.0,\"content\":\"The comment merely states a normative claim that voters should vote according to their feelings and raises a question about representation. It does not construct a formal argument with premises and a conclusion that can be invalidated, nor does it exhibit any identified fallacious reasoning. Thus the comment is non‑fallacious.\"}"
```

## Log 40: 237:5207 / Factual / initial

valid=True; cache_hit=False; error=None

[Full request/response](C:/Users/yoga/Downloads/cocolofa_pard/outputs/nvidia-detection-adaptive-dev10-v3/raw_calls.jsonl:40)

```json
"{\"prediction\":\"Fallacious\",\"confidence\":0.92,\"content\":\"The comment extrapolates from the single example that the U.S. took ten years to legalize gay marriage to the claim that other countries will take even longer, without providing evidence for that pattern. This overgeneralizes a single case and then offers a vague causal hypothesis (“the rise of social media”) without supporting evidence, constituting a fallacious argument.\"}"
```

## Log 41: 237:5207 / Logical / initial

valid=True; cache_hit=False; error=None

[Full request/response](C:/Users/yoga/Downloads/cocolofa_pard/outputs/nvidia-detection-adaptive-dev10-v3/raw_calls.jsonl:41)

```json
"{\"prediction\":\"Fallacious\",\"confidence\":0.92,\"content\":\"The comment asserts that anti‑LGBT candidates will continue to use such rhetoric for a long time, because \\\"the US just legalized gay marriage only 10 years ago; if it took us this long, it'll take countries like those much longer,\\\" implying that the historical timeline in the US predicts the duration in other nations.\\n\\nPremise 1: The U.S. legalized gay marriage 10 years ago.\\nPremise 2: If the U.S. required 10 years, a comparable country will require an even longer period.\\nConclusion: Anti‑LGBT candidates in that country will maintain such stances for a long time.\\n\\nThis inference commits a non‑sequiturs/false analogy (fallacy of composition) by treating the U.S. experience as a reliable predictor for other countries without acknowledging differing political, cultural, or social conditions. Thus the argument is fallacious.\\n\\nKey span: \\\"I mean the US just legalized gay marriage only 10 years ago. If it took us this long, it'll take countries like those much longer\\\"\"}"
```

## Log 42: 237:5207 / Contextual / initial

valid=True; cache_hit=False; error=None

[Full request/response](C:/Users/yoga/Downloads/cocolofa_pard/outputs/nvidia-detection-adaptive-dev10-v3/raw_calls.jsonl:42)

```json
"{\"prediction\":\"Fallacious\",\"confidence\":0.68,\"content\":\"The comment extrapolates that because the U.S. took ten years to legalize gay marriage, other countries will take even longer, without providing supporting evidence or accounting for differing political, cultural, or legal contexts. This overgeneralization from a single case to a broader claim constitutes a logical fallacy (a hasty generalization).\"}"
```

## Log 43: 237:5207 / Planner / plan

valid=True; cache_hit=False; error=None

[Full request/response](C:/Users/yoga/Downloads/cocolofa_pard/outputs/nvidia-detection-adaptive-dev10-v3/raw_calls.jsonl:43)

```json
"{\n  \"protocol\": \"round_robin\",\n  \"topic\": \"LGBTQI Rights Defenders Sound Alarm over Costa Rica's Presidential Election\",\n  \"reason\": \"All agents independently judged the target comment as fallacious; no direct conflict exists to necessitate a point-counterpoint or cross-examination structure.\",\n  \"order\": [\"Contextual\", \"Factual\", \"Logical\"],\n  \"affirmative\": [],\n  \"negative\": [],\n  \"examiner\": \"Logical\",\n  \"max_rounds\": 3\n}"
```

## Log 44: 237:5207 / Contextual / rr_0

valid=True; cache_hit=False; error=None

[Full request/response](C:/Users/yoga/Downloads/cocolofa_pard/outputs/nvidia-detection-adaptive-dev10-v3/raw_calls.jsonl:44)

```json
"{\"prediction\":\"Fallacious\"   , \"confidence\":0.95, \"content\":\"The comment assumes that the U.S.’s 10‑year path to gay marriage legalization predicts a longer timeline elsewhere, without accounting for differing legal, cultural, or social contexts—an overgeneralization without evidence.\"}"
```

## Log 45: 237:5207 / Factual / rr_0

valid=True; cache_hit=False; error=None

[Full request/response](C:/Users/yoga/Downloads/cocolofa_pard/outputs/nvidia-detection-adaptive-dev10-v3/raw_calls.jsonl:45)

```json
"{\"prediction\":\"Fallacious\",\"confidence\":0.95,\"content\":\"The comment extrapolates from one case—the U.S. taking ten years to legalize gay marriage—to argue that other countries will take even longer, without citing any evidence that the U.S. experience predicts other nations’ timelines or accounting for cultural, legal, or social differences. This overgeneralization (false analogy) invalidates the inference that anti‑LGBT candidates will persist in such rhetoric for a long time elsewhere.\"}"
```

## Log 46: 237:5207 / Logical / rr_0

valid=True; cache_hit=False; error=None

[Full request/response](C:/Users/yoga/Downloads/cocolofa_pard/outputs/nvidia-detection-adaptive-dev10-v3/raw_calls.jsonl:46)

```json
"{\"prediction\":\"Fallacious\",\"confidence\":0.95,\"content\":\"The comment predicates its prediction on an unsubstantiated generalization: the US’ 10‑year journey to legalize gay marriage is treated as evidence that a similar (or comparable) country will take even longer. The underlying premise— that the U.S. experience predicts the duration of social‑change movements in other nations— is omitted. Because the inference relies on an unsupported causal link, the argument is invalid.\\n\\nPremises:\\n1. The U.S. legalized gay marriage 10 years ago. (Target)\\n2. (Implicit) The U.S.’s 10‑year timeline is indicative of how quickly any other country can achieve similar reforms. (Missing premise)\\nConclusion:\\n- Anti‑LGBT candidates in other countries (e.g., Costa Rica) will persist in that rhetoric for a long time. (Target)\\n\\nInference:\\nNon‑sequiturs / false analogy: The argument treats the U.S. experience as a reliable predictor for other countries without accounting for differing legal, cultural, or social contexts. This omission causes the conclusion to lack a valid logical connection to the stated premise.\\n\\nInfer span:\\n\\\"I mean the US just legalized gay marriage only 10 years ago. If it took us this long, it'll take countries like those much longer\\\"\"}"
```

## Log 47: 237:5207 / Contextual / rr_1

valid=True; cache_hit=False; error=None

[Full request/response](C:/Users/yoga/Downloads/cocolofa_pard/outputs/nvidia-detection-adaptive-dev10-v3/raw_calls.jsonl:47)

```json
"{\"prediction\":\"Fallacious\",\"confidence\":0.95,\"content\":\"The comment relies on an unspoken premise that the U.S.’s 10‑year journey to legalize gay marriage serves as a reliable benchmark for how long similar reforms will take elsewhere, such as in Costa Rica. It ignores the fact that legal, cultural, and social contexts differ significantly between nations. Without evidence that the U.S. experience predicts other countries’ timelines, the inference that anti‑LGBT candidates will persist for an even longer time elsewhere is unsupported and constitutes a false‑analogy fallacy.\"}"
```

## Log 48: 237:5207 / Factual / rr_1

valid=True; cache_hit=False; error=None

[Full request/response](C:/Users/yoga/Downloads/cocolofa_pard/outputs/nvidia-detection-adaptive-dev10-v3/raw_calls.jsonl:48)

```json
"{\"prediction\":\"Fallacious\",\"confidence\":0.95,\"content\":\"The comment implicitly assumes that the U.S.’s 10‑year path to legalizing gay marriage is a universal benchmark for how long similar reforms will take elsewhere. This premise is missing because the comment says, \\\"If it took us this long, it'll take countries like those much longer,\\\" without justifying why the U.S. experience should predict the timelines of countries with markedly different legal systems, cultures, and social attitudes (e.g., Costa Rica). The inference therefore lacks a connective premise that accounts for contextual differences, making the reasoning unsupported and fallacious.\"}"
```

## Log 49: 237:5207 / Logical / rr_1

valid=True; cache_hit=False; error=None

[Full request/response](C:/Users/yoga/Downloads/cocolofa_pard/outputs/nvidia-detection-adaptive-dev10-v3/raw_calls.jsonl:49)

```json
"{\"prediction\":\"Fallacious\",\"confidence\":0.95,\"content\":\"The comment draws a conclusion about future anti‑LGBT rhetoric in other nations based solely on the U.S. taking ten years to legalize gay marriage, but it omits the essential premise that the U.S. timeline can serve as a reliable predictor for any other country. Without evidence that legal, cultural, or social conditions are comparable, the inference ignores major contextual differences and relies on a false analogy. Consequently the argument commits a fallacy of overlooking a key premise (the U.S. benchmark premise).\"}"
```

## Log 50: 237:5207 / Arbiter / final

valid=True; cache_hit=False; error=None

[Full request/response](C:/Users/yoga/Downloads/cocolofa_pard/outputs/nvidia-detection-adaptive-dev10-v3/raw_calls.jsonl:50)

```json
"{\"prediction\":\"Fallacious\",\"confidence\":0.95,\"content\":\"The comment infers that because the U.S. required 10 years to legalize gay marriage, other nations (e.g., Costa Rica) will take even longer, without providing any evidence that the U.S. experience is a reliable predictor for other countries. The inference rests on an omitted premise— that the U.S. timeline is universally indicative of how long similar reforms will take elsewhere— and ignores significant legal, cultural, and social differences. This unsupported generalization constitutes a false‑analogy/hasty generalization fallacy.\"}"
```

## Log 51: 237:5508 / Factual / initial

valid=True; cache_hit=False; error=None

[Full request/response](C:/Users/yoga/Downloads/cocolofa_pard/outputs/nvidia-detection-adaptive-dev10-v3/raw_calls.jsonl:51)

```json
"{\"prediction\":\"Non-Fallacious\",\"confidence\":0.92,\"content\":\"The target comment expresses an opinion and a proposal based on the belief that social media can accelerate social change: \\\"I think we can use social media to move this cause faster and ensure equal rights for all.\\\" This statement does not commit a recognizable logical fallacy such as ad hominem, straw‑man, false dilemma, or others. It simply posits a causal relationship without providing evidence, which constitutes an unsupported assertion rather than a formal fallacy. Therefore, the comment is judged as non‑fallacious.\"}"
```

## Log 52: 237:5508 / Logical / initial

valid=True; cache_hit=False; error=None

[Full request/response](C:/Users/yoga/Downloads/cocolofa_pard/outputs/nvidia-detection-adaptive-dev10-v3/raw_calls.jsonl:52)

```json
"{\"prediction\":\"Fallacious\",\"confidence\":0.73,\"content\":\"Yes, the comment contains a logical fallacy. The commenter concludes that social media can accelerate equal‑rights progress simply because other countries are setting a precedent, but offers no evidence or reasoning that social media will actually cause a faster outcome. The reasoning jumps from the observation that other nations have made gains to the claim that a hashtag activism strategy will suffice, without establishing a causal link. The premise “other countries are setting precedent” does not logically support the conclusion that an online movement alone will ensure quicker equality, so the inference is invalid. Thus the target comment is fallacious.\"}"
```

## Log 53: 237:5508 / Contextual / initial

valid=True; cache_hit=False; error=None

[Full request/response](C:/Users/yoga/Downloads/cocolofa_pard/outputs/nvidia-detection-adaptive-dev10-v3/raw_calls.jsonl:53)

```json
"{\"prediction\":\"Non-Fallacious\",\"confidence\":1.0,\"content\":\"The comment simply proposes a method (using social media and a hashtag movement) to accelerate progress toward equal rights. It does not present an argument with premises, conclusions, or a logical structure that could contain a fallacy. Thus, the comment is non-fallacious.\"}"
```

## Log 54: 237:5508 / Planner / plan

valid=True; cache_hit=False; error=None

[Full request/response](C:/Users/yoga/Downloads/cocolofa_pard/outputs/nvidia-detection-adaptive-dev10-v3/raw_calls.jsonl:54)

```json
"{\"protocol\":\"point_counterpoint\",\"topic\":\"LGBTQI Rights Defenders Sound Alarm over Costa Rica's Presidential Election\",\"reason\":\"Two agents predicted 'Non-Fallacious' and one predicted 'Fallacious', a natural 2v1 split. This matches the point_counterpoint protocol.\",\"order\":[\"Logical\",\"Contextual\",\"Factual\"],\"affirmative\":[\"Contextual\",\"Factual\"],\"negative\":[\"Logical\"],\"examiner\":\"Logical\",\"max_rounds\":3}"
```

## Log 55: 237:5508 / Contextual / pc_0_affirmative

valid=True; cache_hit=False; error=None

[Full request/response](C:/Users/yoga/Downloads/cocolofa_pard/outputs/nvidia-detection-adaptive-dev10-v3/raw_calls.jsonl:55)

```json
"{\"prediction\":\"Non-Fallacious\",\"confidence\":0.92,\"content\":\"The target comment states, \\\"I think we can use social media to move this cause faster and ensure equal rights for all,\\\" and proposes a hashtag movement. It is a simple statement of belief and a suggestion for action. It does not present premises that support a conclusion, nor does it imply an invalid inference such as a false dilemma or ad hominem. The reasoning is not structured in a way that could exhibit a logical fallacy; it merely offers an unsubstantiated claim that social media can accelerate progress, which is an unsupported assertion rather than a formal fallacious argument. Therefore, the comment is non‑fallacious.\"}"
```

## Log 56: 237:5508 / Factual / pc_0_affirmative

valid=True; cache_hit=False; error=None

[Full request/response](C:/Users/yoga/Downloads/cocolofa_pard/outputs/nvidia-detection-adaptive-dev10-v3/raw_calls.jsonl:56)

```json
"{\n  \"prediction\": \"Non-Fallacious\",\n  \"confidence\": 0.92,\n  \"content\": \"The target comment states an opinion about using social media to accelerate equal‑rights progress and proposes a hashtag movement. It does not present premises that are intended to support a conclusion, nor does it employ a recognizable fallable inference pattern (e.g., false dilemma, ad hominem, etc.). The claim that social media will speed outcomes is an unsupported assertion, but this lack of evidence alone does not constitute a logical fallacy. Therefore, the comment is non‑fallacious.\"\n}"
```

## Log 57: 237:5508 / Logical / pc_0_negative

valid=True; cache_hit=False; error=None

[Full request/response](C:/Users/yoga/Downloads/cocolofa_pard/outputs/nvidia-detection-adaptive-dev10-v3/raw_calls.jsonl:57)

```json
"{\"prediction\":\"Fallacious\",\"confidence\":0.73,\"content\":\"The comment asserts that moving the cause forward swiftly, ensuring equal rights for all, can be achieved through a hashtag movement. The implicit reasoning is: *Because other countries are setting precedents, social media can accelerate this process.* The premises explicitly mentioned are: 1) *Other countries are setting precedent* (span: *“other countries are setting a precedent”*); 2) *Social media can move the cause faster and ensure equal rights* (span: *“I think we can use social media to move this cause faster and ensure equal rights for all”*). The conclusion the commenter draws is that the proposed hashtag strategy will accomplish those goals. This inference jumps directly from the observation that some nations are making progress to the claim that a specific digital tactic will guarantee comparable outcomes without providing evidence of a causal link. The argument therefore commits a non‑sequitur fallacy: the premises do not logically support the conclusion. The assertion that “a hashtag movement” will alone lead to faster equality is an invalid inference, which qualifies the comment as fallacious. \"}"
```

## Log 58: 237:5508 / Contextual / pc_1_affirmative

valid=True; cache_hit=False; error=None

[Full request/response](C:/Users/yoga/Downloads/cocolofa_pard/outputs/nvidia-detection-adaptive-dev10-v3/raw_calls.jsonl:58)

```json
"{\"prediction\":\"Non-Fallacious\",\"confidence\":0.92,\"content\":\"The target comment is an expression of opinion and a proposal for action.  It contains no explicit premises that lead to a conclusion, nor does it formulate an inference that could be linked to a recognized fallacy such as a non‑sequitur.  The statement “I think we can use social media to move this cause faster and ensure equal rights for all” merely asserts a belief about potential effectiveness and suggests creating a hashtag.  Because the text does not present a structured argument that fails to follow logical rules, nothing in it demonstrates a fallacious inference.  Therefore, the comment is best classified as non‑fallacious.\"}"
```

## Log 59: 237:5508 / Factual / pc_1_affirmative

valid=True; cache_hit=False; error=None

[Full request/response](C:/Users/yoga/Downloads/cocolofa_pard/outputs/nvidia-detection-adaptive-dev10-v3/raw_calls.jsonl:59)

```json
"{\"prediction\":\"Non-Fallacious\",\"confidence\":0.86,\"content\":\"The target comment reads: *“But does it have to take that long when other countries are setting a precedent? I think we can use social media to move this cause faster and ensure equal rights for all. Let's create a hashtag movement, tag relevant officials and leaders, together we can do this!”* It is a direct exhortation of action and an expression of belief. It contains no structured set of premises that are meant to support a particular conclusion, nor does it explicitly present an inference that could be mismatched. The only inference that can be discerned is the author’s own, that “social media can accelerate the cause,” but the text does not show a logical chain whereby premises lead to this result; it merely states the belief. Thus, labeling the comment as a *non‑sequitur* is an over‑extension: the definition requires an explicit premise–conclusion structure that fails to support each other. Here, the comment is simply an opinion + call to action, which, although unsupported by evidence, does not constitute an argument at all, let alone a fallacious one. Accordingly, the assessment “Non‑Fallacious” is accurate. No reason exists in the supplied text to regard the comment as fallacious.\"}"
```

## Log 60: 237:5508 / Logical / pc_1_negative

valid=True; cache_hit=False; error=None

[Full request/response](C:/Users/yoga/Downloads/cocolofa_pard/outputs/nvidia-detection-adaptive-dev10-v3/raw_calls.jsonl:60)

```json
"{\"prediction\":\"Fallacious\",\"confidence\":0.73,\"content\":\"The comment presents an implicit inference that the fact that other countries are setting precedents *justifies* using social media to accelerate progress and guarantee equal rights in Costa Rica. The premises it supplies are: 1) *‘other countries are setting a precedent’* (span: “But does it have to take that long when other countries are setting a precedent?”) and 2) *‘social media can move this cause faster’* (span: “I think we can use social media to move this cause faster and ensure equal rights for all”). From these premises the conclusion drawn is the practical plan of launching a hashtag movement that will “ensure equal rights for all”. The leap from observing progress elsewhere to asserting that a particular tactic will produce the same outcome is unsupported; no evidence of a causal link or mechanism is offered. This is a classic non‑sequitur: the premises do not logically support the conclusion. The comment therefore contains a fallacious inference. If the commenter instead had provided evidence that social media campaigns in other contexts had produced measurable legal or societal change, the inference might be valid. In its current form, the claim rests on an illicit causal generalization, rendering the argument fallacious. \"}"
```

## Log 61: 237:5508 / Arbiter / final

valid=True; cache_hit=False; error=None

[Full request/response](C:/Users/yoga/Downloads/cocolofa_pard/outputs/nvidia-detection-adaptive-dev10-v3/raw_calls.jsonl:61)

```json
"{\"prediction\":\"Non-Fallacious\",\"confidence\":0.92,\"content\":\"The comment is a straightforward expression of opinion and a call to action. It states an unsubstantiated belief that social media can accelerate the cause, but it does not present premises that the author is asserting as supporting a conclusion. The only inference it contains is the implicit idea that because other countries are progressing, a hashtag campaign will help, yet the text does not form a structured argument or demonstrate that the premises fail to support the conclusion. Therefore the comment does not contain a recognisable logical fallacy and is best classified as non‑fallacious.\"}"
```

## Log 62: 237:5509 / Factual / initial

valid=True; cache_hit=False; error=None

[Full request/response](C:/Users/yoga/Downloads/cocolofa_pard/outputs/nvidia-detection-adaptive-dev10-v3/raw_calls.jsonl:62)

```json
"{\"prediction\":\"Non-Fallacious\",\"confidence\":0.85,\"content\":\"None\"}"
```

## Log 63: 237:5509 / Logical / initial

valid=True; cache_hit=False; error=None

[Full request/response](C:/Users/yoga/Downloads/cocolofa_pard/outputs/nvidia-detection-adaptive-dev10-v3/raw_calls.jsonl:63)

```json
"{\"prediction\":\"Fallacious\",\"confidence\":0.88,\"content\":\"{\\\"status\\\":\\\"Fallacious\\\",\\\"faulty_inference_type\\\":[\\\"non sequitur\\\"],\\\"premises\\\":[\\\"Perhaps there can be some compromised so that there are not additional verbal and physical attacks.\\\",\\\"They can't control the way the people think.\\\",\\\"This seems certainly unfair.\\\"],\\\"conclusion\\\":\\\"But there has to be some way to keep these people safe.\\\",\\\"explanation\\\":\\\"The premises assert a possible compromise, unfairness, and the inability to control others’ thoughts. None of these premises logically safeguards the conclusion that *there must be some way to keep these people safe*. The inference draws a causal link without evidence, leaving the conclusion unsupported – a classic non sequitur.\\\"}\"}"
```

## Log 64: 237:5509 / Contextual / initial

valid=True; cache_hit=False; error=None

[Full request/response](C:/Users/yoga/Downloads/cocolofa_pard/outputs/nvidia-detection-adaptive-dev10-v3/raw_calls.jsonl:64)

```json
"{\"prediction\":\"Non-Fallacious\",\"confidence\":1.0,\"content\":\"No logical fallacy is evident in the target comment. It merely presents an opinion about potential compromise, highlights perceived unfairness, observes that people cannot control others’ thoughts, and suggests a need to keep people safe. None of these constitute a fallacious reasoning pattern.\"}"
```

## Log 65: 237:5509 / Planner / plan

valid=False; cache_hit=False; error=Order must include each role once

[Full request/response](C:/Users/yoga/Downloads/cocolofa_pard/outputs/nvidia-detection-adaptive-dev10-v3/raw_calls.jsonl:65)

```json
"{\n  \"protocol\": \"point_counterpoint\",\n  \"topic\": \"LGBTQI Rights Defenders Sound Alarm over Costa Rica's Presidential Election\",\n  \"reason\": \"Two distinct initial predictions were detected (fallacious vs. non‑fallacious). The point_counterpoint protocol requires a two‑team split with each team’s predictions aligned to one of the initial prediction groups.\",\n  \"order\": [],\n  \"affirmative\": [],\n  \"negative\": [],\n  \"examiner\": \"Logical\",\n  \"max_rounds\": 3\n}"
```

## Log 66: 237:5509 / Planner / plan

valid=False; cache_hit=False; error=Order must include each role once

[Full request/response](C:/Users/yoga/Downloads/cocolofa_pard/outputs/nvidia-detection-adaptive-dev10-v3/raw_calls.jsonl:66)

```json
"{\"protocol\":\"point_counterpoint\",\"topic\":\"LGBTQI Rights Defenders Sound Alarm over Costa Rica's Presidential Election\",\"reason\":\"Two distinct predictions exist: Non-Fallacious vs Fallacious. Point‑counterpoint is appropriate for a 1 vs 2 team split.\",\"order\":[\"Logical\",\"Contextual\"],\"affirmative\":[],\"negative\":[],\"examiner\":\"Logical\",\"max_rounds\":3}"
```

## Log 67: 237:5509 / Planner / plan

valid=False; cache_hit=False; error=Teams must be a disjoint 2v1 partition of all roles

[Full request/response](C:/Users/yoga/Downloads/cocolofa_pard/outputs/nvidia-detection-adaptive-dev10-v3/raw_calls.jsonl:67)

```json
"{\n  \"protocol\": \"point_counterpoint\",\n  \"topic\": \"LGBTQI Rights Defenders Sound Alarm over Costa Rica's Presidential Election\",\n  \"reason\": \"Two opposing predictions (Non-Fallacious vs. Fallacious) require a 2v1 split\",\n  \"order\": [\"Logical\", \"Contextual\", \"Factual\"],\n  \"affirmative\": [],\n  \"negative\": [],\n  \"examiner\": \"Logical\",\n  \"max_rounds\": 3\n}"
```

## Log 68: 237:5509 / Factual / initial

valid=True; cache_hit=True; error=None

[Full request/response](C:/Users/yoga/Downloads/cocolofa_pard/outputs/nvidia-detection-adaptive-dev10-v3/raw_calls.jsonl:68)

```json
"{\"prediction\":\"Non-Fallacious\",\"confidence\":0.85,\"content\":\"None\"}"
```

## Log 69: 237:5509 / Logical / initial

valid=True; cache_hit=True; error=None

[Full request/response](C:/Users/yoga/Downloads/cocolofa_pard/outputs/nvidia-detection-adaptive-dev10-v3/raw_calls.jsonl:69)

```json
"{\"prediction\":\"Fallacious\",\"confidence\":0.88,\"content\":\"{\\\"status\\\":\\\"Fallacious\\\",\\\"faulty_inference_type\\\":[\\\"non sequitur\\\"],\\\"premises\\\":[\\\"Perhaps there can be some compromised so that there are not additional verbal and physical attacks.\\\",\\\"They can't control the way the people think.\\\",\\\"This seems certainly unfair.\\\"],\\\"conclusion\\\":\\\"But there has to be some way to keep these people safe.\\\",\\\"explanation\\\":\\\"The premises assert a possible compromise, unfairness, and the inability to control others’ thoughts. None of these premises logically safeguards the conclusion that *there must be some way to keep these people safe*. The inference draws a causal link without evidence, leaving the conclusion unsupported – a classic non sequitur.\\\"}\"}"
```

## Log 70: 237:5509 / Contextual / initial

valid=True; cache_hit=True; error=None

[Full request/response](C:/Users/yoga/Downloads/cocolofa_pard/outputs/nvidia-detection-adaptive-dev10-v3/raw_calls.jsonl:70)

```json
"{\"prediction\":\"Non-Fallacious\",\"confidence\":1.0,\"content\":\"No logical fallacy is evident in the target comment. It merely presents an opinion about potential compromise, highlights perceived unfairness, observes that people cannot control others’ thoughts, and suggests a need to keep people safe. None of these constitute a fallacious reasoning pattern.\"}"
```

## Log 71: 237:5509 / Planner / plan

valid=False; cache_hit=False; error=Teams must be a disjoint 2v1 partition of all roles

[Full request/response](C:/Users/yoga/Downloads/cocolofa_pard/outputs/nvidia-detection-adaptive-dev10-v3/raw_calls.jsonl:71)

```json
"{\n    \"protocol\": \"point_counterpoint\",\n    \"topic\": \"Fallacy assessment of target comment\",\n    \"reason\": \"The reports present two distinct prediction outcomes: Non-Fallacious (Contextual + Factual) vs. Fallacious (Logical). This satisfies the requirement for a 2v1 split in predictions.\",\n    \"order\": [\"Logical\", \"Contextual\", \"Factual\"],\n    \"affirmative\": [],\n    \"negative\": [],\n    \"examiner\": \"Logical\",\n    \"max_rounds\": 3\n}"
```

## Log 72: 237:5509 / Planner / plan

valid=False; cache_hit=False; error=Teams must be a disjoint 2v1 partition of all roles

[Full request/response](C:/Users/yoga/Downloads/cocolofa_pard/outputs/nvidia-detection-adaptive-dev10-v3/raw_calls.jsonl:72)

```json
"{\n  \"protocol\": \"point_counterpoint\",\n  \"topic\": \"Logical fallacy assessment of the target comment\",\n  \"reason\": \"The first agent (Ben) predicted a non‐fallacious conclusion, while the second agent (Fae) predicted a fallacious conclusion. Both predictions are distinct, so the point_counterpoint protocol, which partitions the participants into a 1‑vs‑2 team split with the same predictions, is appropriate.\",\n  \"order\": [\n    \"Contextual\",\n    \"Factual\",\n    \"Logical\"\n  ],\n  \"affirmative\": [\n    \"Contextual\",\n    \"Factual\",\n    \"Logical\"\n  ],\n  \"negative\": [\n    \"Contextual\",\n    \"Logical\"\n  ],\n  \"examiner\": \"Factual\",\n  \"max_rounds\": 3\n}"
```

## Log 73: 237:5509 / Planner / plan

valid=False; cache_hit=False; error=Teams must be a disjoint 2v1 partition of all roles

[Full request/response](C:/Users/yoga/Downloads/cocolofa_pard/outputs/nvidia-detection-adaptive-dev10-v3/raw_calls.jsonl:73)

```json
"{\n  \"protocol\": \"point_counterpoint\",\n  \"topic\": \"Logical Fallacy Analysis\",\n  \"reason\": \"The target comment is assessed to be non-fallacious. A point-counterpoint structure allows a concise debate between a single perspective and a two-entity perspective, satisfying the requirement for disjoint teams of sizes 1 and 2.\",\n  \"order\": [\n    \"Contextual\",\n    \"Factual\",\n    \"Logical\"\n  ],\n  \"affirmative\": [],\n  \"negative\": [],\n  \"examiner\": \"Contextual\",\n  \"max_rounds\": 3\n}"
```
