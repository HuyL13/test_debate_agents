import json

llama_path = 'outputs/marketplace-classification-adversarial-llama70b-test481-v1/summary.json'
gpt_path = 'outputs/marketplace-classification-adversarial-gptoss120b-test481-v1/summary.json'

llama_full = json.load(open(llama_path, encoding='utf-8'))
gpt_full = json.load(open(gpt_path, encoding='utf-8'))

llama = llama_full['per_class']
gpt = gpt_full['per_class']

labels = sorted(llama.keys())

print(f"{'Label':<26} | {'Sup':<4} | {'Llama Prec':<10} {'GPT Prec':<10} {'Diff Prec':<10} | {'Llama Rec':<10} {'GPT Rec':<10} {'Diff Rec':<10} | {'Llama F1':<9} {'GPT F1':<9} {'Diff F1':<8}")
print("-" * 125)

for l in labels:
    lp, lr, lf, sup = llama[l]['precision']*100, llama[l]['recall']*100, llama[l]['f1']*100, llama[l]['support']
    gp, gr, gf = gpt[l]['precision']*100, gpt[l]['recall']*100, gpt[l]['f1']*100
    dp = gp - lp
    dr = gr - lr
    df = gf - lf
    print(f"{l:<26} | {sup:<4} | {lp:6.2f}%    {gp:6.2f}%    {dp:+6.2f}%    | {lr:6.2f}%    {gr:6.2f}%    {dr:+6.2f}%    | {lf:6.2f}%   {gf:6.2f}%   {df:+6.2f}%")

print("-" * 125)
acc_l, acc_g = llama_full['accuracy']*100, gpt_full['accuracy']*100
f1_l, f1_g = llama_full['macro_f1']*100, gpt_full['macro_f1']*100
print(f"{'Macro Average / Overall':<26} | 481  | {'-':<10} {'-':<10} {'-':<10} | {'-':<10} {'-':<10} {'-':<10} | {f1_l:6.2f}%   {f1_g:6.2f}%   {f1_g-f1_l:+6.2f}%")
print(f"Accuracy: Llama-70B = {acc_l:.2f}%, GPT-OSS-120B = {acc_g:.2f}% (Diff = {acc_g-acc_l:+.2f}%)")
